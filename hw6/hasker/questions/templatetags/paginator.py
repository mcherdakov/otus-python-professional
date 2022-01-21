from django import template

register = template.Library()


@register.inclusion_tag('questions/paginator.html')
def paginator(pagination, **kwargs):
    params = '&'.join([f'{key}={value}' for key, value in kwargs.items()])
    return {
        'pagination': pagination,
        'link':  f'?{params}&' if params else '?',
    }
