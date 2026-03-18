"""
社交模块Admin配置
"""
from django.contrib import admin
from .models import Moment, MomentImage, MomentComment, Message


class MomentImageInline(admin.TabularInline):
    """动态图片内联"""
    model = MomentImage
    extra = 0


@admin.register(Moment)
class MomentAdmin(admin.ModelAdmin):
    """动态管理"""
    list_display = ['user', 'content_preview', 'activity', 'likes_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content']
    inlines = [MomentImageInline]
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容'
    
    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = '点赞数'


@admin.register(MomentComment)
class MomentCommentAdmin(admin.ModelAdmin):
    """动态评论管理"""
    list_display = ['user', 'moment', 'content', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """消息管理"""
    list_display = ['recipient', 'sender', 'message_type', 'title', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'content']
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f'已标记{queryset.count()}条消息为已读')
    mark_as_read.short_description = '标记为已读'
