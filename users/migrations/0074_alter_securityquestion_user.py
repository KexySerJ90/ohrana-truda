# Generated by Django 5.1.3 on 2024-12-26 11:57

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0073_alter_securityquestion_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='securityquestion',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='sec_user', to=settings.AUTH_USER_MODEL),
        ),
    ]