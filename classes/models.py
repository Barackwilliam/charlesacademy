#classes/models.py

from django.db import models


class ClassRoom(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    fee = models.PositiveIntegerField(default=30000)


class Subject(models.Model):
    name = models.CharField(max_length=100)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
