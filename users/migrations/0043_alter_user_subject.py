# Generated by Django 5.1.3 on 2024-12-05 13:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0051_article_views'),
        ('users', '0042_user_last_activity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='subject',
            field=models.ManyToManyField(blank=True, related_name='subjs', to='main.subject', verbose_name='Предмет'),
        ),
    ]
