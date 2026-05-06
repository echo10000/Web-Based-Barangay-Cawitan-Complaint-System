from django import forms
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import User
from .models import (
    Complaint,
    ComplaintCategory,
    ComplaintResponse,
    Escalation,
    HearingMediation,
    Respondent,
    RespondentEvidence,
    UploadedEvidence,
)


ACTIVE_ASSIGNMENT_STATUSES = [
    Complaint.Status.PENDING,
    Complaint.Status.UNDER_REVIEW,
    Complaint.Status.RESPONDENT_NOT_CONTACTED,
    Complaint.Status.RESPONDENT_CONTACTED,
    Complaint.Status.WAITING_RESPONDENT_RESPONSE,
    Complaint.Status.RESPONDENT_RESPONSE_RECORDED,
    Complaint.Status.NO_RESPONSE,
    Complaint.Status.FAILED_TO_ATTEND,
    Complaint.Status.SECOND_NOTICE_SENT,
    Complaint.Status.HEARING_SCHEDULED,
    Complaint.Status.IN_MEDIATION,
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
    privacy_consent = forms.BooleanField(
        label=(
            "I consent to the collection, use, and processing of my personal information and complaint details "
            "by the Barangay Cawitan office for complaint handling, mediation, documentation, and official reporting "
            "in accordance with the Data Privacy Act of 2012."
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={"required": "You must agree to the Data Privacy consent before submitting a complaint."},
    )
    accuracy_certification = forms.BooleanField(
        label=(
            "I certify that the information I provided is true and correct to the best of my knowledge, "
            "and I understand that false or misleading information may delay or affect the complaint process."
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={"required": "You must certify that the information provided is true and correct."},
    )
    contact_permission = forms.BooleanField(
        label=(
            "I allow barangay staff to contact me using the contact details I provided for updates, verification, "
            "notices, hearing schedules, and mediation-related communication."
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={"required": "You must allow contact for complaint updates and notices."},
    )
    respondent_full_name = forms.CharField(
        label="Respondent full name",
        max_length=150,
        initial="Unknown",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter full name or Unknown"}),
    )
    respondent_contact_number = forms.CharField(
        label="Respondent contact number",
        required=False,
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional if unknown"}),
    )
    respondent_address = forms.CharField(
        label="Respondent address or Purok",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional if unknown"}),
    )
    respondent_relationship_to_complainant = forms.CharField(
        label="Relationship to complainant",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
    )
    respondent_is_known_to_complainant = forms.TypedChoiceField(
        label="Is the respondent known to you?",
        choices=((True, "Yes"), (False, "No")),
        coerce=lambda value: value in (True, "True", "true", "1", "Yes", "yes"),
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial=True,
    )
    respondent_identifying_details = forms.CharField(
        label="Other identifying details",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional"}),
    )
    respondent_remarks = forms.CharField(
        label="Remarks about the respondent",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional"}),
    )
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
            "privacy_consent",
            "accuracy_certification",
            "contact_permission",
            "respondent_full_name",
            "respondent_contact_number",
            "respondent_address",
            "respondent_relationship_to_complainant",
            "respondent_is_known_to_complainant",
            "respondent_identifying_details",
            "respondent_remarks",
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
        self.fields["category"].required = True
        self.fields["title"].required = True
        self.fields["description"].required = True
        self.fields["incident_location"].required = True
        self.fields["incident_date"].required = True
        self.fields["priority"].help_text = (
            "Choose Urgent for immediate risks such as safety, peace and order, flooding, or health issues."
        )

    def clean_respondent_full_name(self):
        return self.cleaned_data["respondent_full_name"].strip() or "Unknown"


class ComplaintUpdateForm(forms.ModelForm):
    assigned_to = StaffAssignmentChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    public_remarks_input = forms.CharField(
        label="Public remarks",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Visible to the complainant, such as hearing instructions or status updates.",
            }
        ),
    )
    internal_remarks_input = forms.CharField(
        label="Internal remarks",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 3, "placeholder": "Staff-only notes. Not shown to complainants."}
        ),
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


class RespondentForm(forms.ModelForm):
    class Meta:
        model = Respondent
        fields = [
            "full_name",
            "contact_number",
            "address",
            "email",
            "relationship_to_complainant",
            "is_known_to_complainant",
            "identifying_details",
            "remarks",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "relationship_to_complainant": forms.TextInput(attrs={"class": "form-control"}),
            "is_known_to_complainant": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "identifying_details": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_full_name(self):
        return self.cleaned_data["full_name"].strip() or "Unknown"


class RespondentContactForm(forms.ModelForm):
    class Meta:
        model = Respondent
        fields = [
            "contacted",
            "contact_method",
            "contact_date",
            "contact_remarks",
            "response_status",
            "response_statement",
        ]
        widgets = {
            "contacted": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "contact_method": forms.Select(attrs={"class": "form-select"}),
            "contact_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "contact_remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "response_status": forms.Select(attrs={"class": "form-select"}),
            "response_statement": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class RespondentResponseForm(forms.ModelForm):
    evidence = forms.FileField(
        label="Respondent evidence",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        help_text="Optional file or image submitted by the respondent.",
    )
    evidence_remarks = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Short note about the evidence"}),
    )

    class Meta:
        model = ComplaintResponse
        fields = ["remarks"]
        widgets = {"remarks": forms.Textarea(attrs={"class": "form-control", "rows": 4})}


class HearingMediationForm(forms.ModelForm):
    class Meta:
        model = HearingMediation
        fields = ["date", "time", "location", "purpose", "remarks"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "purpose": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hearing, mediation, or case conference"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class HearingAttendanceForm(forms.ModelForm):
    class Meta:
        model = HearingMediation
        fields = [
            "complainant_attended",
            "respondent_attended",
            "attendance_remarks",
            "mediation_result",
            "agreement_remarks",
        ]
        widgets = {
            "complainant_attended": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "respondent_attended": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "attendance_remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "mediation_result": forms.Select(attrs={"class": "form-select"}),
            "agreement_remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class SecondNoticeForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["second_notice_sent", "second_notice_date", "second_notice_method", "second_notice_remarks"]
        widgets = {
            "second_notice_sent": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "second_notice_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "second_notice_method": forms.TextInput(attrs={"class": "form-control", "placeholder": "SMS, letter, personal notice, etc."}),
            "second_notice_remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class EscalationForm(forms.ModelForm):
    class Meta:
        model = Escalation
        fields = ["escalation_date", "escalated_to", "reason", "remarks"]
        widgets = {
            "escalation_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "escalated_to": forms.TextInput(attrs={"class": "form-control", "placeholder": "Office, council, or authority"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class EvidenceForm(forms.ModelForm):
    class Meta:
        model = UploadedEvidence
        fields = ["file"]
        widgets = {"file": forms.ClearableFileInput(attrs={"class": "form-control"})}


class RespondentEvidenceForm(forms.ModelForm):
    class Meta:
        model = RespondentEvidence
        fields = ["file", "remarks"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "remarks": forms.TextInput(attrs={"class": "form-control"}),
        }
