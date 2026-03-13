from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0001_initial'),
        ('classes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentattendance',
            name='subject',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='classes.subject',
                verbose_name='Subject / Somo',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='studentattendance',
            unique_together={('student', 'date', 'subject')},
        ),
    ]
