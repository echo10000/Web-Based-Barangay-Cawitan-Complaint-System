from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import (
    LoginForm,
    ResidentProfileForm,
    ResidentRegistrationForm,
    StaffAccountForm,
    StaffProfileForm,
    UserProfileForm,
)
from .models import ResidentProfile, StaffProfile, User


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_barangay_admin:
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have permission to access that page.")
        return redirect("dashboard:home")

    return wrapper


class RoleAwareLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


login_view = RoleAwareLoginView.as_view()


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


@login_required
def profile_view(request):
    user_form = UserProfileForm(request.POST or None, instance=request.user)
    profile_form = None

    if request.user.is_resident:
        profile, _ = ResidentProfile.objects.get_or_create(user=request.user, defaults={"address": ""})
        profile_form = ResidentProfileForm(request.POST or None, instance=profile)
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
def resident_management_view(request):
    residents = User.objects.filter(role=User.Role.RESIDENT).select_related("resident_profile").order_by("last_name")
    return render(request, "accounts/resident_management.html", {"residents": residents})


@login_required
@admin_required
def staff_management_view(request):
    staff = User.objects.filter(role=User.Role.STAFF).select_related("staff_profile").order_by("last_name")
    return render(request, "accounts/staff_management.html", {"staff": staff})
