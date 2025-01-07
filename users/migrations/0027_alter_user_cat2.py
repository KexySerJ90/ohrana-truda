# Generated by Django 5.0.6 on 2024-11-07 11:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0046_alter_uploadfiles_file'),
        ('users', '0026_alter_user_cat2_alter_user_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='cat2',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cat2', to='main.departments', verbose_name='Отделение'),
        ),
    ]
