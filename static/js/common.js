
"use strict";
window.Avia = {
  async request(url, data) {

    const options = {credentials: "same-origin", mode: "same-origin", headers: {Accept: "application/json"}};
    if (data !== undefined) {
      const token = document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1];
      options.method = "POST";
      options.headers["Content-Type"] = "application/json";
      options.headers["X-CSRFToken"] = decodeURIComponent(token || "");
      options.body = JSON.stringify(data);
    }
    let response;
    try { response = await fetch(url, options); }
    catch { throw new Error("Нет связи с сервером. Проверьте соединение и повторите."); }
    let result;
    try { result = await response.json(); }
    catch { throw new Error("Сервер вернул неожиданный ответ. Попробуйте позже."); }
    if (!response.ok) {
      const error = new Error(result.error?.message || "Не удалось выполнить запрос");
      error.fields = result.error?.fields;
      throw error;
    }
    return result;
  },
  format(value, digits = 0) {

    return new Intl.NumberFormat("ru-RU", {maximumFractionDigits: digits}).format(value);
  },
  fieldError(name, message) {

    const field = document.getElementById(name), target = document.getElementById(`${name}-error`);
    if (field) field.setAttribute("aria-invalid", message ? "true" : "false");
    if (target) target.textContent = message || "";
  },
  showError(box, message) {
    box.textContent = message || "";
    box.hidden = !message;
  }
};
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("logout")?.addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    try { await Avia.request("/api/auth/logout/", {}); location.assign("/"); }
    catch (error) { Avia.showError(document.getElementById("global-message"), error.message); event.target.disabled = false; }
  });
  for (const button of document.querySelectorAll(".password-toggle")) {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.target), show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Скрыть" : "Показать";
      button.setAttribute("aria-label", show ? "Скрыть пароль" : "Показать пароль");
      button.setAttribute("aria-pressed", String(show));
    });
  }
  const dialog = document.getElementById("clear-history-dialog");
  document.getElementById("open-clear-history")?.addEventListener("click", () => dialog.showModal());
  document.getElementById("cancel-clear-history")?.addEventListener("click", () => dialog.close());
});
