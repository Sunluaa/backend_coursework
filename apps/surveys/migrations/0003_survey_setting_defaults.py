from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0002_question_rating_scale"),
    ]

    operations = [
        migrations.AlterField(
            model_name="survey",
            name="allow_anonymous",
            field=models.BooleanField(default=False, verbose_name="Разрешить гостевые ответы"),
        ),
        migrations.AlterField(
            model_name="survey",
            name="allow_multiple_submissions",
            field=models.BooleanField(default=False, verbose_name="Разрешить повторные прохождения"),
        ),
        migrations.AlterField(
            model_name="survey",
            name="is_public",
            field=models.BooleanField(default=False, verbose_name="Публичный"),
        ),
    ]
