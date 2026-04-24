from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.db import models
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User

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
            if complaint.user and complaint.user.email and complaint.user.email != 'guest@example.com':
                subject = 'Barangay Cawitan Complaint Received'
                message = (
                    f"Hello {complaint.user.get_full_name() or complaint.user.username},\n\n"
                    f"Your complaint has been received successfully.\n"
                    f"Reference number: {complaint.reference_number}\n"
                    f"Title: {complaint.title}\n\n"
                    "A staff member will review the complaint and provide an update soon.\n\n"
                    "Thank you,\nBarangay Cawitan"
                )
                send_mail(subject, message, 'noreply@barangaycawitan.ph', [complaint.user.email])
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


@login_required
def staff_complaint_list(request):
    """List of complaints for staff management"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('complaints:index')
    
    complaints = Complaint.objects.all()
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)
    
    # Filter by priority
    priority = request.GET.get('priority')
    if priority:
        complaints = complaints.filter(priority=priority)
    
    # Filter by assigned_to
    assigned = request.GET.get('assigned')
    if assigned:
        if assigned == 'me':
            complaints = complaints.filter(assigned_to=request.user)
        elif assigned != 'unassigned':
            complaints = complaints.filter(assigned_to__id=assigned)
    
    # Search
    search = request.GET.get('search')
    if search:
        complaints = complaints.filter(
            Q(reference_number__icontains=search) |
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    if sort in ['created_at', '-created_at', 'priority', '-priority', 'status']:
        complaints = complaints.order_by(sort)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(complaints, 15)
    page = request.GET.get('page')
    complaints = paginator.get_page(page)
    
    # Get all staff for assignment dropdown
    staff_members = User.objects.filter(is_staff=True)
    
    context = {
        'complaints': complaints,
        'staff_members': staff_members,
    }
    return render(request, 'complaints/staff_complaint_list.html', context)


@login_required
def staff_edit_complaint(request, pk):
    """Edit complaint status and assignment"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('complaints:index')
    
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        # Update status
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Complaint.STATUS_CHOICES):
            complaint.status = new_status
            
            # Set resolved_at if status is resolved
            if new_status == 'resolved':
                complaint.resolved_at = timezone.now()
        
        # Update priority
        new_priority = request.POST.get('priority')
        if new_priority and new_priority in dict(Complaint.PRIORITY_CHOICES):
            complaint.priority = new_priority
        
        # Assign to staff member
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            try:
                assigned_user = User.objects.get(id=assigned_to_id, is_staff=True)
                complaint.assigned_to = assigned_user
            except User.DoesNotExist:
                messages.error(request, 'Invalid staff member selected.')
        
        # Add internal notes
        internal_notes = request.POST.get('internal_notes')
        if internal_notes:
            complaint.internal_notes = (complaint.internal_notes or '') + f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {request.user.get_full_name() or request.user.username}:\n{internal_notes}"
        
        complaint.save()
        if complaint.user and complaint.user.email and complaint.user.email != 'guest@example.com' and new_status:
            subject = f'Complaint Status Updated: {complaint.reference_number}'
            message = (
                f"Hello {complaint.user.get_full_name() or complaint.user.username},\n\n"
                f"Your complaint status has been updated to: {complaint.get_status_display()}.\n"
                f"Reference number: {complaint.reference_number}\n\n"
                "Please log in to the portal for more details.\n\n"
                "Thank you,\nBarangay Cawitan"
            )
            send_mail(subject, message, 'noreply@barangaycawitan.ph', [complaint.user.email])
        messages.success(request, 'Complaint updated successfully!')
        return redirect('complaints:staff_edit_complaint', pk=complaint.pk)
    
    staff_members = User.objects.filter(is_staff=True)
    context = {
        'complaint': complaint,
        'staff_members': staff_members,
    }
    return render(request, 'complaints/staff_edit_complaint.html', context)


@login_required
def staff_add_update(request, pk):
    """Add public update to complaint"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('complaints:index')
    
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        form = ComplaintUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.updated_by = request.user
            update.save()
            
            messages.success(request, 'Update posted to complaint!')
            return redirect('complaints:staff_edit_complaint', pk=complaint.pk)
    else:
        form = ComplaintUpdateForm()
    
    context = {
        'form': form,
        'complaint': complaint,
    }
    return render(request, 'complaints/staff_add_update.html', context)


@login_required
def staff_reports(request):
    """Reports and statistics for staff"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('complaints:index')
    
    # Overall stats
    total = Complaint.objects.count()
    by_status = {}
    for status, label in Complaint.STATUS_CHOICES:
        by_status[label] = Complaint.objects.filter(status=status).count()
    
    by_priority = {}
    for priority, label in Complaint.PRIORITY_CHOICES:
        by_priority[label] = Complaint.objects.filter(priority=priority).count()
    
    # By category
    categories = Category.objects.all()
    by_category = []
    for cat in categories:
        by_category.append({
            'name': cat.name,
            'count': cat.complaints.count(),
        })
    
    # Average resolution time (for resolved complaints)
    from django.db.models import F, ExpressionWrapper, DurationField, Avg
    avg_time = Complaint.objects.filter(
        status='resolved',
        resolved_at__isnull=False
    ).aggregate(
        avg_days=Avg(ExpressionWrapper(
            F('resolved_at') - F('created_at'),
            output_field=DurationField()
        ))
    )['avg_days']
    
    avg_days = avg_time.days if avg_time else 0
    
    # Staff performance
    staff_complaints = User.objects.filter(is_staff=True).annotate(
        assigned_count=models.Count('assigned_complaints'),
        resolved_count=models.Count('assigned_complaints', filter=models.Q(assigned_complaints__status='resolved'))
    )
    
    context = {
        'total': total,
        'by_status': by_status,
        'by_priority': by_priority,
        'by_category': by_category,
        'avg_resolution_days': avg_days,
        'staff_complaints': staff_complaints,
    }
    return render(request, 'complaints/staff_reports.html', context)


@login_required
def staff_my_complaints(request):
    """Complaints assigned to current staff member"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('complaints:index')
    
    complaints = Complaint.objects.filter(assigned_to=request.user)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)
    
    # Filter by priority
    priority = request.GET.get('priority')
    if priority:
        complaints = complaints.filter(priority=priority)
    
    pending = complaints.filter(status='pending').count()
    in_progress = complaints.filter(status='in_progress').count()
    resolved = complaints.filter(status='resolved').count()
    
    context = {
        'complaints': complaints,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
    }
    return render(request, 'complaints/staff_my_complaints.html', context)


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
