
import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import Client, SimpleTestCase, TestCase

from accounts.models import User
from .models import Calculation
from .services import Catalog, ForecastError, load_data
from .views import get_catalog

PARAMS = {"origin": "Москва", "destination": "Сочи", "date": "2026-06-01", "price": 10000}


class CalculationTests(SimpleTestCase):


    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalog = load_data(settings.BASE_DIR / "data/seasonal_forecast.csv", settings.BASE_DIR / "data/routes.csv")

    def test_real_data_and_manual_control(self):
        self.assertEqual(len(self.catalog.flights), 155)
        self.assertEqual(len(self.catalog.routes), 5)
        result = self.catalog.compute_forecast(**{ "origin": "Москва", "destination": "Сочи", "date_iso": "2026-06-01", "price": 10000 })
        self.assertEqual((result["wish"], result["sold"], result["seats"], result["remaining"]), (634, 634, 900, 266))
        self.assertEqual(result["wish"], result["scenarios"][4]["wish"])
        self.assertEqual(len(result["scenarios"]), 9)

    def test_bounds_and_negative_demand(self):
        low = self.catalog.compute_forecast("Москва", "Сочи", "2026-06-01", 0)
        high = self.catalog.compute_forecast("Москва", "Сочи", "2026-06-01", 100000)
        self.assertEqual(low["sold"], 900)
        self.assertGreater(low["wish"], 900)
        self.assertTrue(low["capped_by_seats"])
        self.assertLess(high["wish"], 0)
        self.assertEqual(high["sold"], 0)
        self.assertFalse(high["capped_by_seats"])

    def test_floor_before_rounding(self):
        result = self.catalog.compute_forecast("Москва", "Сочи", "2026-06-01", 9000.001)
        self.assertEqual(result["wish"], 775)
        self.assertEqual(result["sold"], 774)
        self.assertEqual(result["scenarios"][4]["sold"], 774)

    def test_all_flights_and_price_boundaries(self):
        for (code, day), flight in self.catalog.flights.items():
            route = self.catalog.routes[code]
            for price in (0, route["base_price"], route["price_max"] * 10):
                with self.subTest(route=code, day=day, price=price):
                    result = self.catalog.compute_forecast(route["origin"], route["destination"], day, price)
                    self.assertTrue(0 <= result["sold"] <= flight["seats"])
                    demands = [s["wish"] for s in result["scenarios"]]
                    self.assertEqual(demands, sorted(demands))
                    self.assertEqual(result["wish"], result["scenarios"][4]["wish"])

    def test_bad_inputs(self):
        for value in (None, "", -1, True, float("nan"), float("inf"), {}, []):
            with self.subTest(price=value), self.assertRaises(ForecastError):
                self.catalog.compute_forecast("Москва", "Сочи", "2026-06-01", value)
        for day in (None, "2026-02-30", "20260601", "2026-06-01T00:00", "2027-01-01"):
            with self.subTest(day=day), self.assertRaises(ForecastError):
                self.catalog.compute_forecast("Москва", "Сочи", day, 9000)
        for origin, destination in (("Москва", "Москва"), ("Париж", "Сочи"), (None, "Сочи")):
            with self.subTest(pair=(origin, destination)), self.assertRaises(ForecastError):
                self.catalog.compute_forecast(origin, destination, "2026-06-01", 9000)

    def test_missing_and_broken_flights(self):
        for replacement, expected in (({}, 404), ({("MOW-AER", "2026-06-01"): None}, 422)):
            flights = dict(self.catalog.flights)
            flights.pop(("MOW-AER", "2026-06-01"))
            flights.update(replacement)
            catalog = Catalog(self.catalog.routes, flights)
            with self.assertRaises(ForecastError) as caught:
                catalog.compute_forecast("Москва", "Сочи", "2026-06-01", 9000)
            self.assertEqual(caught.exception.status, expected)

    def test_dates_follow_replacement_dataset(self):
        catalog = Catalog(self.catalog.routes, {("MOW-AER", "2030-01-02"): self.catalog.flights[("MOW-AER", "2026-06-01")]})
        self.assertEqual(catalog.get_meta()["date_min"], "2030-01-02")
        self.assertEqual(catalog.compute_forecast("Москва", "Сочи", "2030-01-02", 9000)["sold"], 775)
        with self.assertRaisesMessage(ForecastError, "02.01.2030"):
            catalog.compute_forecast("Москва", "Сочи", "2026-06-01", 9000)

    def test_csv_corruption_and_missing_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "forecast.csv"
            with (settings.BASE_DIR / "data/seasonal_forecast.csv").open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                rows, fields = list(reader), reader.fieldnames
            rows[0]["0.5_base_demand"] = "NaN"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
            with self.assertLogs("forecast.services", level="WARNING"):
                catalog = load_data(path, settings.ROUTES_CSV_PATH)
            self.assertIsNone(catalog.flights[("MOW-AER", "2026-06-01")])
            self.assertIsNotNone(catalog.flights[("MOW-AER", "2026-06-02")])
            path.write_text("route,date\nMOW-AER,2026-06-01\n", encoding="utf-8")
            with self.assertRaisesMessage(ValueError, "отсутствуют колонки"):
                load_data(path, settings.ROUTES_CSV_PATH)


class ForecastAPITests(TestCase):

    def post(self, data=PARAMS):
        return self.client.post("/api/forecast/", data=json.dumps(data), content_type="application/json")

    def test_guest_meta_and_forecast(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        meta = self.client.get("/api/meta/").json()
        self.assertEqual((len(meta["pairs"]), meta["date_min"], meta["date_max"]), (5, "2026-06-01", "2026-07-01"))
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sold"], 634)
        self.assertFalse(Calculation.objects.exists())

    def test_json_errors_and_status(self):
        for body in ("[1]", "{", "null"):
            response = self.client.post("/api/forecast/", data=body, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("message", response.json()["error"])
        self.assertEqual(self.post({**PARAMS, "price": -1}).status_code, 400)
        original = get_catalog()
        bad = Catalog(original.routes, {**original.flights, ("MOW-AER", "2026-06-01"): None})
        with patch("forecast.views.get_catalog", return_value=bad):
            self.assertEqual(self.post().status_code, 422)
        with patch("forecast.views.get_catalog", side_effect=ValueError("bad config")):
            with self.assertLogs("forecast.views", level="ERROR"):
                self.assertEqual(self.post().status_code, 503)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/api/forecast/", data=json.dumps(PARAMS), content_type="application/json").status_code, 403)
        client.get("/")
        response = client.post("/api/forecast/", data=json.dumps(PARAMS), content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_history_is_private_and_clear_is_scoped(self):
        first = User.objects.create_user("first@example.test", "test-only-password", name="Первый")
        second = User.objects.create_user("second@example.test", "test-only-password", name="Второй")
        self.assertEqual(self.client.get("/history/").status_code, 302)
        self.client.force_login(first)
        self.post()
        self.assertEqual(Calculation.objects.filter(user=first).count(), 1)
        self.client.force_login(second)
        self.assertContains(self.client.get("/history/"), "Выберите рейс и цену")
        self.post({**PARAMS, "price": 10001})
        self.assertEqual(Calculation.objects.filter(user=second).count(), 1)
        self.assertEqual(self.client.get("/history/clear/").status_code, 405)
        self.assertEqual(self.client.post("/history/clear/").status_code, 302)
        self.assertEqual(Calculation.objects.filter(user=first).count(), 1)
        self.assertFalse(Calculation.objects.filter(user=second).exists())

    def test_history_repeat_keeps_fractional_price(self):
        user = User.objects.create_user("fraction@example.test", "test-only-password", name="Тест")
        self.client.force_login(user)
        self.post({**PARAMS, "price": 9000.001})
        self.assertContains(self.client.get("/history/"), "price=9000.001")
