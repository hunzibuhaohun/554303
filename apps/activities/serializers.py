
"""活动序列化器 - 校园打卡平台"""
from rest_framework import serializers

from .models import Activity, ActivityComment, ActivityRegistration, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color', 'description']


class ActivityCommentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActivityComment
        fields = ['id', 'user', 'user_username', 'content', 'created_at']


class ActivitySerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    active_registration_count = serializers.SerializerMethodField()
    comments = ActivityCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'cover_image', 'category', 'category_name',
            'creator', 'creator_username', 'start_time', 'end_time',
            'registration_deadline', 'location', 'location_lat', 'location_lng',
            'max_participants', 'min_participants', 'points', 'requirements',
            'allow_checkin_before_start', 'checkin_radius', 'checkin_review_mode',
            'status', 'view_count', 'created_at', 'updated_at',
            'registration_percentage', 'active_registration_count', 'comments',
        ]
        read_only_fields = [
            'creator', 'status', 'view_count', 'created_at', 'updated_at',
            'registration_percentage', 'active_registration_count',
        ]

    def get_active_registration_count(self, obj):
        return obj.get_active_registration_count()


class ActivityRegistrationSerializer(serializers.ModelSerializer):
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ActivityRegistration
        fields = [
            'id', 'activity', 'activity_title', 'user', 'user_username',
            'status', 'status_display', 'registered_at', 'checked_in_at',
        ]
        read_only_fields = ['registered_at', 'checked_in_at', 'status_display']
