# Generated by Django 5.1.3 on 2024-12-23 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0060_user_reserve_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='reserve_email',
            field=models.EmailField(blank=True, default='', max_length=254, null=True, verbose_name='Резервный Email'),
        ),
    ]