"""
社交模型 - 校园打卡平台
"""
from django.db import models
from django.conf import settings


class Moment(models.Model):
    """动态（朋友圈）模型"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moments'
    )
    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moments'
    )
    content = models.TextField('内容', max_length=500)
    
    # 互动数据
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_moments',
        blank=True
    )
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '动态'
        verbose_name_plural = '动态'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}..."
    
    @property
    def comments_count(self):
        return self.comments.count()


class MomentImage(models.Model):
    """动态图片"""
    moment = models.ForeignKey(
        Moment,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField('图片', upload_to='moments/%Y/%m/%d/')
    order = models.PositiveIntegerField('排序', default=0)
    
    class Meta:
        ordering = ['order']


class MomentComment(models.Model):
    """动态评论"""
    moment = models.ForeignKey(
        Moment,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField('内容', max_length=200)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']


class Message(models.Model):
    """系统消息"""
    MESSAGE_TYPES = [
        ('system', '系统通知'),
        ('like', '点赞'),
        ('comment', '评论'),
        ('follow', '关注'),
        ('activity', '活动提醒'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    message_type = models.CharField(
        '类型',
        max_length=20,
        choices=MESSAGE_TYPES
    )
    title = models.CharField('标题', max_length=100)
    content = models.TextField('内容')
    
    # 关联对象
    related_activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    related_moment = models.ForeignKey(
        Moment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # 状态
    is_read = models.BooleanField('是否已读', default=False)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '消息'
        verbose_name_plural = '消息'
        ordering = ['-created_at']
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
