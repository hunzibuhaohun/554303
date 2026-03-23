"""打卡序列化器 - 校园打卡平台"""
from rest_framework import serializers
from .models import CheckIn, CheckInPhoto


class CheckInPhotoSerializer(serializers.ModelSerializer):
    """打卡照片序列化器"""

    class Meta:
        model = CheckInPhoto
        fields = ['id', 'image', 'uploaded_at']


class CheckInSerializer(serializers.ModelSerializer):
    """打卡序列化器"""
    photos = CheckInPhotoSerializer(many=True, read_only=True)
    activity_title = serializers.CharField(source='activity.title', read_only=True)

    class Meta:
        model = CheckIn
        fields = [
            'id', 'activity', 'activity_title', 'remark',
            'latitude', 'longitude', 'accuracy', 'location_name',
            'status', 'points_earned', 'created_at', 'photos'
        ]
        read_only_fields = ['status', 'points_earned', 'created_at']