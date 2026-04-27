from django.db.models import Count

from .models import Survey
from .services import calculate_survey_results


def _survey_base_queryset():
    return (
        Survey.objects.select_related("author")
        .prefetch_related("questions__choices")
        .annotate(
            questions_count=Count("questions", distinct=True),
            responses_count=Count("responses", distinct=True),
        )
    )


def get_public_surveys():
    return _survey_base_queryset().filter(status=Survey.Status.PUBLISHED, is_public=True).order_by("-published_at")


def get_user_surveys(user):
    return _survey_base_queryset().filter(author=user).order_by("-created_at")


def get_survey_for_author(survey_id, user):
    return _survey_base_queryset().get(id=survey_id, author=user)


def get_published_survey_by_uuid(uuid):
    return _survey_base_queryset().get(uuid=uuid, status=Survey.Status.PUBLISHED)


def get_survey_results_data(survey):
    return calculate_survey_results(survey)
