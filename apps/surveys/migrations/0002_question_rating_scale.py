from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="rating_scale",
            field=models.PositiveSmallIntegerField(
                choices=[(5, "5 пунктов"), (10, "10 пунктов")],
                default=5,
                verbose_name="Шкала рейтинга",
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("single_choice", "Один вариант"),
                    ("multiple_choice", "Несколько вариантов"),
                    ("text", "Текстовый ответ"),
                    ("rating", "Оценка"),
                ],
                max_length=30,
                verbose_name="Тип вопроса",
            ),
        ),
    ]
