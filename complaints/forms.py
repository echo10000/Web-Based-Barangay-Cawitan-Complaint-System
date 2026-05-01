from django import forms

from accounts.models import User
from .models import Complaint, ComplaintCategory, ComplaintResponse, UploadedEvidence


class ComplaintForm(forms.ModelForm):
    evidence = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        help_text="Optional: upload an image or supporting document.",
    )

    class Meta:
        model = Complaint
        fields = ["category", "title", "description", "incident_location", "incident_date"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "incident_location": forms.TextInput(attrs={"class": "form-control"}),
            "incident_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["category"].required = False


class ComplaintUpdateForm(forms.ModelForm):
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.STAFF),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Add remarks or response"}),
    )

    class Meta:
        model = Complaint
        fields = ["status", "assigned_to"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class ComplaintResponseForm(forms.ModelForm):
    class Meta:
        model = ComplaintResponse
        fields = ["remarks"]
        widgets = {"remarks": forms.Textarea(attrs={"class": "form-control", "rows": 4})}


class EvidenceForm(forms.ModelForm):
    class Meta:
        model = UploadedEvidence
        fields = ["file"]
        widgets = {"file": forms.ClearableFileInput(attrs={"class": "form-control"})}
