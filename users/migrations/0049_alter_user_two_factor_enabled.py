# Generated by Django 5.1.3 on 2024-12-10 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0048_alter_otp_otp_secret'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='two_factor_enabled',
            field=models.BooleanField(default=False, verbose_name='Двухфакторная авторизация'),
        ),
    ]