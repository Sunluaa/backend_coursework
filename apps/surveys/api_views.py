from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Choice, Question, Survey
from .permissions import IsDraftChoiceOwner, IsDraftQuestionOwner, IsDraftSurveyOwner, IsSurveyOwner
from .selectors import get_public_surveys, get_survey_results_data, get_user_surveys
from .serializers import (
    ChoiceSerializer,
    PublicSurveyDetailSerializer,
    PublicSurveyListSerializer,
    QuestionSerializer,
    SurveySerializer,
    SurveySubmitSerializer,
)
from .services import (
    BusinessLogicError,
    close_survey,
    create_survey_response,
    ensure_survey_editable,
    publish_survey,
    validate_survey_can_be_answered,
)


def _client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _raise_edit_error(survey: Survey, user) -> None:
    if survey.author_id != user.id:
        raise PermissionDenied("Доступ разрешен только автору.")
    try:
        ensure_survey_editable(survey, user)
    except BusinessLogicError as exc:
        raise ValidationError({"detail": str(exc)}) from exc


class PublicSurveyListAPIView(generics.ListAPIView):
    serializer_class = PublicSurveyListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_public_surveys()


class PublicSurveyDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PublicSurveyDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "uuid"

    def get_queryset(self):
        return get_public_surveys()


class PublicSurveySubmitAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=SurveySubmitSerializer,
        responses={
            200: OpenApiResponse(description="Survey response submitted successfully."),
            400: OpenApiResponse(description="Ошибка валидации ответов."),
            403: OpenApiResponse(description="Опрос недоступен для прохождения."),
        },
    )
    def post(self, request, uuid):
        survey = get_object_or_404(
            Survey.objects.prefetch_related("questions__choices"),
            uuid=uuid,
            status=Survey.Status.PUBLISHED,
            is_public=True,
        )

        try:
            validate_survey_can_be_answered(survey, request.user)
        except BusinessLogicError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        serializer = SurveySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            create_survey_response(
                survey=survey,
                answers_data=serializer.validated_data["answers"],
                user=request.user,
                respondent_name=serializer.validated_data.get("respondent_name", ""),
                ip_address=_client_ip(request),
            )
        except BusinessLogicError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Survey response submitted successfully."})


class MySurveyListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = SurveySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_user_surveys(self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MySurveyDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SurveySerializer
    permission_classes = [IsAuthenticated, IsSurveyOwner]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Survey.objects.filter(author=self.request.user).prefetch_related("questions__choices")

    def patch(self, request, *args, **kwargs):
        survey = self.get_object()
        self.check_object_permissions(request, survey)
        _raise_edit_error(survey, request.user)
        return self.partial_update(request, *args, **kwargs)


class PublishSurveyAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSurveyOwner]

    @extend_schema(responses={200: OpenApiResponse(description="Опрос опубликован.")})
    def post(self, request, pk):
        survey = get_object_or_404(Survey.objects.prefetch_related("questions__choices"), pk=pk, author=request.user)
        self.check_object_permissions(request, survey)
        try:
            publish_survey(survey, request.user)
        except BusinessLogicError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Опрос опубликован."})


class CloseSurveyAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSurveyOwner]

    @extend_schema(responses={200: OpenApiResponse(description="Опрос закрыт.")})
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk, author=request.user)
        self.check_object_permissions(request, survey)
        try:
            close_survey(survey, request.user)
        except BusinessLogicError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Опрос закрыт."})


class SurveyResultsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSurveyOwner]

    @extend_schema(responses={200: OpenApiResponse(description="Агрегированные результаты опроса.")})
    def get(self, request, pk):
        survey = get_object_or_404(Survey.objects.prefetch_related("questions__choices"), pk=pk, author=request.user)
        self.check_object_permissions(request, survey)
        data = get_survey_results_data(survey)
        return Response(
            {
                "survey": {
                    "id": survey.id,
                    "title": survey.title,
                    "status": survey.status,
                    "response_count": data["response_count"],
                },
                "questions": data["questions"],
            }
        )


class QuestionCreateAPIView(generics.CreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        survey = serializer.validated_data["survey"]
        _raise_edit_error(survey, self.request.user)
        serializer.save()


class QuestionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated, IsDraftQuestionOwner]
    http_method_names = ["patch", "delete", "head", "options"]

    def get_queryset(self):
        return Question.objects.select_related("survey").filter(survey__author=self.request.user)

    def patch(self, request, *args, **kwargs):
        question = self.get_object()
        self.check_object_permissions(request, question)
        _raise_edit_error(question.survey, request.user)
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        self.check_object_permissions(request, question)
        _raise_edit_error(question.survey, request.user)
        return self.destroy(request, *args, **kwargs)


class ChoiceCreateAPIView(generics.CreateAPIView):
    serializer_class = ChoiceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = serializer.validated_data["question"]
        _raise_edit_error(question.survey, self.request.user)
        if not question.needs_choices:
            raise ValidationError({"detail": "Для этого типа вопроса варианты ответа не используются."})
        serializer.save()


class ChoiceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChoiceSerializer
    permission_classes = [IsAuthenticated, IsDraftChoiceOwner]
    http_method_names = ["patch", "delete", "head", "options"]

    def get_queryset(self):
        return Choice.objects.select_related("question__survey").filter(question__survey__author=self.request.user)

    def patch(self, request, *args, **kwargs):
        choice = self.get_object()
        self.check_object_permissions(request, choice)
        _raise_edit_error(choice.question.survey, request.user)
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        choice = self.get_object()
        self.check_object_permissions(request, choice)
        _raise_edit_error(choice.question.survey, request.user)
        return self.destroy(request, *args, **kwargs)
