from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Question(models.Model):
    title = models.CharField(max_length=128)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.title


class Answer(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    is_correct = models.BooleanField()

    def __str__(self):
        return f'{self.author.username}:{self.question.title}'


class Vote(models.Model):
    UPVOTE = 1
    DOWNVOTE = -1
    VALUE_CHOICES = (
        (UPVOTE, "Upvote"),
        (DOWNVOTE, "Downvote"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.IntegerField(
        choices=VALUE_CHOICES,
    )

    class Meta:
        abstract = True


class QuestionVote(Vote):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='votes',
    )

    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return f'{self.user.username}:{self.question.title}'


class AnswerVote(Vote):
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name='votes',
    )

    class Meta:
        unique_together = ('user', 'answer')

    def __str__(self):
        return f'{self.user.username}:{self.answer.question.title}'
