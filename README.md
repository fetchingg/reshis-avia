
## Запуск

Нужен Python 3.11+

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver 127.0.0.1:8877
```

Дальше открыть http://127.0.0.1:8877/. На Windows можно просто `.\run.ps1`
На Linux/macOS вместо `.venv\Scripts\python` — `.venv/bin/python`

`python manage.py runserver`


## Как считается

Для каждого квантиля X (0.1–0.9):

```
wish_X = X_base_demand − price_sensitivity × (price − base_price)
sold   = floor(min(seats, max(0, wish_0.5)))
```

«Хотят купить» - это медиана. Спрос не обрезается (может быть меньше нуля или больше вместимости), обрезаются только продажи. `seats` - вместимость из CSV, а не свободные места. Цены в рублях. Выход за `price_min`/`price_max` не запрещен, просто показывается предупреждение

## Структура

- `forecast/` - формула, чтение CSV, API, история
- `accounts/` - регистрация и вход по email
- `config/` - настройки
- `templates/`, `static/` - страницы, JS, CSS

API: `GET /api/meta/`, `POST /api/forecast/`, `POST /api/auth/{register,login,logout}/`, `GET /api/auth/me/`.

## Тесты

```
.venv\Scripts\python manage.py test
```

## Хостинг

https://reshis-avia-d04y.onrender.com


## Использованные ресурсы

Для разработки использовались нейросети: Claude, ChatGPT(codex)

Также некоторые файлы были написаны самостоятельно (в основном бэкенд)
