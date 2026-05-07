from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from complaints.models import ComplaintCategory
from .models import ResidentProfile, StaffProfile, User


PUROK_CHOICES = [
    ("", "Select purok"),
    ("Purok 1-A", "Purok 1-A"),
    ("Purok 1-B", "Purok 1-B"),
    ("Purok 2", "Purok 2"),
    ("Purok 3", "Purok 3"),
    ("Purok 4", "Purok 4"),
    ("Purok 5", "Purok 5"),
    ("Purok 6", "Purok 6"),
    ("Purok 7", "Purok 7"),
]


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"})
    )

    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        password = self.cleaned_data.get("password")

        if identifier and password:
            self.user_cache = authenticate(self.request, username=identifier, password=password)

            if self.user_cache is None and "@" in identifier:
                for user in User.objects.filter(email__iexact=identifier):
                    self.user_cache = authenticate(self.request, username=user.get_username(), password=password)
                    if self.user_cache is not None:
                        break

            if self.user_cache is None:
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ResidentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    address = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    purok = forms.ChoiceField(choices=PUROK_CHOICES, required=False, widget=forms.Select(attrs={"class": "form-select"}))
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
                purok=self.cleaned_data.get("purok", ""),
                household_number="",
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


class AdminAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AdminSelfAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
        labels = {
            "first_name": "Admin first name",
            "last_name": "Admin last name",
            "email": "Admin email address",
        }


class ResidentProfileForm(forms.ModelForm):
    class Meta:
        model = ResidentProfile
        fields = [
            "phone_number",
            "address",
            "purok",
            "household_number",
            "birth_date",
            "valid_id_type",
            "valid_id_front_image",
            "valid_id_back_image",
        ]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "purok": forms.TextInput(attrs={"class": "form-control"}),
            "household_number": forms.TextInput(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "valid_id_type": forms.Select(attrs={"class": "form-select"}),
            "valid_id_front_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "valid_id_back_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "valid_id_type": "Type of valid ID",
            "valid_id_front_image": "Valid ID front image",
            "valid_id_back_image": "Valid ID back image",
        }
        help_texts = {
            "valid_id_type": "Choose the ID shown in the images you will submit.",
            "valid_id_front_image": "Upload the front side of your valid ID.",
            "valid_id_back_image": "Upload the back side of your valid ID.",
        }


class ResidentAdminProfileForm(forms.ModelForm):
    class Meta:
        model = ResidentProfile
        fields = ["phone_number", "address", "purok", "household_number", "birth_date"]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "purok": forms.TextInput(attrs={"class": "form-control"}),
            "household_number": forms.TextInput(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class ResidentVerificationForm(forms.ModelForm):
    class Meta:
        model = ResidentProfile
        fields = ["verification_status", "verification_notes"]
        widgets = {
            "verification_status": forms.Select(attrs={"class": "form-select"}),
            "verification_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ["position", "availability", "specialization_categories", "phone_number"]
        widgets = {
            "position": forms.TextInput(attrs={"class": "form-control"}),
            "availability": forms.Select(attrs={"class": "form-select"}),
            "specialization_categories": forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["specialization_categories"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["specialization_categories"].required = False


class StaffAccountForm(UserCreationForm):
    position = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    availability = forms.ChoiceField(
        choices=StaffProfile.Availability.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    specialization_categories = forms.ModelMultipleChoiceField(
        queryset=ComplaintCategory.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
    )
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
        self.fields["specialization_categories"].queryset = ComplaintCategory.objects.filter(is_active=True)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STAFF
        user.is_staff = True
        if commit:
            user.save()
            staff_profile = StaffProfile.objects.create(
                user=user,
                position=self.cleaned_data.get("position", ""),
                availability=self.cleaned_data.get("availability") or StaffProfile.Availability.AVAILABLE,
                phone_number=self.cleaned_data.get("phone_number", ""),
            )
            staff_profile.specialization_categories.set(self.cleaned_data.get("specialization_categories"))
        return user
