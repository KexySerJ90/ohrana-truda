# Generated by Django 5.0.6 on 2024-11-08 06:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_alter_user_cat2'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_social_user',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='patronymic',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Отчество (необязательное поле)'),
        ),
        migrations.AlterField(
            model_name='user',
            name='profession',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Профессия (необязательное поле)'),
        ),
    ]
