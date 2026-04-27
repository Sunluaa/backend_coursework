# Generated for the coursework project.
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Survey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=255, verbose_name="Название")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="surveys",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Автор",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Черновик"), ("published", "Опубликован"), ("closed", "Закрыт")],
                        default="draft",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                ("is_public", models.BooleanField(default=True, verbose_name="Публичный")),
                ("allow_anonymous", models.BooleanField(default=True, verbose_name="Разрешить гостевые ответы")),
                (
                    "allow_multiple_submissions",
                    models.BooleanField(default=True, verbose_name="Разрешить повторные прохождения"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлен")),
                ("published_at", models.DateTimeField(blank=True, null=True, verbose_name="Опубликован")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="Закрыт")),
            ],
            options={"verbose_name": "Опрос", "verbose_name_plural": "Опросы", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Текст вопроса")),
                (
                    "question_type",
                    models.CharField(
                        choices=[
                            ("single_choice", "Один вариант"),
                            ("multiple_choice", "Несколько вариантов"),
                            ("text", "Текстовый ответ"),
                            ("rating", "Оценка 1-5"),
                        ],
                        max_length=30,
                        verbose_name="Тип вопроса",
                    ),
                ),
                ("is_required", models.BooleanField(default=True, verbose_name="Обязательный")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                (
                    "survey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="surveys.survey",
                        verbose_name="Опрос",
                    ),
                ),
            ],
            options={"verbose_name": "Вопрос", "verbose_name_plural": "Вопросы", "ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Choice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=255, verbose_name="Текст варианта")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="surveys.question",
                        verbose_name="Вопрос",
                    ),
                ),
            ],
            options={
                "verbose_name": "Вариант ответа",
                "verbose_name_plural": "Варианты ответа",
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="SurveyResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("respondent_name", models.CharField(blank=True, max_length=150, verbose_name="Имя респондента")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата прохождения")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP-адрес")),
                (
                    "respondent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="survey_responses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Респондент",
                    ),
                ),
                (
                    "survey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="surveys.survey",
                        verbose_name="Опрос",
                    ),
                ),
            ],
            options={
                "verbose_name": "Прохождение опроса",
                "verbose_name_plural": "Прохождения опросов",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Answer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text_answer", models.TextField(blank=True, verbose_name="Текстовый ответ")),
                ("rating_value", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Оценка")),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="surveys.question",
                        verbose_name="Вопрос",
                    ),
                ),
                (
                    "response",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="surveys.surveyresponse",
                        verbose_name="Ответ",
                    ),
                ),
                ("selected_choices", models.ManyToManyField(blank=True, to="surveys.choice", verbose_name="Выбранные варианты")),
            ],
            options={"verbose_name": "Ответ на вопрос", "verbose_name_plural": "Ответы на вопросы"},
        ),
    ]
