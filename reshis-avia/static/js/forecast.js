"use strict";
document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("forecast-form"), button = document.getElementById("calculate");
  const origin = form.elements.origin, destination = form.elements.destination, date = form.elements.date, price = form.elements.price;
  const errorBox = document.getElementById("error-box"), result = document.getElementById("result");
  const resultSection = document.getElementById("results-section"), resetPrice = document.getElementById("reset-price");
  let meta, chart, busy = false;
  const query = new URLSearchParams(location.search);

  function selectedPair() {

    return meta.pairs.find(pair => pair.origin === origin.value && pair.destination === destination.value);
  }
  function updatePrice() {

    const pair = selectedPair();
    price.value = pair.base_price;
    document.getElementById("price-hint").textContent = `Базовая цена: ${Avia.format(pair.base_price)} ₽ · диапазон модели: ${Avia.format(pair.price_min)}–${Avia.format(pair.price_max)} ₽`;
    date.min = pair.dates[0]; date.max = pair.dates.at(-1);
    if (!pair.dates.includes(date.value)) date.value = pair.dates[0];
  }
  function updateDestinations() {

    const old = destination.value;
    destination.replaceChildren(...meta.pairs.filter(pair => pair.origin === origin.value).map(pair => new Option(pair.destination, pair.destination)));
    if ([...destination.options].some(option => option.value === old)) destination.value = old;
    updatePrice();
  }
  function markChanged() {
    if (!result.hidden && !busy) document.getElementById("result-context").textContent = "Параметры изменены — нажмите «Рассчитать»";
  }
  function renderForecast(data) {
    document.getElementById("empty-state").hidden = true; result.hidden = false;
    for (const name of ["seats", "wish", "sold"]) document.getElementById(`${name}-value`).textContent = Avia.format(data[name], name === "wish" ? 1 : 0);
    document.getElementById("capacity-meter").style.width = `${Math.min(100, data.sold / data.seats * 100)}%`;
    document.getElementById("result-context").textContent = `${data.origin} → ${data.destination} · ${new Date(data.date + "T12:00:00").toLocaleDateString("ru-RU")} · ${Avia.format(data.price, 2)} ₽`;
    document.getElementById("result-note").textContent = data.capped_by_seats
      ? "Спрос выше вместимости. Прогноз продаж ограничен числом мест на рейсе."
      : data.wish <= 0 ? "При этой цене медианный спрос отсутствует. Отрицательные значения отражают линейную модель, продажи равны нулю."
      : `Не продано по прогнозу: ${Avia.format(data.remaining)} мест`;
    const warning = document.getElementById("range-warning");
    warning.hidden = !data.outside_price_range;
    warning.textContent = `Цена вне диапазона модели ${Avia.format(data.price_min)}–${Avia.format(data.price_max)} ₽. Расчёт выполнен по той же линейной формуле; интерпретируйте его осторожно.`;
    const table = document.getElementById("scenario-table"); table.replaceChildren();
    for (const scenario of data.scenarios) {
      const row = document.createElement("tr");
      if (scenario.quantile === 0.5) row.className = "median-row";
      for (const value of [`${Math.round(scenario.quantile * 100)}%${scenario.quantile === 0.5 ? " · медиана" : ""}`, Avia.format(scenario.wish, 1), Avia.format(scenario.sold)]) {
        const cell = document.createElement("td"); cell.textContent = value; row.append(cell);
      }
      table.append(row);
    }
    if (chart) chart.destroy();
    if (typeof Chart === "undefined") {
      document.querySelector(".chart-container").hidden = true;
      document.querySelector(".scenario-details").open = true;
      Avia.showError(errorBox, "График не загрузился. Точные значения доступны в таблице сценариев."); return;
    }
    chart = new Chart(document.getElementById("demand-chart"), {
      type: "bar",
      data: {labels: data.scenarios.map(s => `${Math.round(s.quantile * 100)}%`), datasets: [
        {label: "Спрос", data: data.scenarios.map(s => s.wish), backgroundColor: data.scenarios.map(s => s.quantile === 0.5 ? "#3378a7" : s.wish > data.seats ? "#be713c" : "#c4dbe9"), borderRadius: 7, maxBarThickness: 66, order: 2},
        {type: "line", label: "Вместимость", data: data.scenarios.map(() => data.seats), borderColor: "#7e8f9d", borderWidth: 1.5, borderDash: [6, 5], pointRadius: 0, fill: false, order: 1}
      ]},
      options: {responsive: true, maintainAspectRatio: false, animation: {duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 350},
        plugins: {legend: {display: false}, tooltip: {backgroundColor: "#263748", padding: 12, callbacks: {label: context => `${context.dataset.label}: ${Avia.format(context.parsed.y, 1)}`}}},
        scales: {x: {grid: {display: false}, border: {display: false}, ticks: {color: "#62788a", font: {size: 12}}}, y: {beginAtZero: data.scenarios.every(s => s.wish >= 0), border: {display: false}, grid: {color: "#edf2f6"}, ticks: {color: "#62788a", maxTicksLimit: 6}}}}
    });
  }

  try {
    meta = await Avia.request("/api/meta/");
    origin.replaceChildren(...meta.origins.map(city => new Option(city, city)));
    updateDestinations();
    const pair = meta.pairs.find(pair => pair.route === query.get("route"));
    if (pair) { origin.value = pair.origin; updateDestinations(); destination.value = pair.destination; updatePrice(); }
    if (query.get("date")) date.value = query.get("date");
    if (query.has("price") && query.get("price").trim() && Number.isFinite(Number(query.get("price"))) && Number(query.get("price")) >= 0) price.value = query.get("price");
    document.getElementById("dataset-summary").textContent = `${meta.pairs.length} маршрутов · ${new Date(meta.date_min + "T12:00:00").toLocaleDateString("ru-RU")} — ${new Date(meta.date_max + "T12:00:00").toLocaleDateString("ru-RU")}`;
    for (const field of [origin, destination, date, price, button, resetPrice]) field.disabled = false;
  } catch (error) { Avia.showError(errorBox, error.message); document.getElementById("dataset-summary").textContent = "Данные временно недоступны"; }
  origin.addEventListener("change", () => { updateDestinations(); markChanged(); });
  destination.addEventListener("change", () => { updatePrice(); markChanged(); });
  resetPrice.addEventListener("click", () => { updatePrice(); markChanged(); Avia.fieldError("price", ""); });
  for (const field of [origin, destination, date, price]) field.addEventListener("input", () => { Avia.fieldError(field.name, ""); markChanged(); });
  form.addEventListener("submit", async event => {
    event.preventDefault(); if (!meta || busy) return;
    Avia.showError(errorBox, "");
    let valid = true;
    for (const field of [origin, destination, date, price]) {
      let message = field.validity.valid ? "" : field.validity.valueMissing ? "Заполните поле" : field === date ? `Выберите дату с ${date.min} по ${date.max}` : "Введите неотрицательную цену";
      if (field === price && (!Number.isFinite(Number(price.value)) || price.value.trim() === "")) message = "Введите неотрицательную цену";
      Avia.fieldError(field.name, message); if (message) valid = false;
    }
    if (!valid) { form.querySelector('[aria-invalid="true"]')?.focus(); return; }
    const payload = {origin: origin.value, destination: destination.value, date: date.value, price: Number(price.value)};
    busy = true; button.disabled = true; button.firstElementChild.textContent = "Считаем…"; resultSection.setAttribute("aria-busy", "true");
    for (const field of [origin, destination, date, price, resetPrice]) field.disabled = true;
    try {
      const data = await Avia.request("/api/forecast/", payload); renderForecast(data);
      const params = new URLSearchParams({route: data.route, date: data.date, price: data.price});
      history.replaceState(null, "", `/?${params}`);
      if (matchMedia("(max-width: 700px)").matches) resultSection.scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start"});
    } catch (error) {
      Avia.showError(errorBox, error.message);
      if (!result.hidden) document.getElementById("result-context").textContent = "Последний успешный расчёт — новые параметры не рассчитаны";
      for (const [name, messages] of Object.entries(error.fields || {})) Avia.fieldError(name, messages.join(". "));
    } finally {
      busy = false; button.disabled = false; button.firstElementChild.textContent = "Рассчитать"; resultSection.setAttribute("aria-busy", "false");
      for (const field of [origin, destination, date, price, resetPrice]) field.disabled = false;
    }
  });
});
