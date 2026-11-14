"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("auth-form"), errorBox = document.getElementById("auth-error");
  for (const field of form.querySelectorAll("input:not([type=hidden])")) {
    field.addEventListener("input", () => Avia.fieldError(field.name, ""));
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    Avia.showError(errorBox, "");
    let valid = true;
    for (const field of form.querySelectorAll("input[required]")) {
      const message = field.validity.valid ? "" : (field.validity.valueMissing ? "Заполните поле" : field.type === "email" ? "Укажите корректный email" : "Проверьте значение поля");
      Avia.fieldError(field.name, message);
      if (message) valid = false;
    }
    if (form.dataset.action === "register" && form.elements.password.value !== form.elements.password2.value) {
      Avia.fieldError("password2", "Пароли не совпадают"); valid = false;
    }
    if (!valid) { form.querySelector('[aria-invalid="true"]')?.focus(); return; }
    const button = form.querySelector('[type="submit"]'), original = button.innerHTML;
    button.disabled = true; button.textContent = "Подождите…";
    const data = Object.fromEntries(new FormData(form));
    delete data.csrfmiddlewaretoken;
    if (form.dataset.action === "login") data.remember = form.elements.remember.checked;
    try {
      await Avia.request(`/api/auth/${form.dataset.action}/`, data);

      location.assign("/history/");
    } catch (error) {
      Avia.showError(errorBox, error.message);
      for (const [name, messages] of Object.entries(error.fields || {})) Avia.fieldError(name, messages.join(". "));
      form.querySelector('[aria-invalid="true"]')?.focus();
    } finally { button.disabled = false; button.innerHTML = original; }
  });
});
