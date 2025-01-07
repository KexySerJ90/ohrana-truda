# Generated by Django 5.0.6 on 2024-08-14 13:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_remove_video_slug_answer'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='next_video',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_videos', to='main.video'),
        ),
        migrations.AlterField(
            model_name='answer',
            name='text',
            field=models.CharField(max_length=200),
        ),
    ]