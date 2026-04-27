from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Choice, Question, Survey, SurveyResponse
from .services import BusinessLogicError, calculate_survey_results, create_survey_response, publish_survey


class SurveyBusinessTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")

    def create_valid_survey(self, **kwargs):
        survey = Survey.objects.create(
            title=kwargs.pop("title", "Опрос"),
            description=kwargs.pop("description", "Описание"),
            author=kwargs.pop("author", self.author),
            **kwargs,
        )
        question = Question.objects.create(
            survey=survey,
            text="Выберите вариант",
            question_type=Question.Type.SINGLE_CHOICE,
            order=1,
        )
        first = Choice.objects.create(question=question, text="Первый", order=1)
        second = Choice.objects.create(question=question, text="Второй", order=2)
        return survey, question, first, second

    def test_authenticated_user_can_create_survey(self):
        self.client.login(username="author", password="pass12345")
        response = self.client.post(
            reverse("surveys:survey_create"),
            {
                "title": "Новый опрос",
                "description": "Описание",
                "is_public": "on",
                "allow_anonymous": "on",
                "allow_multiple_submissions": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        survey = Survey.objects.get(title="Новый опрос")
        self.assertEqual(survey.author, self.author)

    def test_empty_survey_cannot_be_published(self):
        survey = Survey.objects.create(title="Пустой", description="", author=self.author)

        with self.assertRaises(BusinessLogicError):
            publish_survey(survey, self.author)

    def test_valid_survey_can_be_published(self):
        survey, _, _, _ = self.create_valid_survey()

        publish_survey(survey, self.author)
        survey.refresh_from_db()

        self.assertEqual(survey.status, Survey.Status.PUBLISHED)
        self.assertIsNotNone(survey.published_at)

    def test_guest_can_submit_public_anonymous_survey(self):
        survey, question, first, _ = self.create_valid_survey(allow_anonymous=True)
        publish_survey(survey, self.author)

        response = self.client.post(
            reverse("surveys:take_survey", kwargs={"survey_uuid": survey.uuid}),
            {"respondent_name": "Гость", f"question_{question.id}": str(first.id)},
        )

        self.assertRedirects(response, reverse("surveys:thanks"))
        saved_response = SurveyResponse.objects.get(survey=survey)
        self.assertIsNone(saved_response.respondent)
        self.assertEqual(saved_response.respondent_name, "Гость")

    def test_guest_cannot_submit_when_anonymous_disabled(self):
        survey, _, _, _ = self.create_valid_survey(allow_anonymous=False)
        publish_survey(survey, self.author)

        response = self.client.get(reverse("surveys:take_survey", kwargs={"survey_uuid": survey.uuid}))

        self.assertRedirects(response, reverse("surveys:public_surveys"))
        self.assertEqual(SurveyResponse.objects.count(), 0)

    def test_user_cannot_edit_other_users_survey(self):
        survey, _, _, _ = self.create_valid_survey()
        self.client.login(username="other", password="pass12345")

        response = self.client.get(reverse("surveys:survey_edit", kwargs={"survey_id": survey.id}))

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_view_other_users_results(self):
        survey, _, _, _ = self.create_valid_survey()
        self.client.login(username="other", password="pass12345")

        response = self.client.get(reverse("surveys:survey_results", kwargs={"survey_id": survey.id}))

        self.assertEqual(response.status_code, 404)

    def test_api_submit_survey_response(self):
        survey, _, first, _ = self.create_valid_survey()
        publish_survey(survey, self.author)
        api_client = APIClient()

        response = api_client.post(
            reverse("surveys_api:public-survey-submit", kwargs={"uuid": survey.uuid}),
            {
                "respondent_name": "Иван",
                "answers": [{"question_id": first.question_id, "selected_choices": [first.id]}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SurveyResponse.objects.filter(survey=survey).count(), 1)

    def test_single_choice_statistics(self):
        survey, question, first, second = self.create_valid_survey()
        publish_survey(survey, self.author)
        create_survey_response(
            survey,
            [{"question_id": question.id, "selected_choices": [first.id]}],
            respondent_name="Первый респондент",
        )
        create_survey_response(
            survey,
            [{"question_id": question.id, "selected_choices": [second.id]}],
            respondent_name="Второй респондент",
        )

        results = calculate_survey_results(survey)
        choices = {choice["text"]: choice for choice in results["questions"][0]["choices"]}

        self.assertEqual(results["response_count"], 2)
        self.assertEqual(choices["Первый"]["count"], 1)
        self.assertEqual(choices["Первый"]["percentage"], 50)

    def test_published_survey_cannot_be_edited_via_api(self):
        survey, _, _, _ = self.create_valid_survey()
        publish_survey(survey, self.author)
        api_client = APIClient()
        api_client.force_authenticate(self.author)

        response = api_client.patch(
            reverse("surveys_api:my-survey-detail", kwargs={"pk": survey.id}),
            {"title": "Новое название"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        survey.refresh_from_db()
        self.assertEqual(survey.title, "Опрос")
