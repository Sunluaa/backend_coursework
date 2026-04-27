from django.urls import path

from . import views


app_name = "surveys"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("my/", views.my_surveys, name="my_surveys"),
    path("create/", views.survey_create, name="survey_create"),
    path("<int:survey_id>/edit/", views.survey_edit, name="survey_edit"),
    path("<int:survey_id>/delete/", views.survey_delete, name="survey_delete"),
    path("<int:survey_id>/publish/", views.survey_publish, name="survey_publish"),
    path("<int:survey_id>/close/", views.survey_close, name="survey_close"),
    path("<int:survey_id>/questions/create/", views.question_create, name="question_create"),
    path("questions/<int:question_id>/edit/", views.question_edit, name="question_edit"),
    path("questions/<int:question_id>/delete/", views.question_delete, name="question_delete"),
    path("questions/<int:question_id>/choices/", views.choices_manage, name="choices_manage"),
    path("public/", views.public_surveys, name="public_surveys"),
    path("take/<uuid:survey_uuid>/", views.take_survey, name="take_survey"),
    path("thanks/", views.thanks, name="thanks"),
    path("<int:survey_id>/results/", views.survey_results, name="survey_results"),
]
