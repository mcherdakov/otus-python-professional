# Generated by Django 3.2.9 on 2022-01-03 20:41

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('questions', '0004_auto_20220103_1255'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='answervote',
            unique_together={('user', 'answer')},
        ),
        migrations.AlterUniqueTogether(
            name='questionvote',
            unique_together={('user', 'question')},
        ),
    ]
