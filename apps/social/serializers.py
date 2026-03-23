"""社交序列化器 - 校园打卡平台"""
from rest_framework import serializers
from .models import Moment, MomentComment


class MomentCommentSerializer(serializers.ModelSerializer):
    """动态评论序列化器"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.CharField(source='user.avatar.url', read_only=True)

    class Meta:
        model = MomentComment
        fields = ['id', 'user', 'user_username', 'user_avatar', 'content', 'created_at']


class MomentSerializer(serializers.ModelSerializer):
    """动态序列化器"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.CharField(source='user.avatar.url', read_only=True)
    comments = MomentCommentSerializer(many=True, read_only=True)

    likes_count = serializers.IntegerField(default=0, read_only=True)

    class Meta:
        model = Moment
        fields = [
            'id', 'user', 'user_username', 'user_avatar', 'content', 'images',
            'activity', 'likes_count', 'comments', 'created_at'
        ]
        read_only_fields = ['likes_count', 'created_at']