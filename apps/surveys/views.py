from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ChoiceForm, QuestionForm, SurveyForm, SurveyTakeForm
from .models import Choice, Question, Survey
from .selectors import get_public_survey_by_uuid, get_public_surveys, get_survey_results_data, get_user_surveys
from .services import (
    BusinessLogicError,
    close_survey,
    create_survey_response,
    ensure_survey_editable,
    publish_survey,
    validate_survey_can_be_answered,
)


def _client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


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
        if form.is_valid():
            question = form.save(commit=False)
            question.survey = survey
            question.save()
            messages.success(request, "Вопрос добавлен.")
            if question.needs_choices:
                return redirect("surveys:choices_manage", question_id=question.id)
            return redirect("surveys:survey_edit", survey_id=survey.id)
    else:
        next_order = survey.questions.count() + 1
        form = QuestionForm(initial={"order": next_order})

    return render(request, "surveys/question_form.html", {"form": form, "survey": survey, "title": "Добавить вопрос"})


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
        if form.is_valid():
            question = form.save()
            messages.success(request, "Вопрос обновлен.")
            if question.needs_choices:
                return redirect("surveys:choices_manage", question_id=question.id)
            return redirect("surveys:survey_edit", survey_id=question.survey_id)
    else:
        form = QuestionForm(instance=question)

    return render(
        request,
        "surveys/question_form.html",
        {"form": form, "survey": question.survey, "question": question, "title": "Редактировать вопрос"},
    )


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


@login_required
def choices_manage(request, question_id):
    question = get_object_or_404(
        Question.objects.select_related("survey").prefetch_related("choices"),
        id=question_id,
        survey__author=request.user,
    )
    try:
        ensure_survey_editable(question.survey, request.user)
    except BusinessLogicError as exc:
        messages.error(request, str(exc))
        return redirect("surveys:my_surveys")

    if not question.needs_choices:
        messages.info(request, "Для текстовых вопросов и рейтинга варианты ответа не используются.")
        return redirect("surveys:survey_edit", survey_id=question.survey_id)

    form = ChoiceForm()
    if request.method == "POST":
        delete_choice_id = request.POST.get("delete_choice_id")
        if delete_choice_id:
            choice = get_object_or_404(Choice, id=delete_choice_id, question=question)
            choice.delete()
            messages.success(request, "Вариант ответа удален.")
            return redirect("surveys:choices_manage", question_id=question.id)

        form = ChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save(commit=False)
            choice.question = question
            choice.save()
            messages.success(request, "Вариант ответа добавлен.")
            return redirect("surveys:choices_manage", question_id=question.id)

    return render(request, "surveys/choices_manage.html", {"question": question, "form": form})


def public_surveys(request):
    surveys = get_public_surveys()
    return render(request, "surveys/public_surveys.html", {"surveys": surveys})


def take_survey(request, survey_uuid):
    try:
        survey = get_public_survey_by_uuid(survey_uuid)
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
