from django import template

register = template.Library()


@register.inclusion_tag('questions/question_card.html')
def question_card(question):
    return {
        'question': question,
    }
