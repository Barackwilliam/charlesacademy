# from django import forms
# from django.contrib.auth.models import User
# from datetime import date

# from .models import  SchoolSettings


# class SchoolSettingsForm(forms.ModelForm):
#     class Meta:
#         model = SchoolSettings
#         fields = ('name', 'logo', 'contact_email', 'phone', 'academic_year', 'theme_color')
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'logo': forms.FileInput(attrs={'class': 'form-control'}),
#             'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
#             'phone': forms.TextInput(attrs={'class': 'form-control'}),
#             'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
#             'theme_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
#         }







from django import forms
from .models import Announcement, SchoolSettings

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ('title', 'message')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter announcement title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter announcement message',
                'rows': 4
            }),
        }

class SchoolSettingsForm(forms.ModelForm):
    class Meta:
        model = SchoolSettings
        fields = ('name', 'logo', 'contact_email', 'phone', 'academic_year', 'theme_color')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
            'theme_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }