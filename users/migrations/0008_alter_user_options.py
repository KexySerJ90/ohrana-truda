# Generated by Django 5.0.6 on 2024-07-29 12:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_subjectcompletion_study_completed'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'Пользователь', 'verbose_name_plural': 'Пользователи'},
        ),
    ]