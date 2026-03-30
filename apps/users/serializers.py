
"""用户序列化器 - 校园打卡平台"""
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    streak_days = serializers.IntegerField(read_only=True)
    total_checkins = serializers.IntegerField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'student_id', 'real_name', 'avatar',
            'phone', 'gender', 'department', 'major', 'grade',
            'role', 'role_display', 'points', 'level', 'level_title',
            'streak_days', 'total_checkins', 'followers_count',
            'following_count', 'created_at',
        ]
        read_only_fields = [
            'role_display', 'points', 'level', 'level_title',
            'streak_days', 'total_checkins', 'followers_count',
            'following_count', 'created_at',
        ]
