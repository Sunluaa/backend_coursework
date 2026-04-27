# Oprosnik

Oprosnik - веб-сервис для создания, публикации, прохождения и анализа опросов. Проект реализован на Django MVT: HTML-интерфейс работает на Django Templates, REST API - на Django REST Framework, документация API - через drf-spectacular.

## Стек технологий

- Python 3.13
- Django 5
- Django REST Framework
- PostgreSQL
- Django Templates
- Bootstrap 5
- стандартная Django Auth
- drf-spectacular / Swagger UI
- Docker и docker-compose
- Django TestCase

## Возможности сервиса

- регистрация, вход и выход пользователей;
- создание и удаление своих опросов;
- редактирование опросов, вопросов и вариантов только в статусе черновика;
- вопросы типов single choice, multiple choice, text и rating;
- публикация валидных опросов и закрытие опубликованных;
- публичный список опубликованных опросов;
- прохождение опросов гостями и авторизованными пользователями;
- запрет анонимного прохождения, если `allow_anonymous=False`;
- ограничение повторного прохождения для авторизованных пользователей;
- страница благодарности без показа результатов респонденту;
- результаты доступны только автору опроса;
- REST API и Swagger/OpenAPI;
- Django admin для управления данными;
- автоматические тесты бизнес-правил и API.

## Архитектура

Проект использует Django MVT как практическую реализацию MVC:

- `models.py` - модели и ORM;
- `views.py` - HTML-контроллеры;
- `templates/` - представления HTML;
- `forms.py` - формы HTML;
- `services.py` - бизнес-логика публикации, закрытия, прохождения и расчета результатов;
- `selectors.py` - выборки и агрегированные данные;
- `serializers.py` - преобразование данных REST API;
- `api_views.py` - API-контроллеры DRF;
- `permissions.py` - права доступа API.

HTML views и API views используют общие функции из `apps/surveys/services.py`.

## Структура проекта

```text
.
├── manage.py
├── requirements.txt
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── config/
├── apps/
│   ├── core/
│   ├── accounts/
│   └── surveys/
├── templates/
└── static/
```

## Переменные окружения

Скопируйте пример окружения:

```bash
cp .env.example .env
```

Основные переменные:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
POSTGRES_DB=oprosnik_db
POSTGRES_USER=oprosnik_user
POSTGRES_PASSWORD=oprosnik_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Для локального запуска без Docker укажите `POSTGRES_HOST=localhost`, если PostgreSQL запущен на вашей машине.

## Запуск через Docker

```bash
cp .env.example .env
docker-compose up --build
```

В другом терминале выполните миграции и создайте администратора:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

После запуска доступны:

- http://localhost:8000/
- http://localhost:8000/admin/
- http://localhost:8000/api/docs/

## Локальный запуск без Docker

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Для Windows:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python -m pip install waitress
```

## Миграции

```bash
python manage.py migrate
```

Миграция `apps/surveys/migrations/0001_initial.py` уже добавлена в проект.

## Создание суперпользователя

```bash
python manage.py createsuperuser
```

## Запуск тестов

```bash
python manage.py test
```

Во время запуска тестов проект использует SQLite test database, чтобы тесты можно было выполнить без поднятого PostgreSQL. Основной runtime проекта настроен на PostgreSQL через переменные окружения.

## Основные HTML URL

- `/` - главная страница;
- `/accounts/register/` - регистрация;
- `/accounts/login/` - вход;
- `/accounts/logout/` - выход;
- `/accounts/profile/` - личный кабинет;
- `/surveys/dashboard/` - панель пользователя;
- `/surveys/my/` - мои опросы;
- `/surveys/create/` - создание опроса;
- `/surveys/public/` - публичные опросы;
- `/surveys/take/<uuid>/` - прохождение опроса;
- `/surveys/<id>/results/` - результаты опроса для автора;
- `/admin/` - Django admin.

## Основные API endpoints

- `GET /api/surveys/public/`
- `GET /api/surveys/public/<uuid>/`
- `POST /api/surveys/public/<uuid>/submit/`
- `GET /api/surveys/my/`
- `POST /api/surveys/my/`
- `GET /api/surveys/my/<id>/`
- `PATCH /api/surveys/my/<id>/`
- `DELETE /api/surveys/my/<id>/`
- `POST /api/surveys/my/<id>/publish/`
- `POST /api/surveys/my/<id>/close/`
- `GET /api/surveys/my/<id>/results/`
- `POST /api/questions/`
- `PATCH /api/questions/<id>/`
- `DELETE /api/questions/<id>/`
- `POST /api/choices/`
- `PATCH /api/choices/<id>/`
- `DELETE /api/choices/<id>/`

## Swagger

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`

## Роли пользователей

- Гость: видит главную страницу и публичные опубликованные опросы, может проходить опросы с `allow_anonymous=True`.
- Пользователь: создает опросы, редактирует свои черновики, публикует, закрывает и удаляет свои опросы, смотрит результаты только своих опросов.
- Администратор: управляет данными через Django admin.
