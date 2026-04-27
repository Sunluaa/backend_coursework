from django import forms

from .models import Choice, Question, Survey


class RatingRangeInput(forms.NumberInput):
    input_type = "range"


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ("title", "description", "is_public", "allow_anonymous", "allow_multiple_submissions")
        labels = {
            "is_public": "Публичный доступ",
            "allow_anonymous": "Анонимные ответы",
            "allow_multiple_submissions": "Повторные ответы",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_public": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input survey-switch-input",
                    "role": "switch",
                    "aria-describedby": "id_is_public_help",
                }
            ),
            "allow_anonymous": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input survey-switch-input",
                    "role": "switch",
                    "aria-describedby": "id_allow_anonymous_help",
                }
            ),
            "allow_multiple_submissions": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input survey-switch-input",
                    "role": "switch",
                    "aria-describedby": "id_allow_multiple_submissions_help",
                }
            ),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ("text", "question_type", "rating_scale", "is_required")
        widgets = {
            "text": forms.TextInput(attrs={"class": "form-control"}),
            "question_type": forms.Select(attrs={"class": "form-select"}),
            "rating_scale": forms.Select(attrs={"class": "form-select"}),
            "is_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ("text", "order")
        widgets = {
            "text": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class SurveyTakeForm(forms.Form):
    def __init__(self, survey: Survey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey
        self.questions = list(survey.questions.prefetch_related("choices"))
        self.fields["respondent_name"] = forms.CharField(
            label="Ваше имя",
            required=False,
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Можно оставить пустым"}),
        )

        for question in self.questions:
            field_name = self._field_name(question)
            choices = [(choice.id, choice.text) for choice in question.choices.all()]

            if question.question_type == Question.Type.SINGLE_CHOICE:
                if not question.is_required:
                    choices = [("", "Не выбрано")] + choices
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    widget=forms.RadioSelect(attrs={"class": "choice-list"}),
                )
            elif question.question_type == Question.Type.MULTIPLE_CHOICE:
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-list"}),
                )
            elif question.question_type == Question.Type.TEXT:
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
                )
            elif question.question_type == Question.Type.RATING:
                rating_scale = question.rating_scale or Question.RatingScale.FIVE
                initial_rating = max(1, int(rating_scale) // 2 + int(rating_scale) % 2)
                self.fields[field_name] = forms.IntegerField(
                    label=question.text,
                    required=question.is_required,
                    min_value=1,
                    max_value=rating_scale,
                    initial=initial_rating,
                    widget=RatingRangeInput(
                        attrs={
                            "class": "rating-range-input",
                            "min": 1,
                            "max": rating_scale,
                            "step": 1,
                            "data-rating-scale": rating_scale,
                        }
                    ),
                )

    @staticmethod
    def _field_name(question: Question) -> str:
        return f"question_{question.id}"

    def get_answers_data(self) -> list[dict]:
        answers = []
        for question in self.questions:
            value = self.cleaned_data.get(self._field_name(question))
            payload = {"question_id": question.id}

            if question.question_type == Question.Type.SINGLE_CHOICE:
                payload["selected_choices"] = [int(value)] if value else []
            elif question.question_type == Question.Type.MULTIPLE_CHOICE:
                payload["selected_choices"] = [int(item) for item in value] if value else []
            elif question.question_type == Question.Type.TEXT:
                payload["text_answer"] = value or ""
            elif question.question_type == Question.Type.RATING:
                payload["rating_value"] = int(value) if value else None

            answers.append(payload)
        return answers
