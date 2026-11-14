
from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import User


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=80)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(strip=False, max_length=128)
    password2 = forms.CharField(strip=False, max_length=128)

    def clean_email(self):
        return self.cleaned_data["email"].strip().casefold()

    def clean(self):

        data = super().clean()
        if data.get("password") and data.get("password2"):
            if data["password"] != data["password2"]:
                self.add_error("password2", "Пароли не совпадают")
            else:
                user = User(email=data.get("email", ""), name=data.get("name", ""))
                try:
                    validate_password(data["password"], user)
                except forms.ValidationError as exc:
                    self.add_error("password", exc)
        return data
