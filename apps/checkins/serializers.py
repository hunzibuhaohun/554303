
"""打卡序列化器 - 校园打卡平台"""
from rest_framework import serializers

from .models import CheckIn, CheckInPhoto


class CheckInPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckInPhoto
        fields = ['id', 'image', 'uploaded_at']


class CheckInSerializer(serializers.ModelSerializer):
    photos = CheckInPhotoSerializer(many=True, read_only=True)
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    content = serializers.CharField(source='remark', required=False, allow_blank=True)

    class Meta:
        model = CheckIn
        fields = [
            'id', 'activity', 'activity_title', 'content',
            'latitude', 'longitude', 'accuracy', 'location_name',
            'status', 'points_earned', 'check_in_date', 'created_at', 'photos',
        ]
        read_only_fields = ['status', 'points_earned', 'check_in_date', 'created_at']

    def validate(self, attrs):
        remark = attrs.get('remark', '')
        if not str(remark).strip():
            raise serializers.ValidationError({'content': '打卡内容不能为空'})
        return attrs
