# Generated by Django 5.0.6 on 2024-07-26 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_alter_slide_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadfiles',
            name='title',
            field=models.CharField(blank=True, db_index=True, max_length=200, verbose_name='Название файла'),
        ),
    ]