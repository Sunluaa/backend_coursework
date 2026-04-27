from rest_framework import serializers

from .models import Choice, Question, Survey


class ChoiceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "order")


class QuestionReadSerializer(serializers.ModelSerializer):
    choices = ChoiceReadSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "question_type", "is_required", "order", "choices")


class SurveySerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    questions = QuestionReadSerializer(many=True, read_only=True)
    questions_count = serializers.IntegerField(read_only=True)
    responses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Survey
        fields = (
            "id",
            "uuid",
            "title",
            "description",
            "author",
            "status",
            "is_public",
            "allow_anonymous",
            "allow_multiple_submissions",
            "created_at",
            "updated_at",
            "published_at",
            "closed_at",
            "questions_count",
            "responses_count",
            "questions",
        )
        read_only_fields = (
            "id",
            "uuid",
            "author",
            "status",
            "created_at",
            "updated_at",
            "published_at",
            "closed_at",
            "questions_count",
            "responses_count",
            "questions",
        )


class PublicSurveyListSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    questions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Survey
        fields = ("id", "uuid", "title", "description", "author", "published_at", "questions_count")


class PublicSurveyDetailSerializer(serializers.ModelSerializer):
    questions = QuestionReadSerializer(many=True, read_only=True)

    class Meta:
        model = Survey
        fields = (
            "id",
            "uuid",
            "title",
            "description",
            "allow_anonymous",
            "allow_multiple_submissions",
            "published_at",
            "questions",
        )


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceReadSerializer(many=True, read_only=True)
    survey = serializers.PrimaryKeyRelatedField(queryset=Survey.objects.all())

    class Meta:
        model = Question
        fields = ("id", "survey", "text", "question_type", "is_required", "order", "created_at", "choices")
        read_only_fields = ("id", "created_at", "choices")

    def validate(self, attrs):
        if self.instance and "survey" in attrs and attrs["survey"].id != self.instance.survey_id:
            raise serializers.ValidationError({"survey": "Нельзя переносить вопрос в другой опрос."})
        return attrs


class ChoiceSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.select_related("survey").all())

    class Meta:
        model = Choice
        fields = ("id", "question", "text", "order")
        read_only_fields = ("id",)

    def validate(self, attrs):
        if self.instance and "question" in attrs and attrs["question"].id != self.instance.question_id:
            raise serializers.ValidationError({"question": "Нельзя переносить вариант ответа в другой вопрос."})
        return attrs


class AnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_choices = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    text_answer = serializers.CharField(required=False, allow_blank=True)
    rating_value = serializers.IntegerField(required=False, allow_null=True)


class SurveySubmitSerializer(serializers.Serializer):
    respondent_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    answers = AnswerInputSerializer(many=True)
