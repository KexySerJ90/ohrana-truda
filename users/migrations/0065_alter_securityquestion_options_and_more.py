# Generated by Django 5.1.3 on 2024-12-26 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0064_user_secret_answer_securityquestion'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='securityquestion',
            options={'ordering': ['-user'], 'verbose_name': 'Секретный вопрос', 'verbose_name_plural': 'Секретные вопросы'},
        ),
        migrations.AddField(
            model_name='securityquestion',
            name='previous_answer',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Предыдущий ответ'),
        ),
        migrations.AlterField(
            model_name='securityquestion',
            name='question',
            field=models.CharField(choices=[('pet_name', 'Как зовут Ваше любимое домашнее животное?'), ('mother_maiden_name', 'Какая девичья фамилия у Вашей матери?'), ('first_school', 'В какой школе Вы учились в первый раз?'), ('dream_vacation', 'Какое Ваше самое заветное место для отдыха?'), ('first_car', 'Какую машину Вы впервые водили?')], max_length=255, unique=True, verbose_name='Вопрос безопасности'),
        ),
    ]