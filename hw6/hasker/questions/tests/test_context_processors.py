from django.test import TestCase

from questions.context_processors import add_trending
from questions.models import Question, QuestionVote
from users.models import User


class AddTrendingTests(TestCase):
    @staticmethod
    def _create_questions(author: User, questions: list[tuple[str, tuple[int]]]):
        vote_objects: list[QuestionVote] = []

        for title, votes in questions:
            q = Question.objects.create(
                title=title,
                content='',
                author=author,
            )

            for i, vote in enumerate(votes):
                user = User.objects.create(username=f'{title}{i}')
                vote_objects.append(
                    QuestionVote(
                        user=user,
                        value=vote,
                        question=q,
                    )
                )

        QuestionVote.objects.bulk_create(vote_objects)

    def test_no_questions(self):
        ctx = add_trending({})
        self.assertEqual(len(ctx['trending']), 0)

    def test_questions_without_votes(self):
        self._create_questions(
            User.objects.create(username='author'),
            [
                (f'test{i}', ())
                for i in range(10)
            ]
        )
        ctx = add_trending({})
        self.assertEqual(len(ctx['trending']), 10)

    def test_question_rating(self):
        self._create_questions(
            User.objects.create(username='author'),
            [(
                'test',
                (
                    QuestionVote.UPVOTE,
                    QuestionVote.DOWNVOTE,
                    QuestionVote.UPVOTE,
                )
            )]
        )
        ctx = add_trending({})
        q = ctx['trending'][0]

        self.assertEqual(q['title'], 'test')
        self.assertEqual(q['rating'], 1)

    def test_questions_limit(self):
        self._create_questions(
            User.objects.create(username='author'),
            [
                (f'test{i}', ())
                for i in range(21)
            ]
        )
        ctx = add_trending({})
        self.assertEqual(len(ctx['trending']), 20)

    def test_questions_ordering(self):
        self._create_questions(
            User.objects.create(username='author'),
            [
                ('test1', (QuestionVote.DOWNVOTE,)),
                ('test2', ()),
                ('test3', (QuestionVote.UPVOTE,)),
            ]
        )
        ctx = add_trending({})
        self.assertEqual(
            ['test3', 'test2', 'test1'],
            [q['title'] for q in ctx['trending']],
        )
