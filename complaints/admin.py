from django.contrib import admin

from .models import Category, Complaint, ComplaintUpdate, Feedback


class ComplaintUpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 0
    fields = ('status', 'note', 'updated_by', 'created_at')
    readonly_fields = ('created_at',)


class FeedbackInline(admin.TabularInline):
    model = Feedback
    extra = 0
    fields = ('user_email', 'rating', 'comments', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'user', 'created_at', 'updated_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    inlines = [ComplaintUpdateInline, FeedbackInline]


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'status', 'updated_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('complaint__title', 'note', 'updated_by__username')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'user_email', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('complaint__title', 'user_email', 'comments')
