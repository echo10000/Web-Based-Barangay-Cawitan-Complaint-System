from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login

from complaints.forms import UserRegistrationForm


def register(request):
    """User registration page"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome!')
            return redirect('complaints:dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})
