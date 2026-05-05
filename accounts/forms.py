from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import ResidentProfile, StaffProfile, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


class ResidentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    address = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    birth_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]
        widgets = {"username": forms.TextInput(attrs={"class": "form-control"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.RESIDENT
        if commit:
            user.save()
            ResidentProfile.objects.create(
                user=user,
                phone_number=self.cleaned_data.get("phone_number", ""),
                address=self.cleaned_data["address"],
                birth_date=self.cleaned_data.get("birth_date"),
            )
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class ResidentProfileForm(forms.ModelForm):
    class Meta:
        model = ResidentProfile
        fields = ["phone_number", "address", "birth_date"]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ["position", "phone_number"]
        widgets = {
            "position": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
        }


class StaffAccountForm(UserCreationForm):
    position = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STAFF
        user.is_staff = True
        if commit:
            user.save()
            StaffProfile.objects.create(
                user=user,
                position=self.cleaned_data.get("position", ""),
                phone_number=self.cleaned_data.get("phone_number", ""),
            )
        return user
