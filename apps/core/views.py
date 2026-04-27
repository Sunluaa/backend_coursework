from django.shortcuts import render

from apps.surveys.selectors import get_public_surveys


def home(request):
    latest_surveys = get_public_surveys()[:6]
    return render(request, "core/home.html", {"latest_surveys": latest_surveys})
