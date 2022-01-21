from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import Question


def add_trending(request):
    questions = (
        Question.objects
        .annotate(
            rating=Coalesce(Sum('votes__value'), 0),
        )
        .order_by('-rating', '-date_created')
        .values('pk', 'rating', 'title')
    )

    return {
        'trending': questions[:20],
    }
