
import csv
import logging
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)
QUANTILES = tuple(f"0.{n}" for n in range(1, 10))


class ForecastError(ValueError):

    def __init__(self, message, status=400, code="validation_error", field=None):
        super().__init__(message)
        self.status, self.code, self.field = status, code, field


@dataclass
class Catalog:

    routes: dict
    flights: dict

    def get_meta(self):
        dates = sorted(day for _, day in self.flights)
        pairs = []
        for code, route in self.routes.items():
            available = sorted(day for rt, day in self.flights if rt == code)
            if available:
                pairs.append({**route, "route": code, "dates": available})
        return {
            "origins": sorted({p["origin"] for p in pairs}),
            "destinations": sorted({p["destination"] for p in pairs}),
            "pairs": pairs, "date_min": dates[0], "date_max": dates[-1],
            "price_unit": "руб.",
        }

    def compute_forecast(self, origin, destination, date_iso, price):
        if not isinstance(origin, str) or not isinstance(destination, str) or not origin.strip() or not destination.strip():
            raise ForecastError("Выберите пункты отправления и назначения", field="destination")
        origin, destination = origin.strip(), destination.strip()
        if origin == destination:
            raise ForecastError("Пункты отправления и назначения должны отличаться", field="destination")
        code = next((code for code, route in self.routes.items()
                     if (route["origin"], route["destination"]) == (origin, destination)), None)
        if code is None:
            raise ForecastError("Такого направления нет в расписании", field="destination")
        try:
            if not isinstance(date_iso, str) or date.fromisoformat(date_iso).isoformat() != date_iso:
                raise ValueError
        except ValueError as exc:
            raise ForecastError("Укажите дату в формате ГГГГ-ММ-ДД", field="date") from exc
        meta = self.get_meta()
        if not meta["date_min"] <= date_iso <= meta["date_max"]:
            start = date.fromisoformat(meta["date_min"]).strftime("%d.%m.%Y")
            end = date.fromisoformat(meta["date_max"]).strftime("%d.%m.%Y")
            raise ForecastError(f"Дата должна быть с {start} по {end}", field="date")
        amount = number(price, "price", user_input=True)
        key = (code, date_iso)
        if key not in self.flights:
            raise ForecastError("На эту дату рейса нет в расписании", 404, "flight_not_found", "date")
        flight, route = self.flights[key], self.routes[code]
        if flight is None:
            raise ForecastError("Данные по этому рейсу временно недоступны", 422, "broken_flight_data")
        delta = Decimal(str(route["price_sensitivity"])) * (Decimal(str(amount)) - Decimal(str(route["base_price"])))
        raw = [Decimal(str(flight[q + "_base_demand"])) - delta for q in QUANTILES]
        scenarios = [{"quantile": float(q), "wish": round(float(wish), 1),
                      "sold": int(min(Decimal(flight["seats"]), max(Decimal(0), wish)))}
                     for q, wish in zip(QUANTILES, raw)]
        wish = scenarios[4]["wish"]
        sold = int(min(Decimal(flight["seats"]), max(Decimal(0), raw[4])))
        return {
            "route": code, "origin": origin, "destination": destination, "date": date_iso,
            "price": amount, "base_price": route["base_price"], "seats": flight["seats"],
            "wish": wish, "sold": sold, "remaining": flight["seats"] - sold,
            "capped_by_seats": raw[4] > flight["seats"], "scenarios": scenarios,
            "outside_price_range": not route["price_min"] <= amount <= route["price_max"],
            "price_min": route["price_min"], "price_max": route["price_max"],
        }


def number(value, label, user_input=False):
    try:
        if isinstance(value, bool) or value is None or value == "":
            raise ValueError
        result = float(value)
        if not math.isfinite(result) or result < 0:
            raise ValueError
        return result
    except (ValueError, TypeError, OverflowError) as exc:
        if user_input:
            raise ForecastError("Введите цену — неотрицательное число", field="price") from exc
        raise ValueError(f"Некорректное число в колонке {label}") from exc


def read_rows(path, required):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("В CSV отсутствуют колонки: " + ", ".join(sorted(missing)))
        rows = list(reader)
    if not rows:
        raise ValueError("CSV не содержит данных")
    return rows


def load_data(forecast_path, routes_path):
    routes, flights = {}, {}
    route_columns = ("route", "name", "base_price", "cost_per_passenger", "price_sensitivity", "price_min", "price_max")
    for row in read_rows(routes_path, route_columns):
        code = row["route"].strip()
        cities = row["name"].split(" — ", 1)
        if len(cities) != 2 or not all(city.strip() for city in cities) or not code or code in routes:
            raise ValueError("Повреждённый или повторяющийся маршрут в routes.csv")
        route = {field: number(row[field], field) for field in route_columns[2:]}
        if not route["price_min"] <= route["base_price"] <= route["price_max"] or route["price_sensitivity"] <= 0:
            raise ValueError("Неверные границы цены или чувствительность маршрута")
        routes[code] = {**route, "origin": cities[0].strip(), "destination": cities[1].strip()}
    pair_names = [(r["origin"], r["destination"]) for r in routes.values()]
    if len(set(pair_names)) != len(pair_names):
        raise ValueError("Разные маршруты имеют одинаковые города")
    fields = [q + suffix for q in QUANTILES for suffix in ("_base_demand", "_price", "_price_demand")]
    for row in read_rows(forecast_path, ["route", "date", "seats", *fields]):
        try:
            code = row["route"].strip()
            day = date.fromisoformat(row["date"]).isoformat()
            if code not in routes:
                raise ValueError("Неизвестный маршрут")
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("В прогнозе некорректный маршрут или дата") from exc
        key = (code, day)
        if key in flights:
            raise ValueError(f"Повтор рейса {code} на {day}")
        try:
            parsed = {field: number(row[field], field) for field in ["seats", *fields]}
            if not parsed["seats"].is_integer() or parsed["seats"] <= 0:
                raise ValueError("Вместимость должна быть положительным целым числом")
            demands = [parsed[q + "_base_demand"] for q in QUANTILES]
            if demands != sorted(demands):
                raise ValueError("Квантили спроса должны возрастать")
            parsed["seats"] = int(parsed["seats"])
            flights[key] = parsed
        except ValueError:
            logger.warning("Повреждены числовые данные рейса %s на %s", code, day)
            flights[key] = None
    return Catalog(routes, flights)
