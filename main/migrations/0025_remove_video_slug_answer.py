# Generated by Django 5.0.6 on 2024-08-14 12:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_alter_video_slug'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='video',
            name='slug',
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=100)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='main.video')),
            ],
        ),
    ]