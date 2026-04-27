from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import QuestionForm, SurveyForm, SurveyTakeForm
from .models import Choice, Question, Survey
from .selectors import get_public_surveys, get_published_survey_by_uuid, get_survey_results_data, get_user_surveys
from .services import (
    BusinessLogicError,
    close_survey,
    create_survey_response,
    ensure_survey_editable,
    publish_survey,
    validate_survey_can_be_answered,
)

CHOICE_QUESTION_TYPES = {Question.Type.SINGLE_CHOICE, Question.Type.MULTIPLE_CHOICE}
MAX_CHOICE_TEXTS = 11


def _client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _choice_texts_from_request(request: HttpRequest) -> list[str]:
    texts = request.POST.getlist("choice_texts")
    return texts or [""]


def _choice_texts_from_question(question: Question | None) -> list[str]:
    if question and question.needs_choices:
        texts = list(question.choices.order_by("order").values_list("text", flat=True))
        return texts or [""]
    return [""]


def _sync_question_choices(question: Question, choice_texts: list[str]) -> None:
    cleaned_texts = [text.strip() for text in choice_texts if text and text.strip()]

    if question.needs_choices and not cleaned_texts:
        raise BusinessLogicError("Для этого типа вопроса нужен минимум 1 вариант ответа.")

    if len(cleaned_texts) > MAX_CHOICE_TEXTS:
        raise BusinessLogicError(f"Можно добавить не больше {MAX_CHOICE_TEXTS} вариантов ответа.")

    question.choices.all().delete()

    if question.needs_choices:
        Choice.objects.bulk_create(
            [Choice(question=question, text=text, order=index + 1) for index, text in enumerate(cleaned_texts)]
        )


def _renumber_questions(survey: Survey, start: int = 1) -> None:
    questions = list(survey.questions.order_by("order", "id"))
    for order, question in enumerate(questions, start=start):
        question.order = order
    if questions:
        Question.objects.bulk_update(questions, ["order"])


def _question_form_context(form: QuestionForm, question: Question | None = None, choice_texts: list[str] | None = None):
    current_type = form.data.get("question_type") if form.is_bound else form["question_type"].value()
    if choice_texts is None:
        choice_texts = _choice_texts_from_question(question)
    return {
        "form": form,
        "choice_texts": choice_texts,
        "choice_builder_visible": current_type in CHOICE_QUESTION_TYPES,
        "rating_scale_visible": current_type == Question.Type.RATING,
    }


@login_required
def dashboard(request):
    base_queryset = Survey.objects.filter(author=request.user)
    stats = base_queryset.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Survey.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Survey.Status.DRAFT)),
        closed=Count("id", filter=Q(status=Survey.Status.CLOSED)),
        responses=Count("responses", distinct=True),
    )
    recent_surveys = get_user_surveys(request.user)[:5]
    return render(request, "surveys/dashboard.html", {"stats": stats, "recent_surveys": recent_surveys})


@login_required
def my_surveys(request):
    surveys = get_user_surveys(request.user)
    return render(request, "surveys/my_surveys.html", {"surveys": surveys})


@login_required
def survey_create(request):
    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.author = request.user
            survey.save()
            messages.success(request, "Опрос создан. Теперь добавьте вопросы.")
            return redirect("surveys:survey_edit", survey_id=survey.id)
    else:
        form = SurveyForm()
    return render(request, "surveys/survey_form.html", {"form": form, "title": "Создать опрос"})


@login_required
def survey_edit(request, survey_id):
    survey = get_object_or_404(Survey.objects.prefetch_related("questions__choices"), id=survey_id, author=request.user)
    try:
        ensure_survey_editable(survey, request.user)
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:my_surveys")

    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, "Опрос обновлен.")
            return redirect("surveys:survey_edit", survey_id=survey.id)
    else:
        form = SurveyForm(instance=survey)

    return render(request, "surveys/survey_edit.html", {"survey": survey, "form": form})


@login_required
def survey_delete(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, author=request.user)
    if request.method == "POST":
        survey.delete()
        messages.success(request, "Опрос удален.")
        return redirect("surveys:my_surveys")
    return render(request, "surveys/survey_confirm_delete.html", {"survey": survey})


@login_required
@require_POST
def survey_publish(request, survey_id):
    survey = get_object_or_404(Survey.objects.prefetch_related("questions__choices"), id=survey_id, author=request.user)
    try:
        publish_survey(survey, request.user)
        messages.success(request, "Опрос опубликован.")
        return redirect("surveys:my_surveys")
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:survey_edit", survey_id=survey.id)


@login_required
@require_POST
def survey_close(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, author=request.user)
    try:
        close_survey(survey, request.user)
        messages.success(request, "Опрос закрыт.")
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
    return redirect("surveys:my_surveys")


@login_required
def question_create(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, author=request.user)
    try:
        ensure_survey_editable(survey, request.user)
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:my_surveys")

    if request.method == "POST":
        form = QuestionForm(request.POST)
        choice_texts = _choice_texts_from_request(request)
        if form.is_valid():
            try:
                with transaction.atomic():
                    _renumber_questions(survey, start=2)
                    question = form.save(commit=False)
                    question.survey = survey
                    question.order = 1
                    question.save()
                    _sync_question_choices(question, choice_texts)
                messages.success(request, "Вопрос добавлен.")
                return redirect("surveys:survey_edit", survey_id=survey.id)
            except BusinessLogicError as exc:
                form.add_error(None, str(exc))
    else:
        form = QuestionForm()
        choice_texts = _choice_texts_from_question(None)

    context = {"survey": survey, "title": "Добавить вопрос"}
    context.update(_question_form_context(form, choice_texts=choice_texts))
    return render(request, "surveys/question_form.html", context)


@login_required
@require_POST
def questions_reorder(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, author=request.user)
    try:
        ensure_survey_editable(survey, request.user)
    except BusinessLogicError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=403)

    try:
        question_ids = [int(item) for item in request.POST.getlist("question_ids")]
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Некорректный порядок вопросов."}, status=400)

    existing_ids = list(survey.questions.values_list("id", flat=True))
    if len(question_ids) != len(existing_ids) or set(question_ids) != set(existing_ids):
        return JsonResponse({"ok": False, "error": "Список вопросов не совпадает с опросом."}, status=400)

    order_by_id = {question_id: index for index, question_id in enumerate(question_ids, start=1)}
    questions = list(Question.objects.filter(survey=survey, id__in=question_ids))
    for question in questions:
        question.order = order_by_id[question.id]

    Question.objects.bulk_update(questions, ["order"])
    return JsonResponse({"ok": True})


@login_required
def question_edit(request, question_id):
    question = get_object_or_404(Question.objects.select_related("survey"), id=question_id, survey__author=request.user)
    try:
        ensure_survey_editable(question.survey, request.user)
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:my_surveys")

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        choice_texts = _choice_texts_from_request(request)
        if form.is_valid():
            try:
                with transaction.atomic():
                    question = form.save()
                    _sync_question_choices(question, choice_texts)
                messages.success(request, "Вопрос обновлен.")
                return redirect("surveys:survey_edit", survey_id=question.survey_id)
            except BusinessLogicError as exc:
                form.add_error(None, str(exc))
    else:
        form = QuestionForm(instance=question)
        choice_texts = _choice_texts_from_question(question)

    context = {
        "survey": question.survey,
        "question": question,
        "title": "Редактировать вопрос",
    }
    context.update(_question_form_context(form, question=question, choice_texts=choice_texts))
    return render(request, "surveys/question_form.html", context)


@login_required
def question_delete(request, question_id):
    question = get_object_or_404(Question.objects.select_related("survey"), id=question_id, survey__author=request.user)
    try:
        ensure_survey_editable(question.survey, request.user)
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:my_surveys")

    if request.method == "POST":
        survey_id = question.survey_id
        question.delete()
        messages.success(request, "Вопрос удален.")
        return redirect("surveys:survey_edit", survey_id=survey_id)

    return render(request, "surveys/question_confirm_delete.html", {"question": question, "survey": question.survey})


def public_surveys(request):
    surveys = get_public_surveys()
    return render(request, "surveys/public_surveys.html", {"surveys": surveys})


def take_survey(request, survey_uuid):
    try:
        survey = get_published_survey_by_uuid(survey_uuid)
    except Survey.DoesNotExist as exc:
        raise Http404("Опрос не найден.") from exc

    try:
        validate_survey_can_be_answered(survey, request.user)
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:public_surveys")

    initial = {}
    if request.user.is_authenticated:
        initial["respondent_name"] = request.user.get_username()

    if request.method == "POST":
        form = SurveyTakeForm(survey, request.POST)
        if form.is_valid():
            try:
                create_survey_response(
                    survey=survey,
                    answers_data=form.get_answers_data(),
                    user=request.user,
                    respondent_name=form.cleaned_data.get("respondent_name", ""),
                    ip_address=_client_ip(request),
                )
                return redirect("surveys:thanks")
            except BusinessLogicError as exc:
                form.add_error(None, str(exc))
    else:
        form = SurveyTakeForm(survey, initial=initial)

    return render(request, "surveys/take_survey.html", {"survey": survey, "form": form})


def thanks(request):
    return render(request, "surveys/thanks.html")


@login_required
def survey_results(request, survey_id):
    survey = get_object_or_404(Survey.objects.prefetch_related("questions__choices"), id=survey_id, author=request.user)
    data = get_survey_results_data(survey)
    return render(request, "surveys/results.html", {"survey": survey, "results": data})
