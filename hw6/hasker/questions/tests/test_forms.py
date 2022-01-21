from django.test import TestCase

from questions.forms import CreateQuestionForm


class CreateQuestionFormTests(TestCase):
    def test_valid_form(self):
        form = CreateQuestionForm({
            'title': 'test',
            'text': 'test',
            'tags': ' a, b,c ',
        })
        self.assertTrue(form.is_valid())
        self.assertListEqual(form.cleaned_data['tags'], ['a', 'b', 'c'])

    def test_valid_one_tag(self):
        form = CreateQuestionForm({
            'title': 'test',
            'text': 'test',
            'tags': 'a',
        })
        self.assertTrue(form.is_valid())
        self.assertListEqual(form.cleaned_data['tags'], ['a'])

    def test_valid_no_tags(self):
        form = CreateQuestionForm({
            'title': 'test',
            'text': 'test',
            'tags': '',
        })
        self.assertTrue(form.is_valid())
        self.assertListEqual(form.cleaned_data['tags'], [])

    def test_invalid_too_many_tags(self):
        form = CreateQuestionForm({
            'title': 'test',
            'text': 'test',
            'tags': 'a,b,c,d',
        })
        self.assertFalse(form.is_valid())

    def test_empty_tags(self):
        form = CreateQuestionForm({
            'title': 'test',
            'text': 'test',
            'tags': 'a,b,,c',
        })
        self.assertTrue(form.is_valid())
        self.assertListEqual(form.cleaned_data['tags'], ['a', 'b', 'c'])
