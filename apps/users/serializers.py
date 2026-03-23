"""用户序列化器 - 校园打卡平台"""
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'student_id', 'avatar',
            'phone', 'gender', 'department', 'major', 'grade',
            'points', 'level', 'continuous_checkin_days', 'total_checkin_days',
            'followers_count', 'following_count', 'created_at'
        ]
        read_only_fields = ['points', 'level', 'continuous_checkin_days', 'total_checkin_days']