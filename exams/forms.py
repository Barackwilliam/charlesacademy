from django import forms
from .models import Exam, Result

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'classroom', 'exam_type']

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'marks']
