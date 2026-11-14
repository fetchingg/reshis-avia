"use strict";
document.addEventListener("DOMContentLoaded", () => {
  for (const select of document.querySelectorAll("#forecast-form select")) {
    const wrapper = document.createElement("div"); wrapper.className = "dropdown";
    select.before(wrapper); wrapper.append(select);
    const trigger = document.createElement("button");
    trigger.type = "button"; trigger.className = "dropdown-trigger"; trigger.id = `${select.id}-trigger`;
    trigger.setAttribute("role", "combobox"); trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false"); trigger.setAttribute("aria-controls", `${select.id}-options`);
    trigger.setAttribute("aria-describedby", select.getAttribute("aria-describedby") || "");
    const label = document.querySelector(`label[for="${select.id}"]`);
    if (label) { label.htmlFor = trigger.id; label.id = `${select.id}-label`; }
    const value = document.createElement("span"); value.id = `${select.id}-value`;
    trigger.setAttribute("aria-labelledby", `${label?.id || ""} ${value.id}`.trim());
    trigger.append(value);
    const menu = document.createElement("div"); menu.className = "dropdown-menu"; menu.id = `${select.id}-options`;
    menu.setAttribute("role", "listbox"); menu.setAttribute("aria-labelledby", label?.id || value.id); menu.hidden = true;
    wrapper.append(trigger, menu);
    select.classList.add("dropdown-native"); select.tabIndex = -1; select.setAttribute("aria-hidden", "true");
    let active = 0, search = "", searchTimer;

    function highlight(index) {

      const options = [...menu.children];
      active = Math.max(0, Math.min(index, options.length - 1));
      options.forEach((option, i) => option.classList.toggle("is-active", i === active));
      if (options[active]) {
        trigger.setAttribute("aria-activedescendant", options[active].id);
        if (!menu.hidden) options[active].scrollIntoView({block: "nearest"});
      }
    }
    function close() {

      menu.hidden = true; trigger.setAttribute("aria-expanded", "false"); trigger.removeAttribute("aria-activedescendant");
      wrapper.classList.remove("is-open");
    }
    function open() {

      if (trigger.disabled) return;
      menu.hidden = false; trigger.setAttribute("aria-expanded", "true"); wrapper.classList.add("is-open");
      const rect = trigger.getBoundingClientRect(), below = window.innerHeight - rect.bottom;
      const alignRight = rect.left + menu.offsetWidth > window.innerWidth - 12;
      menu.style.left = alignRight ? "auto" : "0"; menu.style.right = alignRight ? "0" : "auto";
      const above = below < Math.min(240, menu.scrollHeight) + 12 && rect.top > below;
      wrapper.classList.toggle("opens-up", above);
      menu.style.maxHeight = `${Math.max(80, Math.min(240, (above ? rect.top : below) - 16))}px`;
      highlight(select.selectedIndex);
    }
    function choose(index) {

      const option = select.options[index];
      if (!option || option.disabled) return;
      const changed = select.value !== option.value;
      select.value = option.value; close(); sync(); trigger.focus();
      if (changed) { select.dispatchEvent(new Event("input", {bubbles: true})); select.dispatchEvent(new Event("change", {bubbles: true})); }
    }
    function sync() {

      value.textContent = select.selectedOptions[0]?.textContent || "Выберите город";
      trigger.disabled = select.disabled;
      trigger.setAttribute("aria-invalid", select.getAttribute("aria-invalid") || "false");
      menu.replaceChildren(...[...select.options].map((option, index) => {
        const item = document.createElement("div"); item.className = "dropdown-option";
        item.id = `${select.id}-option-${index}`; item.dataset.index = index; item.setAttribute("role", "option");
        item.setAttribute("aria-selected", String(option.selected)); item.textContent = option.textContent;
        return item;
      }));
      if (select.disabled) close();
    }
    trigger.addEventListener("click", () => menu.hidden ? open() : close());
    trigger.addEventListener("keydown", event => {
      if (["ArrowDown", "ArrowUp", "Home", "End", "Enter", " ", "Escape"].includes(event.key)) event.preventDefault();
      if (event.key === "Escape" || event.key === "Tab") { close(); return; }
      if (event.key === "Enter" || event.key === " ") { menu.hidden ? open() : choose(active); return; }
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        const wasClosed = menu.hidden; if (wasClosed) open();
        if (event.key === "Home") highlight(0);
        else if (event.key === "End") highlight(select.options.length - 1);
        else if (!wasClosed) highlight(active + (event.key === "ArrowDown" ? 1 : -1));
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        search += event.key.toLocaleLowerCase("ru"); clearTimeout(searchTimer);
        searchTimer = setTimeout(() => { search = ""; }, 650);
        const index = [...select.options].findIndex(option => option.textContent.toLocaleLowerCase("ru").startsWith(search));
        if (index >= 0) { if (menu.hidden) open(); highlight(index); }
      }
    });
    menu.addEventListener("pointerdown", event => event.preventDefault());
    menu.addEventListener("click", event => {
      const option = event.target.closest(".dropdown-option"); if (option) choose(Number(option.dataset.index));
    });
    menu.addEventListener("pointermove", event => {
      const option = event.target.closest(".dropdown-option"); if (option) highlight(Number(option.dataset.index));
    });
    document.addEventListener("pointerdown", event => { if (!wrapper.contains(event.target)) close(); });
    document.addEventListener("focusin", event => { if (!wrapper.contains(event.target)) close(); });
    select.addEventListener("change", sync);
    select.addEventListener("focus", () => trigger.focus());
    new MutationObserver(sync).observe(select, {childList: true, subtree: true, attributes: true, attributeFilter: ["disabled", "aria-invalid"]});
    sync();
  }
});
