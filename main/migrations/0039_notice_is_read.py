# Generated by Django 5.0.6 on 2024-08-30 06:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0038_notice'),
    ]

    operations = [
        migrations.AddField(
            model_name='notice',
            name='is_read',
            field=models.BooleanField(default=False, verbose_name='Прочитано'),
        ),
    ]
