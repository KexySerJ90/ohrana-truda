# Generated by Django 5.1.3 on 2024-12-26 10:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0066_alter_securityquestion_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='secret_answer',
        ),
        migrations.AddField(
            model_name='securityquestion',
            name='answer',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Ответ'),
        ),
        migrations.AddField(
            model_name='securityquestion',
            name='previous_question',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Предыдущий Вопрос'),
        ),
        migrations.AlterField(
            model_name='securityquestion',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]