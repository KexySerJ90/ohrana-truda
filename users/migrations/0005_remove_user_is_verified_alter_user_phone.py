# Generated by Django 5.0.6 on 2024-07-11 13:15

import phonenumber_field.modelfields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_user_is_verified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_verified',
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=20, null=True, region=None, verbose_name='Телефон'),
        ),
    ]