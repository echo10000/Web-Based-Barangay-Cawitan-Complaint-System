import random

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string

from .forms import (
    AdminAccountForm,
    LoginForm,
    ResidentProfileForm,
    ResidentRegistrationForm,
    ResidentVerificationForm,
    StaffAccountForm,
    StaffProfileForm,
    UserProfileForm,
)
from .models import PasswordResetOTP, ResidentProfile, StaffProfile, User


PASSWORD_RESET_USER_SESSION_KEY = "password_reset_user_id"
PASSWORD_RESET_VERIFIED_SESSION_KEY = "password_reset_verified_user_id"
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


def _generate_otp():
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def _create_and_send_password_reset_otp(user):
    latest_otp = PasswordResetOTP.objects.filter(user=user, is_used=False).first()
    if latest_otp and latest_otp.last_sent_at:
        seconds_since_last_send = (timezone.now() - latest_otp.last_sent_at).total_seconds()
        if seconds_since_last_send < OTP_RESEND_COOLDOWN_SECONDS:
            wait_seconds = int(OTP_RESEND_COOLDOWN_SECONDS - seconds_since_last_send)
            raise ValueError(f"Please wait {wait_seconds} seconds before requesting another OTP.")

    PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
    otp = _generate_otp()
    PasswordResetOTP.objects.create(user=user, otp="", otp_hash=make_password(otp), last_sent_at=timezone.now())
    send_mail(
        "Barangay Cawitan - Password Reset OTP",
        f"Your OTP is: {otp}. It expires in 10 minutes. Do not share this.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_barangay_admin:
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have permission to access that page.")
        return redirect("dashboard:home")

    return wrapper


def _admin_managed_account_or_404(pk):
    account = get_object_or_404(User, pk=pk)
    if account.role not in (User.Role.RESIDENT, User.Role.STAFF):
        raise Http404("Account is not managed from this page.")
    return account


def _account_list_url(account):
    if account.role == User.Role.STAFF:
        return "accounts:staff"
    return "accounts:residents"


class RoleAwareLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    extra_context = {"messages_in_card": True}


login_view = RoleAwareLoginView.as_view()


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("accounts:login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = ResidentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Registration successful. Welcome to the complaint portal.")
        return redirect("dashboard:resident")
    return render(request, "accounts/register.html", {"form": form})


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            messages.error(request, "No account found with that email.")
            return redirect("accounts:forgot_password")

        try:
            _create_and_send_password_reset_otp(user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("accounts:forgot_password")
        except Exception:
            messages.error(request, "Unable to send OTP right now. Please try again later.")
            return redirect("accounts:forgot_password")

        request.session[PASSWORD_RESET_USER_SESSION_KEY] = user.id
        request.session.pop(PASSWORD_RESET_VERIFIED_SESSION_KEY, None)
        messages.success(request, "We sent a 6-digit OTP to your email.")
        return redirect("accounts:verify_otp")

    return render(request, "accounts/forgot_password.html", {"messages_in_card": True})


def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    user_id = request.session.get(PASSWORD_RESET_USER_SESSION_KEY)
    if not user_id:
        messages.error(request, "Please enter your registered email first.")
        return redirect("accounts:forgot_password")

    user = get_object_or_404(User, id=user_id)

    if request.method == "GET" and request.GET.get("resend") == "1":
        try:
            _create_and_send_password_reset_otp(user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("accounts:verify_otp")
        except Exception:
            messages.error(request, "Unable to resend OTP right now. Please try again later.")
            return redirect("accounts:verify_otp")

        messages.success(request, "A new OTP has been sent to your email.")
        return redirect("accounts:verify_otp")

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        otp_record = PasswordResetOTP.objects.filter(user=user, is_used=False).first()

        if not otp_record:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("accounts:verify_otp")

        if otp_record.is_expired():
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("accounts:verify_otp")

        if otp_record.failed_attempts >= OTP_MAX_ATTEMPTS:
            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])
            messages.error(request, "Too many invalid attempts. Please request a new OTP.")
            return redirect("accounts:forgot_password")

        otp_matches = check_password(otp, otp_record.otp_hash) if otp_record.otp_hash else otp_record.otp == otp
        if not otp_matches:
            otp_record.failed_attempts += 1
            otp_record.save(update_fields=["failed_attempts"])
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("accounts:verify_otp")

        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])
        request.session[PASSWORD_RESET_VERIFIED_SESSION_KEY] = user.id
        messages.success(request, "OTP verified. Please set your new password.")
        return redirect("accounts:set_new_password")

    return render(request, "accounts/verify_otp.html", {"messages_in_card": True})


def set_new_password_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    user_id = request.session.get(PASSWORD_RESET_VERIFIED_SESSION_KEY)
    if not user_id:
        messages.error(request, "Please verify your OTP first.")
        return redirect("accounts:verify_otp")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("accounts:set_new_password")

        user.set_password(password)
        user.save(update_fields=["password"])
        request.session.pop(PASSWORD_RESET_USER_SESSION_KEY, None)
        request.session.pop(PASSWORD_RESET_VERIFIED_SESSION_KEY, None)
        messages.success(request, "Password reset successful. You can now log in.")
        return redirect("accounts:login")

    return render(request, "accounts/set_new_password.html", {"messages_in_card": True})


@login_required
def profile_view(request):
    user_form = UserProfileForm(request.POST or None, instance=request.user)
    profile_form = None

    if request.user.is_resident:
        profile, _ = ResidentProfile.objects.get_or_create(user=request.user, defaults={"address": ""})
        profile_form = ResidentProfileForm(request.POST or None, request.FILES or None, instance=profile)
    elif request.user.is_staff_member:
        profile, _ = StaffProfile.objects.get_or_create(user=request.user)
        profile_form = StaffProfileForm(request.POST or None, instance=profile)

    if request.method == "POST" and user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
        user_form.save()
        if profile_form:
            profile_form.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"user_form": user_form, "profile_form": profile_form})


@login_required
@admin_required
def create_staff_view(request):
    form = StaffAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Staff account created successfully.")
        return redirect("accounts:staff")
    return render(request, "accounts/create_staff.html", {"form": form})


@login_required
@admin_required
def edit_account_view(request, pk):
    account = _admin_managed_account_or_404(pk)
    user_form = AdminAccountForm(request.POST or None, instance=account)
    if account.role == User.Role.RESIDENT:
        profile, _ = ResidentProfile.objects.get_or_create(user=account, defaults={"address": ""})
        profile_form = ResidentProfileForm(request.POST or None, request.FILES or None, instance=profile)
        verification_data = request.POST if "verify-verification_status" in request.POST else None
        verification_form = ResidentVerificationForm(verification_data, instance=profile, prefix="verify")
        account_type = "Resident"
    else:
        profile, _ = StaffProfile.objects.get_or_create(user=account)
        profile_form = StaffProfileForm(request.POST or None, instance=profile)
        verification_form = None
        account_type = "Staff"

    verification_valid = verification_form is None or not verification_form.is_bound or verification_form.is_valid()
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid() and verification_valid:
        user_form.save()
        profile_form.save()
        if verification_form and verification_form.is_bound:
            resident_profile = verification_form.save(commit=False)
            if "verification_status" in verification_form.changed_data:
                is_verified = resident_profile.verification_status == ResidentProfile.VerificationStatus.VERIFIED
                resident_profile.verified_at = timezone.now() if is_verified else None
                resident_profile.verified_by = request.user if is_verified else None
            resident_profile.save()
        messages.success(request, f"{account_type} account updated successfully.")
        return redirect(_account_list_url(account))

    return render(
        request,
        "accounts/edit_account.html",
        {
            "account": account,
            "account_type": account_type,
            "user_form": user_form,
            "profile_form": profile_form,
            "verification_form": verification_form,
        },
    )


@login_required
@admin_required
def toggle_account_status_view(request, pk):
    if request.method != "POST":
        return redirect("dashboard:home")
    account = _admin_managed_account_or_404(pk)
    account.is_active = not account.is_active
    account.save(update_fields=["is_active"])
    state = "activated" if account.is_active else "deactivated"
    messages.success(request, f"{account.get_full_name() or account.username} has been {state}.")
    return redirect(_account_list_url(account))


@login_required
@admin_required
def reset_account_password_view(request, pk):
    if request.method != "POST":
        return redirect("dashboard:home")
    account = _admin_managed_account_or_404(pk)
    if not account.email:
        messages.error(request, "This account has no email address for password reset.")
        return redirect(_account_list_url(account))
    temporary_password = get_random_string(12)
    account.set_password(temporary_password)
    account.save(update_fields=["password"])
    try:
        send_mail(
            "Barangay Cawitan - Temporary Password",
            (
                f"Hello {account.get_full_name() or account.username},\n\n"
                f"An administrator reset your Barangay Cawitan account password.\n\n"
                f"Username: {account.username}\n"
                f"Temporary password: {temporary_password}\n\n"
                "Please log in and change your password as soon as possible."
            ),
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
        )
    except Exception:
        messages.error(request, "Password was reset, but the temporary password email could not be sent.")
    else:
        messages.success(request, f"Temporary password sent to {account.email}.")
    return redirect(_account_list_url(account))


@login_required
@admin_required
def verify_resident_view(request, pk):
    if request.method != "POST":
        return redirect("accounts:residents")
    account = get_object_or_404(User, pk=pk, role=User.Role.RESIDENT)
    profile, _ = ResidentProfile.objects.get_or_create(user=account, defaults={"address": ""})
    profile.verification_status = ResidentProfile.VerificationStatus.VERIFIED
    profile.verified_at = timezone.now()
    profile.verified_by = request.user
    profile.save(update_fields=["verification_status", "verified_at", "verified_by"])
    messages.success(request, f"{account.get_full_name() or account.username} has been verified.")
    return redirect("accounts:residents")


@login_required
@admin_required
def resident_management_view(request):
    residents = User.objects.filter(role=User.Role.RESIDENT).select_related("resident_profile").order_by("last_name")
    search = request.GET.get("q", "").strip()
    total_residents = residents.count()
    complete_profiles = residents.exclude(
        Q(email="")
        | Q(first_name="")
        | Q(last_name="")
        | Q(resident_profile__phone_number="")
        | Q(resident_profile__address="")
    ).count()
    verified_residents = residents.filter(
        resident_profile__verification_status=ResidentProfile.VerificationStatus.VERIFIED
    ).count()
    if search:
        residents = residents.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(resident_profile__phone_number__icontains=search)
            | Q(resident_profile__address__icontains=search)
        )
    return render(
        request,
        "accounts/resident_management.html",
        {
            "residents": residents,
            "search_query": search,
            "total_residents": total_residents,
            "filtered_count": residents.count(),
            "complete_profiles": complete_profiles,
            "incomplete_profiles": total_residents - complete_profiles,
            "verified_residents": verified_residents,
        },
    )


@login_required
@admin_required
def staff_management_view(request):
    staff = User.objects.filter(role=User.Role.STAFF).select_related("staff_profile").order_by("last_name")
    search = request.GET.get("q", "").strip()
    total_staff = staff.count()
    available_staff = staff.filter(staff_profile__availability=StaffProfile.Availability.AVAILABLE).count()
    busy_staff = staff.filter(staff_profile__availability=StaffProfile.Availability.BUSY).count()
    if search:
        staff = staff.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(staff_profile__position__icontains=search)
            | Q(staff_profile__department__icontains=search)
            | Q(staff_profile__phone_number__icontains=search)
        )
    return render(
        request,
        "accounts/staff_management.html",
        {
            "staff": staff,
            "search_query": search,
            "total_staff": total_staff,
            "filtered_count": staff.count(),
            "available_staff": available_staff,
            "busy_staff": busy_staff,
        },
    )
