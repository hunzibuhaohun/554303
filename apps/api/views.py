"""
API视图 - 校园打卡平台
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404

from apps.users.models import User
from apps.activities.models import Activity, ActivityRegistration
from apps.checkins.models import CheckIn
from apps.social.models import Moment
from .serializers import (
    UserSerializer, ActivityListSerializer, ActivityDetailSerializer,
    CheckInSerializer, MomentSerializer
)
from .pagination import StandardResultsSetPagination


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """用户API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ActivityViewSet(viewsets.ModelViewSet):
    """活动API"""
    queryset = Activity.objects.all()
    serializer_class = ActivityListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivityDetailSerializer
        return ActivityListSerializer
    
    def get_queryset(self):
        queryset = Activity.objects.filter(status__in=['upcoming', 'ongoing'])
        
        # 搜索
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(title__icontains=q)
        
        # 分类筛选
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """报名活动"""
        activity = self.get_object()
        
        if activity.is_full:
            return Response({'success': False, 'message': '活动已满员'})
        
        if ActivityRegistration.objects.filter(user=request.user, activity=activity).exists():
            return Response({'success': False, 'message': '已报名'})
        
        ActivityRegistration.objects.create(user=request.user, activity=activity)
        
        return Response({
            'success': True,
            'message': '报名成功',
            'points': activity.points
        })


class CheckInViewSet(viewsets.ModelViewSet):
    """打卡API"""
    serializer_class = CheckInSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CheckIn.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MomentViewSet(viewsets.ModelViewSet):
    """动态API"""
    queryset = Moment.objects.all()
    serializer_class = MomentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Moment.objects.select_related('user', 'activity').prefetch_related('images', 'likes')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """点赞/取消点赞"""
        moment = self.get_object()
        
        if moment.likes.filter(id=request.user.id).exists():
            moment.likes.remove(request.user)
            liked = False
        else:
            moment.likes.add(request.user)
            liked = True
        
        return Response({
            'success': True,
            'liked': liked,
            'likes_count': moment.likes.count()
        })
