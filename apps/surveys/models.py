import uuid

from django.contrib.auth.models import User
from django.db import models


class Survey(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликован"
        CLOSED = "closed", "Закрыт"

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    title = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="surveys", verbose_name="Автор")
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_public = models.BooleanField("Публичный", default=True)
    allow_anonymous = models.BooleanField("Разрешить гостевые ответы", default=True)
    allow_multiple_submissions = models.BooleanField("Разрешить повторные прохождения", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)
    published_at = models.DateTimeField("Опубликован", null=True, blank=True)
    closed_at = models.DateTimeField("Закрыт", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Опрос"
        verbose_name_plural = "Опросы"

    def __str__(self) -> str:
        return self.title

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def is_closed(self) -> bool:
        return self.status == self.Status.CLOSED

    def can_be_edited(self) -> bool:
        return self.is_draft


class Question(models.Model):
    class Type(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Один вариант"
        MULTIPLE_CHOICE = "multiple_choice", "Несколько вариантов"
        TEXT = "text", "Текстовый ответ"
        RATING = "rating", "Оценка"

    class RatingScale(models.IntegerChoices):
        FIVE = 5, "5 пунктов"
        TEN = 10, "10 пунктов"

    survey = models.ForeignKey(Survey, related_name="questions", on_delete=models.CASCADE, verbose_name="Опрос")
    text = models.TextField("Текст вопроса")
    question_type = models.CharField("Тип вопроса", max_length=30, choices=Type.choices)
    rating_scale = models.PositiveSmallIntegerField(
        "Шкала рейтинга",
        choices=RatingScale.choices,
        default=RatingScale.FIVE,
    )
    is_required = models.BooleanField("Обязательный", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self) -> str:
        return self.text

    @property
    def needs_choices(self) -> bool:
        return self.question_type in {self.Type.SINGLE_CHOICE, self.Type.MULTIPLE_CHOICE}


class Choice(models.Model):
    question = models.ForeignKey(Question, related_name="choices", on_delete=models.CASCADE, verbose_name="Вопрос")
    text = models.CharField("Текст варианта", max_length=255)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответа"

    def __str__(self) -> str:
        return self.text


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, related_name="responses", on_delete=models.CASCADE, verbose_name="Опрос")
    respondent = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="survey_responses",
        verbose_name="Респондент",
    )
    respondent_name = models.CharField("Имя респондента", max_length=150, blank=True)
    created_at = models.DateTimeField("Дата прохождения", auto_now_add=True)
    ip_address = models.GenericIPAddressField("IP-адрес", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Прохождение опроса"
        verbose_name_plural = "Прохождения опросов"

    def __str__(self) -> str:
        return f"{self.survey} - {self.created_at:%Y-%m-%d %H:%M}"


class Answer(models.Model):
    response = models.ForeignKey(SurveyResponse, related_name="answers", on_delete=models.CASCADE, verbose_name="Ответ")
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE, verbose_name="Вопрос")
    selected_choices = models.ManyToManyField(Choice, blank=True, verbose_name="Выбранные варианты")
    text_answer = models.TextField("Текстовый ответ", blank=True)
    rating_value = models.PositiveSmallIntegerField("Оценка", null=True, blank=True)

    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"

    def __str__(self) -> str:
        return f"Ответ на: {self.question}"
