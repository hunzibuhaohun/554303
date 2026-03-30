
"""社交序列化器 - 校园打卡平台"""
from rest_framework import serializers

from .models import Moment, MomentComment


class MomentCommentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = MomentComment
        fields = ['id', 'user', 'user_username', 'user_avatar', 'content', 'created_at']

    def get_user_avatar(self, obj):
        return obj.user.avatar.url if getattr(obj.user, 'avatar', None) else ''


class MomentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments = MomentCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Moment
        fields = [
            'id', 'user', 'user_username', 'user_avatar', 'content', 'images',
            'activity', 'likes_count', 'comments', 'created_at',
        ]
        read_only_fields = ['likes_count', 'created_at']

    def get_user_avatar(self, obj):
        return obj.user.avatar.url if getattr(obj.user, 'avatar', None) else ''

    def get_images(self, obj):
        return [image.image.url for image in obj.images.all()]

    def get_likes_count(self, obj):
        return obj.likes.count()
