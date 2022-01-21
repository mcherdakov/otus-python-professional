from django.conf import settings
from django.core.exceptions import PermissionDenied, BadRequest
from django.core.mail import send_mail
from django.db.models.expressions import OuterRef, Subquery
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from .forms import CreateQuestionForm, CreateAnswerForm
from .models import AnswerVote, Question, Tag, Answer, QuestionVote, Vote


def index_view(request):
    ordering = request.GET.get('ordering', 'new')
    questions = (
        Question.objects
        .prefetch_related('tags', 'answers')
        .annotate(
            rating=Coalesce(Sum('votes__value'), 0),
        )
    )
    if ordering == 'new':
        questions = questions.order_by('-date_created')
    elif ordering == 'hot':
        questions = questions.order_by('-rating', '-date_created')

    paginator = Paginator(questions.all(), 20)
    page_number = request.GET.get('page')

    # double annotation will lead to duplicates due to JOINs,
    # beacause we can't use distinct on Sum
    questions_page = paginator.get_page(page_number)
    for q in questions_page:
        q.answers_count = q.answers.count()

    return render(
        request=request,
        template_name='questions/index.html',
        context={
            'questions': questions_page,
            'ordering': ordering,
        }
    )


@login_required
def create_question_view(request):
    if request.method == 'POST':
        form = CreateQuestionForm(request.POST)
        if form.is_valid():
            tag_objects = [
                Tag.objects.get_or_create(name=tag_name)[0]
                for tag_name in form.cleaned_data['tags']
            ]

            question = Question.objects.create(
                title=form.cleaned_data['title'],
                content=form.cleaned_data['text'],
                author=request.user,
            )
            question.tags.set(tag_objects)

            return redirect('question', pk=question.pk)

    else:
        form = CreateQuestionForm()

    return render(request, 'questions/create_question.html', {'form': form})


def question_detail_view(request, pk):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            raise PermissionDenied()

        form = CreateAnswerForm(request.POST)
        if form.is_valid():
            question = Question.objects.get(pk=pk)
            answer = Answer.objects.create(
                question=question,
                content=form.cleaned_data['text'],
                author=request.user,
                is_correct=False,
            )
            html_content = answer.content.replace('\n', '<br>')
            html_message = f'{html_content}<br><a href={request.build_absolute_uri()}>Go to question</a>'
            plain_message = f'{answer.content}\nGo to question: {request.build_absolute_uri()}'
            send_mail(
                f'New answer in question "{question.title}"',
                plain_message,
                None,
                [Question.objects.get(pk=pk).author.email],
                html_message=html_message,
            )
    else:
        form = CreateAnswerForm()

    question_query = (
        Question.objects
        .prefetch_related('tags')
        .annotate(
            rating=Coalesce(Sum('votes__value'), 0),
        )
    )
    if request.user.is_authenticated:
        question_query = question_query.annotate(
            user_vote=Subquery(
                QuestionVote.objects.filter(
                    user=request.user,
                    question=OuterRef('pk'),
                ).values('value')[:1],
            )
        )
    question = get_object_or_404(question_query, pk=pk)

    answers_query = (
        Answer.objects
        .filter(question=question)
        .annotate(
            rating=Coalesce(Sum('votes__value'), 0),
        )
        .order_by('-rating', '-date_created')
    )
    if request.user.is_authenticated:
        answers_query = answers_query.annotate(
            user_vote=Subquery(
                AnswerVote.objects.filter(
                    user=request.user,
                    answer=OuterRef('pk'),
                ).values('value')[:1],
            )
        )
    paginator = Paginator(answers_query.all(), 30)
    page_number = request.GET.get('page')

    return render(
        request,
        'questions/question_detail.html',
        {
            'question': question,
            'answers': paginator.get_page(page_number),
            'form': form,
            'voted_best': answers_query.filter(is_correct=True).exists()
        }
    )


def vote_view(request):
    if not request.user.is_authenticated:
        # after login redirect back to question page
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.META.get('HTTP_REFERER')))

    obj_id = request.POST.get('pk')
    if request.POST.get('type') == 'question':
        model = QuestionVote
        filter_kwargs = {'question_id': obj_id}
    else:
        model = AnswerVote
        filter_kwargs = {'answer_id': obj_id}

    with transaction.atomic():
        vote = (
            model.objects
            .select_for_update()
            .filter(
                user=request.user,
                **filter_kwargs
            )
        )

        vote_value = Vote.UPVOTE if 'upvote' in request.POST else Vote.DOWNVOTE
        if vote.exists():
            if vote[0].value == vote_value:
                vote.delete()
            else:
                vote.update(value=Vote.UPVOTE if 'upvote' in request.POST else Vote.DOWNVOTE)
        else:
            model.objects.create(
                user=request.user,
                value=vote_value,
                **filter_kwargs,
            )

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def vote_best_view(request):
    answer_id = request.POST.get('pk')

    with transaction.atomic():
        answer = (
            Answer.objects
            .select_for_update()
            .select_related('question')
            .filter(id=answer_id)
        )
        if answer[0].question.author != request.user:
            raise PermissionDenied()

        possible_best = (
            Answer.objects
            .filter(
                question=answer[0].question,
                is_correct=True,
            )
            .exclude(id=answer_id)
        )
        if possible_best.exists():
            raise BadRequest

        answer.update(is_correct=not answer[0].is_correct)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def search_view(request):
    query = request.GET.get('q', '')

    questions = (
        Question.objects
        .prefetch_related('tags')
        .annotate(
            rating=Coalesce(Sum('votes__value', distinct=True), 0),
            answers_count=Count('answers', distinct=True),
        )
    )

    if query.startswith('tag:'):
        _, tag = query.split(':')
        questions = (
            questions
            .filter(tags__name=tag)
            .order_by('-rating', '-date_created')
        )
    else:
        vector = SearchVector('title', 'content')
        q = SearchQuery(query)
        questions = (
            questions
            .annotate(
                search=vector,
                rank=SearchRank(vector, q),
            )
            .filter(search=query)
            .order_by('-rank')
        )

    paginator = Paginator(questions.all(), 20)
    page = request.GET.get('page')

    return render(
        request,
        'questions/search.html',
        {
            'questions': paginator.get_page(page),
            'q': query,
        }
    )
