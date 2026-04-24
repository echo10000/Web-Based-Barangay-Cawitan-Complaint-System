from django import forms
from django.contrib.auth.models import User
from .models import Complaint, ComplaintUpdate, Feedback, Category


class ComplaintForm(forms.ModelForm):
    """Form for citizens to file a new complaint"""
    
    class Meta:
        model = Complaint
        fields = ['title', 'description', 'category', 'location', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief title of your complaint'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Provide detailed information about your complaint',
                'rows': 5
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Where did this occur?'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class ComplaintUpdateForm(forms.ModelForm):
    """Form for staff to add updates to a complaint"""
    
    class Meta:
        model = ComplaintUpdate
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Add an update to this complaint',
                'rows': 4
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class FeedbackForm(forms.ModelForm):
    """Form for citizens to rate complaint resolution"""
    
    class Meta:
        model = Feedback
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any additional comments (optional)',
                'rows': 3
            }),
        }


class UserRegistrationForm(forms.ModelForm):
    """Form for user registration"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("Passwords do not match!")
        
        return cleaned_data
