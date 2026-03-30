
"""
API序列化器 - 校园打卡平台
"""
from rest_framework import serializers

from apps.activities.models import Activity, ActivityRegistration, Category
from apps.checkins.models import CheckIn
from apps.social.models import Moment, MomentComment
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'student_id', 'real_name', 'avatar',
            'department', 'points', 'total_checkins', 'role', 'role_display',
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color']


class ActivityListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'cover_image', 'category', 'creator',
            'start_time', 'end_time', 'location', 'points', 'status',
            'max_participants', 'participants_count', 'is_registered',
            'registration_percentage',
        ]

    def get_participants_count(self, obj):
        return obj.get_active_registration_count()

    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(
                user=request.user,
                status__in=['registered', 'checked_in', 'completed'],
            ).exists()
        return False


class ActivityDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    creator = UserSerializer(read_only=True)

    class Meta:
        model = Activity
        fields = '__all__'


class ActivityRegistrationSerializer(serializers.ModelSerializer):
    activity = ActivityListSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = ActivityRegistration
        fields = ['id', 'user', 'activity', 'status', 'registered_at', 'checked_in_at']


class CheckInSerializer(serializers.ModelSerializer):
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all(), write_only=True)
    activity_detail = ActivityListSerializer(source='activity', read_only=True)
    user = UserSerializer(read_only=True)
    photos = serializers.SerializerMethodField()
    content = serializers.CharField(source='remark', required=False, allow_blank=True)

    class Meta:
        model = CheckIn
        fields = [
            'id', 'user', 'activity', 'activity_detail', 'content',
            'location_name', 'status', 'points_earned', 'created_at', 'photos',
        ]
        read_only_fields = ['status', 'points_earned', 'created_at']

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def validate(self, attrs):
        if not str(attrs.get('remark', '')).strip():
            raise serializers.ValidationError({'content': '打卡内容不能为空'})
        return attrs


class MomentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    activity = ActivityListSerializer(read_only=True)
    images = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Moment
        fields = [
            'id', 'user', 'activity', 'content', 'images',
            'likes_count', 'comments_count', 'is_liked', 'created_at',
        ]

    def get_images(self, obj):
        return [img.image.url for img in obj.images.all()]

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class MomentCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = MomentComment
        fields = ['id', 'user', 'content', 'created_at']
