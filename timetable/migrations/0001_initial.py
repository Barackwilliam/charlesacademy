from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('classes', '__first__'),
        ('exams', '__first__'),
        ('teachers', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimetableEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.CharField(choices=[('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'), ('THU', 'Thursday'), ('FRI', 'Friday')], max_length=3)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('room', models.CharField(blank=True, max_length=100)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timetable_entries', to='classes.classroom')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timetable_entries', to='classes.subject')),
                ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='timetable_entries', to='teachers.teacher')),
            ],
            options={
                'verbose_name': 'Timetable Entry',
                'verbose_name_plural': 'Timetable Entries',
                'ordering': ['day', 'start_time'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='timetableentry',
            unique_together={('classroom', 'day', 'start_time')},
        ),
    ]