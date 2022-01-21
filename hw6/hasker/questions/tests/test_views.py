from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from users.models import User
from questions.models import AnswerVote, Question, QuestionVote, Answer, Tag


class IndexViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user1 = User.objects.create(username='user1')
        user2 = User.objects.create(username='user2')
        user3 = User.objects.create(username='user3')
        user4 = User.objects.create(username='user4')

        cls.q1 = Question.objects.create(title='title', content='content', author=user1)
        QuestionVote.objects.bulk_create(
            [
                QuestionVote(user=user2, question=cls.q1, value=QuestionVote.DOWNVOTE),
                QuestionVote(user=user3, question=cls.q1, value=QuestionVote.DOWNVOTE),
            ]
        )
        Answer.objects.create(
            question=cls.q1,
            content='',
            author=user2,
            is_correct=False,
        )

        cls.q2 = Question.objects.create(title='title', content='content', author=user2)
        QuestionVote.objects.bulk_create(
            [
                QuestionVote(user=user1, question=cls.q2, value=QuestionVote.DOWNVOTE),
                QuestionVote(user=user3, question=cls.q2, value=QuestionVote.UPVOTE),
            ]
        )

        cls.q3 = Question.objects.create(title='title', content='content', author=user3)
        QuestionVote.objects.bulk_create(
            [
                QuestionVote(user=user1, question=cls.q3, value=QuestionVote.UPVOTE),
                QuestionVote(user=user2, question=cls.q3, value=QuestionVote.UPVOTE),
            ]
        )

        cls.q4 = Question.objects.create(title='title', content='content', author=user4)

    def test_new_ordering(self):
        response = self.client.get(
            reverse('index') + '?ordering=new',
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        questions = response.context['questions']
        self.assertEqual(len(questions), 4)
        self.assertEqual(
            [self.q4.pk, self.q3.pk, self.q2.pk, self.q1.pk],
            [q.pk for q in questions]
        )

        self.assertEqual(response.context['ordering'], 'new')

    def test_hot_ordering(self):
        response = self.client.get(
            reverse('index') + '?ordering=hot',
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        questions = response.context['questions']
        self.assertEqual(len(questions), 4)
        self.assertEqual(
            [self.q3.pk, self.q4.pk, self.q2.pk, self.q1.pk],
            [q.pk for q in questions]
        )

        self.assertEqual(response.context['ordering'], 'hot')

    def test_question_data(self):
        response = self.client.get(
            reverse('index') + '?ordering=new',
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # must be q1
        question = response.context['questions'][-1]
        self.assertEqual(question.rating, -2)
        self.assertEqual(question.answers_count, 1)


class CreateQuestionViewTests(TestCase):
    def test_create_question_not_authenticated(self):
        response = self.client.post(
            reverse('create'),
            data={
                'title': 'test',
                'text': 'test_text',
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Question.objects.filter(title='test').exists())

    def test_create_question_with_tags(self):
        user = User.objects.create(username='test')
        self.client.force_login(user)
        response = self.client.post(
            reverse('create'),
            data={
                'title': 'test',
                'text': 'test_text',
                'tags': '1, 2, 3',
            },
        )
        # because of redirect to question page
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        q = Question.objects.filter(title='test')
        self.assertTrue(q.exists())
        q: Question = q.get()
        self.assertEqual(q.content, 'test_text')
        self.assertEqual(q.author, user)

        tags = q.tags.order_by('name').all()
        self.assertEqual(tags.count(), 3)
        for i, tag in enumerate(tags):
            self.assertEqual(tag.name, str(i + 1))


class QuestionDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='test')
        cls.q = Question.objects.create(
            author=cls.author,
            title='test',
            content='test',
        )

    def test_create_answer_not_authenticated(self):
        response = self.client.post(reverse('question', kwargs={'pk': self.q.pk}))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_create_answer(self):
        user = User.objects.create(username='user')
        self.client.force_login(user)
        response = self.client.post(
            reverse('question', kwargs={'pk': self.q.pk}),
            data={'text': 'test'},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        answer = Answer.objects.filter(question=self.q)
        self.assertTrue(answer.exists())
        answer: Answer = answer.get()
        self.assertEqual(answer.content, 'test')
        self.assertEqual(answer.author, user)
        self.assertFalse(answer.is_correct)

    def test_question_detail_context(self):
        user = User.objects.create(username='user')
        QuestionVote.objects.create(
            user=user,
            value=QuestionVote.UPVOTE,
            question=self.q,
        )

        answer = Answer.objects.create(
            question=self.q,
            content='test',
            author=user,
            is_correct=True,
        )
        AnswerVote.objects.create(
            answer=answer,
            user=user,
            value=AnswerVote.UPVOTE,
        )

        self.client.force_login(user)
        response = self.client.get(
            reverse('question', kwargs={'pk': self.q.pk}),
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        question = response.context['question']
        self.assertEqual(question.rating, 1)
        self.assertEqual(question.user_vote, QuestionVote.UPVOTE)

        answer = response.context['answers'][0]
        self.assertEqual(answer.rating, 1)
        self.assertEqual(answer.user_vote, AnswerVote.UPVOTE)

        self.assertTrue(response.context['voted_best'])


class VoteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='test')
        cls.question = Question.objects.create(
            author=cls.user,
            title='test',
            content='test',
        )
        cls.answer = Answer.objects.create(
            question=cls.question,
            content='test',
            author=cls.user,
            is_correct=False,
        )

    def test_user_not_authenticated(self):
        response = self.client.post(
            reverse('vote'),
            data={
                'type': 'question',
                'pk': self.question.pk,
                'upvote': '',
            }
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(QuestionVote.objects.filter(question=self.question).exists())

    def test_question_vote(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('vote'),
            data={
                'type': 'question',
                'pk': self.question.pk,
                'upvote': '',
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        vote = QuestionVote.objects.filter(question=self.question)
        self.assertTrue(vote.exists())
        vote: QuestionVote = vote.get()
        self.assertEqual(vote.user, self.user)
        self.assertEqual(vote.value, QuestionVote.UPVOTE)

    def test_answer_vote(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('vote'),
            data={
                'type': 'answer',
                'pk': self.answer.pk,
                'upvote': '',
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        vote = AnswerVote.objects.filter(answer=self.answer)
        self.assertTrue(vote.exists())
        vote: AnswerVote = vote.get()
        self.assertEqual(vote.user, self.user)
        self.assertEqual(vote.value, AnswerVote.UPVOTE)

    def test_vote_change(self):
        self.client.force_login(self.user)

        vote = AnswerVote.objects.create(
            user=self.user,
            answer=self.answer,
            value=AnswerVote.UPVOTE,
        )

        response = self.client.post(
            reverse('vote'),
            data={
                'type': 'answer',
                'pk': self.answer.pk,
                'downvote': '',
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        vote.refresh_from_db()
        self.assertEqual(vote.value, AnswerVote.DOWNVOTE)


class VoteBestViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='test')
        cls.question = Question.objects.create(
            author=cls.user,
            title='test',
            content='test',
        )
        cls.answer = Answer.objects.create(
            question=cls.question,
            content='test',
            author=cls.user,
            is_correct=False,
        )

    def test_vote_best_not_author(self):
        another_user = User.objects.create(username='another_user')
        self.client.force_login(another_user)
        response = self.client.post(
            reverse('vote_best'),
            data={
                'pk': self.answer.pk,
            }
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_vote_best(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('vote_best'),
            data={
                'pk': self.answer.pk,
            }
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.answer.refresh_from_db()
        self.assertTrue(self.answer.is_correct)

    def test_another_answer_best(self):
        Answer.objects.create(
            question=self.question,
            content='test',
            author=self.user,
            is_correct=True,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('vote_best'),
            data={
                'pk': self.answer.pk,
            }
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)


class SearchViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='test')
        tag1 = Tag.objects.create(name='hello')
        tag2 = Tag.objects.create(name='world')

        cls.q1 = Question.objects.create(
            author=cls.user,
            title='test',
            content='test',
        )
        cls.q1.tags.set([tag1])

        cls.q2 = Question.objects.create(
            author=cls.user,
            title='hello',
            content='world',
        )
        cls.q2.tags.set([tag2])

        cls.q3 = Question.objects.create(
            author=cls.user,
            title='test',
            content='We Live In A Big World!!!',
        )

    def test_tag_search(self):
        response = self.client.get(reverse('search') + '?q=tag:hello')
        self.assertEqual(response.status_code, HTTPStatus.OK)

        questions = response.context['questions']
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0], self.q1)

    def test_fulltext_search(self):
        response = self.client.get(reverse('search') + '?q=world')
        self.assertEqual(response.status_code, HTTPStatus.OK)

        questions = response.context['questions']
        self.assertEqual(len(questions), 2)
        # q2 must be ranked higher by SearchRank
        self.assertEqual(questions[0], self.q2)
        self.assertEqual(questions[1], self.q3)
