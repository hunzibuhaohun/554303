"""
用户模块Admin配置
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, FollowRelation, UserAchievement


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理后台"""
    list_display = ['username', 'student_id', 'real_name', 'department', 
                    'role', 'points', 'total_checkins', 'is_verified', 'created_at']
    list_filter = ['role', 'is_verified', 'gender', 'department', 'created_at']
    search_fields = ['username', 'student_id', 'real_name', 'phone', 'email']
    readonly_fields = ['points', 'total_checkins', 'created_at', 'updated_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': ('student_id', 'real_name', 'gender', 'phone',
                      'department', 'major', 'grade', 'role', 'is_verified',
                      'avatar', 'bio', 'points', 'total_checkins')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FollowRelation)
class FollowRelationAdmin(admin.ModelAdmin):
    """关注关系管理"""
    list_display = ['follower', 'following', 'created_at']
    list_filter = ['created_at']
    search_fields = ['follower__username', 'following__username']


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    """用户成就管理"""
    list_display = ['user', 'achievement_type', 'name', 'level', 'earned_at']
    list_filter = ['achievement_type', 'level', 'earned_at']
    search_fields = ['user__username', 'name']
