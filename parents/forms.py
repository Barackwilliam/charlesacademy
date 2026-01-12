from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Parent
from django.contrib.auth.models import User


class ParentLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username'
        }),
        label="Username or Email"
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        }),
        label="Password"
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Remember me"
    )


class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['full_name', 'phone', 'email', 'relationship', 'address', 'occupation', 'profile_picture']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+255123456789'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your@email.com'
            }),
            'relationship': forms.Select(attrs={
                'class': 'form-control'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your complete address'
            }),
            'occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your occupation (optional)'
            }),
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'phone': 'Phone Number',
            'email': 'Email Address',
            'relationship': 'Relationship to Student',
            'address': 'Residential Address',
            'occupation': 'Occupation',
            'profile_picture': 'Profile Picture',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email field required
        self.fields['email'].required = True


class UserUpdateForm(forms.ModelForm):
    """Form for updating User model"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True









from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re

User = get_user_model()

class ParentRegistrationForm(forms.ModelForm):
    """Form for parent registration"""
    
    # User fields
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        }),
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
        min_length=8,
        help_text='Password must be at least 8 characters long.'
    )
    
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    # Student linking fields
    student_registration_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student admission/registration number'
        }),
        help_text='Enter your child\'s admission number to link your account'
    )
    
    # Verification fields
    id_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'National ID/Passport Number'
        })
    )
    
    class Meta:
        model = Parent
        fields = [
            'full_name', 'phone', 'email', 'relationship', 
            'address', 'occupation', 'profile_picture'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'relationship': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'full_name': 'Full Name',
            'phone': 'Phone Number',
            'email': 'Email Address',
            'relationship': 'Relationship to Student',
            'address': 'Address',
            'occupation': 'Occupation',
            'profile_picture': 'Profile Picture (Optional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate password match
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        # Validate username uniqueness
        username = cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            self.add_error('username', "Username already exists. Please choose a different one.")
        
        # Validate email uniqueness
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            self.add_error('email', "Email already registered. Please use a different email or login.")
        
        # Validate phone format
        phone = cleaned_data.get('phone')
        if phone:
            phone_regex = r'^\+?1?\d{9,15}$'
            if not re.match(phone_regex, phone):
                self.add_error('phone', "Phone number must be entered in the format: '+255123456789'. Up to 15 digits allowed.")
        
        # Validate student registration number
        student_reg_no = cleaned_data.get('student_registration_number')
        if student_reg_no:
            from students.models import Student
            try:
                student = Student.objects.get(registration_number=student_reg_no)
                # Check if student already has parents
                if student.parents.count() >= 2:  # Assuming max 2 parents
                    self.add_error('student_registration_number', "This student already has the maximum number of parents registered.")
            except Student.DoesNotExist:
                self.add_error('student_registration_number', "Student not found. Please check the registration number.")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Create user first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            is_active=False,  # Parent accounts need admin approval
            user_type='PARENT'
        )
        
        # Save parent instance
        parent = super().save(commit=False)
        parent.user = user
        parent.full_name = self.cleaned_data['full_name']
        parent.phone = self.cleaned_data['phone']
        parent.email = self.cleaned_data['email']
        parent.relationship = self.cleaned_data['relationship']
        parent.address = self.cleaned_data['address']
        parent.occupation = self.cleaned_data.get('occupation', '')
        
        if commit:
            parent.save()
            self.save_m2m()
            
            # Link student
            student_reg_no = self.cleaned_data['student_registration_number']
            from students.models import Student
            try:
                student = Student.objects.get(registration_number=student_reg_no)
                parent.students.add(student)
            except Student.DoesNotExist:
                pass
        
        return parent


class ParentApprovalForm(forms.Form):
    """Form for admin to approve/reject parent registration"""
    APPROVAL_CHOICES = (
        ('APPROVE', 'Approve Registration'),
        ('REJECT', 'Reject Registration'),
    )
    
    action = forms.ChoiceField(
        choices=APPROVAL_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for rejection (optional)'
        }),
        required=False,
        help_text='Provide reason if rejecting registration'
    )
    
    send_email = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Send email notification to parent'
    )