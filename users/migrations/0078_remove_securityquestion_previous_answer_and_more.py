# Generated by Django 5.1.3 on 2024-12-30 08:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0077_alter_securityquestion_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="securityquestion",
            name="previous_answer",
        ),
        migrations.RemoveField(
            model_name="securityquestion",
            name="previous_question",
        ),
    ]