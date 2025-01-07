# Generated by Django 5.1.3 on 2024-12-26 12:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0076_remove_securityquestion_secret_answer_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='securityquestion',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
