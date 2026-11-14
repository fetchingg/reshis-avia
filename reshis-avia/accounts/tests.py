"""проверки регистрации стойкости паролей блокировки входа и тп"""
import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .models import LoginThrottle, User

PASSWORD = "Airline-study!47"
REGISTRATION = {"name": "Тестовый пользователь", "email": "pilot@example.test", "password": PASSWORD, "password2": PASSWORD}


class AccountTests(TestCase):

    def api(self, endpoint, data):
        return self.client.post(f"/api/auth/{endpoint}/", data=json.dumps(data), content_type="application/json")

    def test_register_email_case_and_password_hash(self):
        response = self.api("register", {**REGISTRATION, "email": "Pilot@Example.Test"})
        self.assertEqual(response.status_code, 201)
        user = User.objects.get()
        self.assertEqual(user.email, "pilot@example.test")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(self.client.get("/api/auth/me/").json()["user"]["email"], user.email)
        self.assertEqual(self.api("register", REGISTRATION).status_code, 409)

    def test_bad_registration(self):
        for data in ({**REGISTRATION, "password": "12345678", "password2": "12345678"}, {**REGISTRATION, "password2": "different"}, {**REGISTRATION, "email": "not-email"}, {**REGISTRATION, "name": ["bad"]}):
            with self.subTest(data_keys=list(data)), self.assertNumQueries(0):
                self.assertEqual(self.api("register", data).status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_login_remember_logout(self):
        User.objects.create_user(REGISTRATION["email"], PASSWORD, name="Тест")
        self.assertEqual(self.api("login", {"email": "PILOT@example.test", "password": PASSWORD, "remember": True}).status_code, 200)
        self.assertEqual(self.client.session.get_expiry_age(), 14 * 24 * 60 * 60)
        self.assertEqual(self.api("logout", {}).status_code, 200)
        self.assertIsNone(self.client.get("/api/auth/me/").json()["user"])
        self.assertEqual(self.api("logout", {}).status_code, 401)
        self.assertEqual(self.api("login", {"email": REGISTRATION["email"], "password": PASSWORD}).status_code, 200)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_limit_and_expiration(self):
        User.objects.create_user(REGISTRATION["email"], PASSWORD, name="Тест")
        for _ in range(5):
            self.assertEqual(self.api("login", {"email": REGISTRATION["email"], "password": "wrong"}).status_code, 400)
        locked = self.api("login", {"email": REGISTRATION["email"], "password": PASSWORD})
        self.assertEqual(locked.status_code, 429)
        self.assertIn("Retry-After", locked)
        LoginThrottle.objects.update(updated_at=timezone.now() - timedelta(minutes=6))
        self.assertEqual(self.api("login", {"email": REGISTRATION["email"], "password": PASSWORD}).status_code, 200)
        self.assertFalse(LoginThrottle.objects.exists())

    def test_csrf_registration_and_rotation(self):
        client = Client(enforce_csrf_checks=True)
        data = json.dumps(REGISTRATION)
        self.assertEqual(client.post("/api/auth/register/", data=data, content_type="application/json").status_code, 403)
        client.get("/register/")
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post("/api/auth/register/", data=data, content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 201)
        self.assertNotEqual(client.cookies["csrftoken"].value, token)
