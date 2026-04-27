from rest_framework.permissions import BasePermission

from .models import Choice, Question, Survey


class IsSurveyOwner(BasePermission):
    message = "Доступ разрешен только автору опроса."

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Survey):
            return obj.author_id == request.user.id
        return False


class IsDraftSurveyOwner(BasePermission):
    message = "Редактировать можно только свой опрос в статусе черновика."

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Survey):
            return obj.author_id == request.user.id and obj.can_be_edited()
        return False


class IsDraftQuestionOwner(BasePermission):
    message = "Изменять можно только вопросы своего черновика."

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Question):
            return obj.survey.author_id == request.user.id and obj.survey.can_be_edited()
        return False


class IsDraftChoiceOwner(BasePermission):
    message = "Изменять можно только варианты ответа своего черновика."

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Choice):
            return obj.question.survey.author_id == request.user.id and obj.question.survey.can_be_edited()
        return False
