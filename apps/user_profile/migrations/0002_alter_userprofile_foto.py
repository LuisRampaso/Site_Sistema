# Generated by Django 4.2.7 on 2023-12-01 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='foto',
            field=models.ImageField(blank=True, upload_to='perfil/foto/'),
        ),
    ]
