"""
API序列化器 - 校园打卡平台
"""
from rest_framework import serializers
from apps.users.models import User
from apps.activities.models import Activity, Category, ActivityRegistration, ActivityComment
from apps.checkins.models import CheckIn
from apps.social.models import Moment, MomentComment


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'student_id', 'real_name', 'avatar', 
                  'department', 'points', 'total_checkins']


class CategorySerializer(serializers.ModelSerializer):
    """分类序列化器"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color']


class ActivityListSerializer(serializers.ModelSerializer):
    """活动列表序列化器"""
    category = CategorySerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = ['id', 'title', 'description', 'cover_image', 'category',
                  'creator', 'start_time', 'end_time', 'location', 'points',
                  'status', 'max_participants', 'participants_count', 
                  'is_registered', 'registration_percentage']
    
    def get_participants_count(self, obj):
        return obj.participants.count()
    
    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(user=request.user).exists()
        return False


class ActivityDetailSerializer(serializers.ModelSerializer):
    """活动详情序列化器"""
    category = CategorySerializer(read_only=True)
    creator = UserSerializer(read_only=True)
    
    class Meta:
        model = Activity
        fields = '__all__'


class ActivityRegistrationSerializer(serializers.ModelSerializer):
    """活动报名序列化器"""
    activity = ActivityListSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ActivityRegistration
        fields = ['id', 'user', 'activity', 'status', 'registered_at']


class CheckInSerializer(serializers.ModelSerializer):
    """打卡记录序列化器"""
    activity = ActivityListSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    photos = serializers.SerializerMethodField()
    
    class Meta:
        model = CheckIn
        fields = ['id', 'user', 'activity', 'remark', 'location_name',
                  'status', 'points_earned', 'created_at', 'photos']
    
    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]


class MomentSerializer(serializers.ModelSerializer):
    """动态序列化器"""
    user = UserSerializer(read_only=True)
    activity = ActivityListSerializer(read_only=True)
    images = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Moment
        fields = ['id', 'user', 'activity', 'content', 'images',
                  'likes_count', 'comments_count', 'is_liked', 'created_at']
    
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
    """动态评论序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MomentComment
        fields = ['id', 'user', 'content', 'created_at']
