"""
社交视图 - 校园打卡平台
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import Moment, MomentComment, Message
from .forms import MomentForm, MomentCommentForm


def moments_list(request):
    """动态广场"""
    moments = Moment.objects.select_related('user', 'activity').prefetch_related('images', 'likes').order_by('-created_at')
    
    # 分页
    paginator = Paginator(moments, 10)
    page = request.GET.get('page')
    moments = paginator.get_page(page)
    
    # 表单
    form = None
    if request.user.is_authenticated:
        form = MomentForm(user=request.user)
    
    return render(request, 'social/moments.html', {
        'moments': moments,
        'form': form
    })


@login_required
def publish_moment(request):
    """发布动态"""
    if request.method == 'POST':
        form = MomentForm(user=request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            moment = form.save(commit=False)
            moment.user = request.user
            moment.save()
            
            # 保存图片
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                from .models import MomentImage
                MomentImage.objects.create(moment=moment, image=image, order=i)
            
            messages.success(request, '动态发布成功！')
            return redirect('social:moments')
        else:
            messages.error(request, '发布失败，请检查内容')
    
    return redirect('social:moments')


@login_required
@require_POST
def like_moment(request, moment_id):
    """点赞/取消点赞动态"""
    moment = get_object_or_404(Moment, id=moment_id)
    
    if request.user in moment.likes.all():
        moment.likes.remove(request.user)
        liked = False
    else:
        moment.likes.add(request.user)
        liked = True
        
        # 创建通知
        if moment.user != request.user:
            Message.objects.create(
                recipient=moment.user,
                sender=request.user,
                message_type='like',
                title='有人赞了你的动态',
                content=f'{request.user.username} 赞了你的动态',
                related_moment=moment
            )
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'likes_count': moment.likes.count()
    })


@login_required
@require_POST
def comment_moment(request, moment_id):
    """评论动态"""
    moment = get_object_or_404(Moment, id=moment_id)
    form = MomentCommentForm(request.POST)
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.moment = moment
        comment.user = request.user
        comment.save()
        
        # 创建通知
        if moment.user != request.user:
            Message.objects.create(
                recipient=moment.user,
                sender=request.user,
                message_type='comment',
                title='有人评论了你的动态',
                content=f'{request.user.username} 评论：{comment.content}',
                related_moment=moment
            )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': comment.user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    
    return JsonResponse({'success': False, 'message': '评论失败'})


@login_required
def delete_moment(request, moment_id):
    """删除动态"""
    moment = get_object_or_404(Moment, id=moment_id)
    
    if moment.user != request.user and not request.user.is_staff:
        messages.error(request, '您没有权限删除此动态')
        return redirect('social:moments')
    
    moment.delete()
    messages.success(request, '动态已删除')
    return redirect('social:moments')


@login_required
def messages_list(request):
    """消息列表"""
    messages_qs = Message.objects.filter(recipient=request.user).order_by('-created_at')
    
    # 分页
    paginator = Paginator(messages_qs, 20)
    page = request.GET.get('page')
    messages_list = paginator.get_page(page)
    
    # 标记为已读
    unread_messages = Message.objects.filter(recipient=request.user, is_read=False)
    for msg in unread_messages:
        msg.mark_as_read()
    
    return render(request, 'social/messages.html', {
        'messages': messages_list
    })


@login_required
def unread_count(request):
    """获取未读消息数量"""
    count = Message.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
@require_POST
def mark_all_read(request):
    """标记所有消息为已读"""
    Message.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


from rest_framework import viewsets, permissions
from .serializers import MomentSerializer


class MomentViewSet(viewsets.ModelViewSet):
    """动态API视图集"""
    queryset = Moment.objects.all()
    serializer_class = MomentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """返回关注的人的动态和自己的动态"""
        user = self.request.user
        # 简化：返回所有公开动态
        return Moment.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        """创建时自动设置用户"""
        serializer.save(user=self.request.user)