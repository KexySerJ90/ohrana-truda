# Generated by Django 5.0.6 on 2024-09-05 06:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0041_remove_notification_comment_remove_notification_user_and_more'),
        ('users', '0018_remove_subjectcompletion_notice'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(verbose_name='Сообщение')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Время создания')),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notice', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Уведомление',
                'verbose_name_plural': 'Уведомления',
                'ordering': ['user', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Время создания')),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='main.comment', verbose_name='Комментарий')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Оповещение',
                'verbose_name_plural': 'Оповещения',
                'ordering': ['user', '-created_at'],
            },
        ),
    ]