"""
打卡模块Admin配置
"""
from django.contrib import admin
from .models import CheckIn, CheckInPhoto


class CheckInPhotoInline(admin.TabularInline):
    """打卡照片内联"""
    model = CheckInPhoto
    extra = 0
    readonly_fields = ['uploaded_at']


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    """打卡记录管理"""
    list_display = ['user', 'activity', 'status', 'points_earned', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'activity__title']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CheckInPhotoInline]
    actions = ['approve_checkins', 'reject_checkins']
    
    def approve_checkins(self, request, queryset):
        """批量通过审核"""
        for checkin in queryset.filter(status='pending'):
            checkin.approve(reviewer=request.user)
        self.message_user(request, f'已通过{queryset.count()}条打卡记录')
    approve_checkins.short_description = '批量通过审核'
    
    def reject_checkins(self, request, queryset):
        """批量拒绝审核"""
        for checkin in queryset.filter(status='pending'):
            checkin.reject(reviewer=request.user)
        self.message_user(request, f'已拒绝{queryset.count()}条打卡记录')
    reject_checkins.short_description = '批量拒绝审核'


@admin.register(CheckInPhoto)
class CheckInPhotoAdmin(admin.ModelAdmin):
    """打卡照片管理"""
    list_display = ['checkin', 'uploaded_at']
    list_filter = ['uploaded_at']
