from django.contrib import admin
from .models import (
    Category, Activity, ActivityRegistration,
    ActivityComment, ActivityApplication
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'created_at']
    list_editable = ['sort_order']
    search_fields = ['name']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'creator', 'start_time',
                    'status', 'points', 'view_count', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'start_time'
    readonly_fields = ['view_count', 'created_at', 'updated_at']


@admin.register(ActivityRegistration)
class ActivityRegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity', 'status', 'registered_at']
    list_filter = ['status', 'registered_at']
    search_fields = ['user__username', 'activity__title']


@admin.register(ActivityComment)
class ActivityCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '评论内容'


@admin.register(ActivityApplication)
class ActivityApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'applicant', 'title', 'category', 'status',
        'created_at', 'reviewed_by', 'reviewed_at'
    ]
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['applicant__username', 'title', 'description', 'location']
    readonly_fields = ['created_at', 'reviewed_at']