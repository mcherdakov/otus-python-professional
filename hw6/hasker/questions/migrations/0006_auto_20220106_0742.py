# Generated by Django 3.2.9 on 2022-01-06 07:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0005_auto_20220103_2041'),
    ]

    operations = [
        migrations.AlterField(
            model_name='answer',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='question',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]