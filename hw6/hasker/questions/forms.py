from django import forms
from django.core.exceptions import ValidationError


class TagsField(forms.CharField):
    def to_python(self, value):
        if not value:
            return []

        return [
            tag
            for tag in map(lambda v: v.strip(), value.split(','))
            if tag
        ]

    def validate(self, value):
        if len(value) > 3:
            raise ValidationError('Question must have at most 3 tags.')


class CreateQuestionForm(forms.Form):
    title = forms.CharField(label='Title', max_length=128)
    text = forms.CharField(
        label='Text',
        max_length=1024,
        widget=forms.Textarea,
    )
    tags = TagsField(label='Tags', max_length=256, required=False)


class CreateAnswerForm(forms.Form):
    text = forms.CharField(
        label='Text',
        max_length=1024,
        widget=forms.Textarea(
            attrs={
                'style': 'width: 100%;',
            },
        ),
    )
