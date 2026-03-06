from django.db import models


DAYS = [
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
]

# Colour per subject (cycles through these)
SUBJECT_COLOURS = [
    '#4361ee', '#7c3aed', '#10b981', '#f59e0b',
    '#ef4444', '#3b82f6', '#06b6d4', '#ec4899',
    '#8b5cf6', '#14b8a6',
]


class TimetableEntry(models.Model):
    classroom   = models.ForeignKey(
        'classes.ClassRoom', on_delete=models.CASCADE,
        related_name='timetable_entries'
    )
    subject     = models.ForeignKey(
        'classes.Subject', on_delete=models.CASCADE,
        related_name='timetable_entries'
    )
    teacher     = models.ForeignKey(
        'teachers.Teacher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='timetable_entries'
    )
    day         = models.CharField(max_length=3, choices=DAYS)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    room        = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['day', 'start_time']
        verbose_name        = 'Timetable Entry'
        verbose_name_plural = 'Timetable Entries'
        # prevent same class having two subjects at the same time/day
        unique_together = [('classroom', 'day', 'start_time')]

    def __str__(self):
        return f"{self.classroom} | {self.get_day_display()} {self.start_time:%H:%M} — {self.subject}"

    @property
    def time_label(self):
        return f"{self.start_time:%H:%M} – {self.end_time:%H:%M}"

    @property
    def colour(self):
        """Deterministic colour based on subject id."""
        return SUBJECT_COLOURS[self.subject_id % len(SUBJECT_COLOURS)]