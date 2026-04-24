from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Complaint, Category, ComplaintUpdate, Feedback
from .forms import ComplaintForm, ComplaintUpdateForm, FeedbackForm, UserRegistrationForm


# ===== PUBLIC VIEWS =====

def index(request):
    """Homepage - display system info and statistics"""
    total_complaints = Complaint.objects.count()
    resolved_complaints = Complaint.objects.filter(status='resolved').count()
    in_progress_complaints = Complaint.objects.filter(status='in_progress').count()
    pending_complaints = Complaint.objects.filter(status='pending').count()
    
    context = {
        'total_complaints': total_complaints,
        'resolved_complaints': resolved_complaints,
        'in_progress_complaints': in_progress_complaints,
        'pending_complaints': pending_complaints,
    }
    return render(request, 'complaints/index.html', context)


def file_complaint(request):
    """Page for citizens to file a new complaint"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            if request.user.is_authenticated:
                complaint.user = request.user
            else:
                from django.contrib.auth.models import User
                user, created = User.objects.get_or_create(
                    username='guest',
                    defaults={'email': 'guest@example.com'}
                )
                complaint.user = user
            complaint.save()
            messages.success(request, f'Complaint filed successfully! Reference: {complaint.reference_number}')
            return redirect('complaints:complaint_detail', pk=complaint.pk)
    else:
        form = ComplaintForm()
    
    categories = Category.objects.all()
    context = {'form': form, 'categories': categories}
    return render(request, 'complaints/file_complaint.html', context)


def complaint_list(request):
    """Display list of all public complaints"""
    complaints = Complaint.objects.all()
    
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)
    
    category = request.GET.get('category')
    if category:
        complaints = complaints.filter(category__id=category)
    
    search = request.GET.get('search')
    if search:
        complaints = complaints.filter(
            Q(reference_number__icontains=search) |
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    paginator = Paginator(complaints, 10)
    page = request.GET.get('page')
    complaints = paginator.get_page(page)
    
    categories = Category.objects.all()
    context = {
        'complaints': complaints,
        'categories': categories,
    }
    return render(request, 'complaints/complaint_list.html', context)


def complaint_detail(request, pk):
    """Display detailed view of a specific complaint"""
    complaint = get_object_or_404(Complaint, pk=pk)
    updates = complaint.updates.all()
    
    context = {
        'complaint': complaint,
        'updates': updates,
    }
    return render(request, 'complaints/complaint_detail.html', context)


def track_complaint(request):
    """Track complaint by reference number"""
    reference = request.GET.get('reference')
    complaint = None
    
    if reference:
        complaint = Complaint.objects.filter(reference_number=reference).first()
    
    context = {'complaint': complaint, 'reference': reference}
    return render(request, 'complaints/track_complaint.html', context)


# ===== AUTHENTICATED VIEWS =====

@login_required
def my_complaints(request):
    """View user's own complaints"""
    complaints = request.user.complaints.all()
    
    context = {'complaints': complaints}
    return render(request, 'complaints/my_complaints.html', context)


@login_required
def dashboard(request):
    """Dashboard for logged-in users"""
    my_complaints = request.user.complaints.all()
    my_complaint_count = my_complaints.count()
    my_resolved = my_complaints.filter(status='resolved').count()
    my_pending = my_complaints.filter(status='pending').count()
    
    context = {
        'my_complaint_count': my_complaint_count,
        'my_resolved': my_resolved,
        'my_pending': my_pending,
        'my_complaints': my_complaints[:5],
    }
    return render(request, 'complaints/dashboard.html', context)


# ===== STAFF VIEWS =====

@login_required
def staff_dashboard(request):
    """Dashboard for staff members"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('complaints:index')
    
    all_complaints = Complaint.objects.all()
    pending = all_complaints.filter(status='pending').count()
    in_progress = all_complaints.filter(status='in_progress').count()
    resolved = all_complaints.filter(status='resolved').count()
    
    assigned = all_complaints.filter(assigned_to=request.user)
    
    context = {
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'assigned': assigned,
        'total': all_complaints.count(),
    }
    return render(request, 'complaints/staff_dashboard.html', context)


# ===== API ENDPOINTS (JSON) =====

def api_categories(request):
    """API endpoint to get all categories (for AJAX)"""
    categories = Category.objects.values('id', 'name')
    return JsonResponse(list(categories), safe=False)


def api_complaint_stats(request):
    """API endpoint to get complaint statistics"""
    stats = {
        'total': Complaint.objects.count(),
        'pending': Complaint.objects.filter(status='pending').count(),
        'in_progress': Complaint.objects.filter(status='in_progress').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
    }
    return JsonResponse(stats)
