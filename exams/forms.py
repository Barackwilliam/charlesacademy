from django import forms
from .models import Exam, Result

# class ExamForm(forms.ModelForm):
#     class Meta:
#         model = Exam
#         fields = ['name', 'classroom', 'exam_type']

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'marks']




from classes.models import ClassRoom, Subject

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'classroom', 'exam_type', 'date', 'subject']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Exam name'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'exam_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
        }