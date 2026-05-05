from django import forms
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import User
from .models import Complaint, ComplaintCategory, ComplaintResponse, UploadedEvidence


ACTIVE_ASSIGNMENT_STATUSES = [
    Complaint.Status.PENDING,
    Complaint.Status.UNDER_REVIEW,
    Complaint.Status.IN_PROGRESS,
]


class StaffAssignmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        workload = getattr(obj, "active_workload", 0)
        overdue = getattr(obj, "overdue_workload", 0)
        try:
            profile = obj.staff_profile
            availability = profile.get_availability_display()
            team = profile.department or profile.position or "No team"
        except Exception:
            availability = "No availability"
            team = "No team"
        return f"{obj.get_full_name() or obj.username} - {availability}, {workload} active, {overdue} overdue, {team}"


class ComplaintForm(forms.ModelForm):
    evidence = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        help_text="Optional: upload an image or supporting document.",
    )

    class Meta:
        model = Complaint
        fields = [
            "category",
            "priority",
            "title",
            "description",
            "contact_number",
            "incident_location",
            "incident_date",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "contact_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 09XX XXX XXXX"}),
            "incident_location": forms.TextInput(attrs={"class": "form-control"}),
            "incident_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["category"].required = False
        self.fields["priority"].help_text = (
            "Choose Urgent for immediate risks such as safety, peace and order, flooding, or health issues."
        )


class ComplaintUpdateForm(forms.ModelForm):
    assigned_to = StaffAssignmentChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Add remarks or response"}),
    )

    class Meta:
        model = Complaint
        fields = ["category", "priority", "status", "assigned_to"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("complaint", None)
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["category"].required = False
        self.fields["priority"].help_text = "Use Urgent for cases that need immediate barangay attention."
        staff_queryset = (
            User.objects.filter(role=User.Role.STAFF, is_active=True)
            .select_related("staff_profile")
            .annotate(
                active_workload=Count(
                    "assigned_complaints",
                    filter=Q(assigned_complaints__status__in=ACTIVE_ASSIGNMENT_STATUSES),
                ),
                overdue_workload=Count(
                    "assigned_complaints",
                    filter=Q(
                        assigned_complaints__status__in=ACTIVE_ASSIGNMENT_STATUSES,
                        assigned_complaints__deadline_at__lt=timezone.now(),
                    ),
                ),
            )
            .order_by("active_workload", "last_name", "first_name", "username")
        )
        self.fields["assigned_to"].queryset = staff_queryset


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
