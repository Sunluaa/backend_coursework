from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from django.utils import timezone

from .models import Answer, Choice, Question, Survey, SurveyResponse


class BusinessLogicError(Exception):
    """Ошибка нарушения бизнес-правил приложения."""


def _is_authenticated(user: User | AnonymousUser | None) -> bool:
    return bool(user and getattr(user, "is_authenticated", False))


def ensure_survey_owner(survey: Survey, user: User | AnonymousUser | None) -> None:
    """Проверяет, что пользователь является автором опроса."""
    if not _is_authenticated(user) or survey.author_id != user.id:
        raise BusinessLogicError("У вас нет прав для выполнения этого действия.")


def ensure_survey_editable(survey: Survey, user: User | AnonymousUser | None) -> None:
    """Проверяет право пользователя редактировать структуру опроса."""
    ensure_survey_owner(survey, user)
    if not survey.can_be_edited():
        raise BusinessLogicError("Редактировать можно только опросы в статусе черновика.")


def validate_survey_can_be_published(survey: Survey) -> None:
    """Проверяет, что черновик готов к публикации."""
    if not survey.is_draft:
        raise BusinessLogicError("Опубликовать можно только черновик.")

    questions = list(survey.questions.prefetch_related("choices"))
    if not questions:
        raise BusinessLogicError("Нельзя опубликовать опрос без вопросов.")

    for question in questions:
        if question.question_type in {Question.Type.SINGLE_CHOICE, Question.Type.MULTIPLE_CHOICE}:
            if question.choices.count() < 2:
                raise BusinessLogicError(
                    f'Для вопроса "{question.text}" нужно добавить минимум 2 варианта ответа.'
                )


def publish_survey(survey: Survey, user: User | AnonymousUser | None) -> Survey:
    """Публикует черновик опроса после проверки прав и структуры."""
    ensure_survey_owner(survey, user)
    validate_survey_can_be_published(survey)
    survey.status = Survey.Status.PUBLISHED
    survey.published_at = timezone.now()
    survey.save(update_fields=["status", "published_at", "updated_at"])
    return survey


def close_survey(survey: Survey, user: User | AnonymousUser | None) -> Survey:
    """Закрывает опубликованный опрос."""
    ensure_survey_owner(survey, user)
    if not survey.is_published:
        raise BusinessLogicError("Закрыть можно только опубликованный опрос.")
    survey.status = Survey.Status.CLOSED
    survey.closed_at = timezone.now()
    survey.save(update_fields=["status", "closed_at", "updated_at"])
    return survey


def validate_survey_can_be_answered(survey: Survey, user: User | AnonymousUser | None) -> None:
    """Проверяет, может ли пользователь пройти опрос."""
    if not survey.is_published:
        raise BusinessLogicError("Этот опрос сейчас недоступен для прохождения.")

    if not _is_authenticated(user):
        if not survey.allow_anonymous:
            raise BusinessLogicError("Этот опрос доступен только авторизованным пользователям.")
        return

    if not survey.allow_multiple_submissions and survey.responses.filter(respondent=user).exists():
        raise BusinessLogicError("Вы уже проходили этот опрос.")


def _percentage(count: int, total: int) -> float:
    return round((count / total) * 100, 2) if total else 0


def _to_int_list(value: Any) -> list[int]:
    if value in (None, ""):
        return []
    if isinstance(value, (str, int)):
        value = [value]
    try:
        return [int(item) for item in value if item not in (None, "")]
    except (TypeError, ValueError) as exc:
        raise BusinessLogicError("Некорректный формат выбранных вариантов ответа.") from exc


def validate_answer_payload(question: Question, answer_data: dict[str, Any]) -> dict[str, Any]:
    """Проверяет ответ на один вопрос и возвращает нормализованные данные."""
    question_label = f'Вопрос "{question.text}"'

    if question.question_type == Question.Type.SINGLE_CHOICE:
        selected_ids = _to_int_list(answer_data.get("selected_choices", []))
        if question.is_required and len(selected_ids) != 1:
            raise BusinessLogicError(f"{question_label}: выберите ровно один вариант ответа.")
        if not question.is_required and len(selected_ids) > 1:
            raise BusinessLogicError(f"{question_label}: можно выбрать не более одного варианта ответа.")
        allowed_ids = set(question.choices.values_list("id", flat=True))
        if any(choice_id not in allowed_ids for choice_id in selected_ids):
            raise BusinessLogicError(f"{question_label}: выбран вариант из другого вопроса.")
        return {"selected_choices": selected_ids, "text_answer": "", "rating_value": None}

    if question.question_type == Question.Type.MULTIPLE_CHOICE:
        selected_ids = _to_int_list(answer_data.get("selected_choices", []))
        if question.is_required and not selected_ids:
            raise BusinessLogicError(f"{question_label}: выберите хотя бы один вариант ответа.")
        allowed_ids = set(question.choices.values_list("id", flat=True))
        if any(choice_id not in allowed_ids for choice_id in selected_ids):
            raise BusinessLogicError(f"{question_label}: выбран вариант из другого вопроса.")
        return {"selected_choices": selected_ids, "text_answer": "", "rating_value": None}

    if question.question_type == Question.Type.TEXT:
        text_answer = str(answer_data.get("text_answer", "")).strip()
        if question.is_required and not text_answer:
            raise BusinessLogicError(f"{question_label}: текстовый ответ обязателен.")
        return {"selected_choices": [], "text_answer": text_answer, "rating_value": None}

    if question.question_type == Question.Type.RATING:
        raw_rating = answer_data.get("rating_value")
        rating_scale = question.rating_scale or Question.RatingScale.FIVE
        if raw_rating in (None, ""):
            if question.is_required:
                raise BusinessLogicError(f"{question_label}: укажите оценку от 1 до {rating_scale}.")
            return {"selected_choices": [], "text_answer": "", "rating_value": None}
        try:
            rating_value = int(raw_rating)
        except (TypeError, ValueError) as exc:
            raise BusinessLogicError(f"{question_label}: оценка должна быть числом от 1 до {rating_scale}.") from exc
        if rating_value < 1 or rating_value > rating_scale:
            raise BusinessLogicError(f"{question_label}: оценка должна быть от 1 до {rating_scale}.")
        return {"selected_choices": [], "text_answer": "", "rating_value": rating_value}

    raise BusinessLogicError("Неизвестный тип вопроса.")


@transaction.atomic
def create_survey_response(
    survey: Survey,
    answers_data: list[dict[str, Any]],
    user: User | AnonymousUser | None = None,
    respondent_name: str = "",
    ip_address: str | None = None,
) -> SurveyResponse:
    """Создает прохождение опроса и ответы на все его вопросы."""
    validate_survey_can_be_answered(survey, user)

    questions = list(survey.questions.prefetch_related("choices"))
    question_ids = {question.id for question in questions}
    payloads_by_question_id: dict[int, dict[str, Any]] = {}

    for raw_payload in answers_data:
        if "question_id" not in raw_payload:
            raise BusinessLogicError("Для каждого ответа нужен question_id.")
        try:
            question_id = int(raw_payload["question_id"])
        except (TypeError, ValueError) as exc:
            raise BusinessLogicError("question_id должен быть числом.") from exc
        if question_id in payloads_by_question_id:
            raise BusinessLogicError("Нельзя отправлять несколько ответов на один вопрос.")
        payloads_by_question_id[question_id] = raw_payload

    unknown_ids = set(payloads_by_question_id) - question_ids
    if unknown_ids:
        raise BusinessLogicError("Ответы должны относиться только к вопросам выбранного опроса.")

    respondent = user if _is_authenticated(user) else None
    response = SurveyResponse.objects.create(
        survey=survey,
        respondent=respondent,
        respondent_name=respondent_name.strip(),
        ip_address=ip_address,
    )

    for question in questions:
        normalized = validate_answer_payload(question, payloads_by_question_id.get(question.id, {}))
        answer = Answer.objects.create(
            response=response,
            question=question,
            text_answer=normalized["text_answer"],
            rating_value=normalized["rating_value"],
        )
        if normalized["selected_choices"]:
            answer.selected_choices.set(
                Choice.objects.filter(question=question, id__in=normalized["selected_choices"])
            )

    return response


def calculate_survey_results(survey: Survey) -> dict[str, Any]:
    """Считает агрегированные результаты опроса для автора."""
    response_count = survey.responses.count()
    questions_data: list[dict[str, Any]] = []

    for question in survey.questions.prefetch_related("choices"):
        item: dict[str, Any] = {
            "id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "question_type_display": question.get_question_type_display(),
            "is_required": question.is_required,
        }

        if question.question_type in {Question.Type.SINGLE_CHOICE, Question.Type.MULTIPLE_CHOICE}:
            raw_choices = []
            for choice in question.choices.all():
                count = Answer.objects.filter(question=question, selected_choices=choice).count()
                raw_choices.append({"id": choice.id, "text": choice.text, "count": count})

            choice_total = sum(choice["count"] for choice in raw_choices)
            item["choice_total"] = choice_total
            if question.question_type == Question.Type.MULTIPLE_CHOICE:
                item["choice_total_label"] = "Всего выборов"
                item["percentage_title"] = "Доля выборов"
            else:
                item["choice_total_label"] = "Ответов на вопрос"
                item["percentage_title"] = "Доля ответов"

            item["choices"] = [
                {
                    **choice,
                    "percentage": _percentage(choice["count"], choice_total),
                }
                for choice in raw_choices
            ]

        elif question.question_type == Question.Type.TEXT:
            item["text_answers"] = list(
                Answer.objects.filter(question=question)
                .exclude(text_answer="")
                .order_by("-response__created_at")
                .values_list("text_answer", flat=True)
            )

        elif question.question_type == Question.Type.RATING:
            rating_scale = question.rating_scale or Question.RatingScale.FIVE
            ratings = list(
                Answer.objects.filter(question=question, rating_value__isnull=False).values_list(
                    "rating_value", flat=True
                )
            )
            distribution = {value: ratings.count(value) for value in range(1, rating_scale + 1)}
            average = round(sum(ratings) / len(ratings), 2) if ratings else None
            item["average"] = average
            item["distribution"] = distribution
            item["rating_rows"] = [
                {"value": value, "count": count, "percentage": _percentage(count, len(ratings))}
                for value, count in distribution.items()
            ]
            item["rating_count"] = len(ratings)
            item["rating_scale"] = rating_scale

        questions_data.append(item)

    return {
        "survey": survey,
        "response_count": response_count,
        "questions": questions_data,
    }
