# Generated by Django 5.1.3 on 2024-12-05 13:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0044_user_two_factor_enabled_maildevice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='maildevice',
            name='verified',
        ),
    ]