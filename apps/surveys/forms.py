from django import forms

from .models import Choice, Question, Survey


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ("title", "description", "is_public", "allow_anonymous", "allow_multiple_submissions")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allow_anonymous": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allow_multiple_submissions": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ("text", "question_type", "is_required", "order")
        widgets = {
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "question_type": forms.Select(attrs={"class": "form-select"}),
            "is_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
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
                    widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
                )
            elif question.question_type == Question.Type.MULTIPLE_CHOICE:
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
                )
            elif question.question_type == Question.Type.TEXT:
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
                )
            elif question.question_type == Question.Type.RATING:
                rating_choices = [(value, str(value)) for value in range(1, 6)]
                if not question.is_required:
                    rating_choices = [("", "Не выбрано")] + rating_choices
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=rating_choices,
                    required=question.is_required,
                    widget=forms.RadioSelect(attrs={"class": "form-check-input rating-options"}),
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
