# Generated by Django 5.1.3 on 2024-12-25 13:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0062_securityquestion'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SecurityQuestion',
        ),
    ]