"""活动序列化器 - 校园打卡平台"""
from rest_framework import serializers
from .models import Activity, ActivityRegistration, ActivityComment


class ActivityCommentSerializer(serializers.ModelSerializer):
    """活动评论序列化器"""
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActivityComment
        fields = ['id', 'user', 'user_username', 'content', 'created_at']


class ActivitySerializer(serializers.ModelSerializer):
    """活动序列化器"""
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    comments = ActivityCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'cover_image', 'category', 'category_name',
            'creator', 'creator_username', 'start_time', 'end_time',
            'registration_deadline', 'location', 'location_lat', 'location_lng',
            'max_participants', 'min_participants', 'points', 'requirements',
            'allow_checkin_before_start', 'checkin_radius', 'status', 'is_public',
            'created_at', 'comments'
        ]
        read_only_fields = ['creator', 'status', 'created_at']


class ActivityRegistrationSerializer(serializers.ModelSerializer):
    """活动报名序列化器"""
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActivityRegistration
        fields = [
            'id', 'activity', 'activity_title', 'user', 'user_username',
            'status', 'remark', 'registered_at', 'checkin_count'
        ]
        read_only_fields = ['status', 'registered_at', 'checkin_count']