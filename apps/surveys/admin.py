from django.contrib import admin

from .models import Answer, Choice, Question, Survey, SurveyResponse


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("text", "question_type", "is_required", "order", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "is_public", "allow_anonymous", "created_at", "published_at")
    list_filter = ("status", "is_public", "allow_anonymous", "allow_multiple_submissions", "created_at")
    search_fields = ("title", "description", "author__username")
    readonly_fields = ("uuid", "created_at", "updated_at", "published_at", "closed_at")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "survey", "question_type", "is_required", "order")
    list_filter = ("question_type", "is_required", "survey__status")
    search_fields = ("text", "survey__title")
    readonly_fields = ("created_at",)
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "order")
    search_fields = ("text", "question__text", "question__survey__title")


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ("question", "text_answer", "rating_value")
    filter_horizontal = ("selected_choices",)


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("survey", "respondent", "respondent_name", "created_at", "ip_address")
    list_filter = ("created_at", "survey")
    search_fields = ("survey__title", "respondent__username", "respondent_name")
    readonly_fields = ("created_at",)
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("response", "question", "text_answer", "rating_value")
    list_filter = ("question__question_type",)
    search_fields = ("question__text", "text_answer")
    filter_horizontal = ("selected_choices",)
