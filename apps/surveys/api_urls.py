from django.urls import path

from . import api_views


app_name = "surveys_api"

urlpatterns = [
    path("surveys/public/", api_views.PublicSurveyListAPIView.as_view(), name="public-surveys"),
    path("surveys/public/<uuid:uuid>/", api_views.PublicSurveyDetailAPIView.as_view(), name="public-survey-detail"),
    path(
        "surveys/public/<uuid:uuid>/submit/",
        api_views.PublicSurveySubmitAPIView.as_view(),
        name="public-survey-submit",
    ),
    path("surveys/my/", api_views.MySurveyListCreateAPIView.as_view(), name="my-surveys"),
    path("surveys/my/<int:pk>/", api_views.MySurveyDetailAPIView.as_view(), name="my-survey-detail"),
    path("surveys/my/<int:pk>/publish/", api_views.PublishSurveyAPIView.as_view(), name="my-survey-publish"),
    path("surveys/my/<int:pk>/close/", api_views.CloseSurveyAPIView.as_view(), name="my-survey-close"),
    path("surveys/my/<int:pk>/results/", api_views.SurveyResultsAPIView.as_view(), name="my-survey-results"),
    path("questions/", api_views.QuestionCreateAPIView.as_view(), name="question-create"),
    path("questions/<int:pk>/", api_views.QuestionDetailAPIView.as_view(), name="question-detail"),
    path("choices/", api_views.ChoiceCreateAPIView.as_view(), name="choice-create"),
    path("choices/<int:pk>/", api_views.ChoiceDetailAPIView.as_view(), name="choice-detail"),
]
