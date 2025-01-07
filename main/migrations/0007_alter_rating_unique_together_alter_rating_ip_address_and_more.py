# Generated by Django 5.0.6 on 2024-06-19 10:11

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_rating'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='rating',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='IP Адрес'),
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together={('post', 'user', 'ip_address')},
        ),
    ]
