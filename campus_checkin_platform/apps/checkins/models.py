"""
打卡模型 - 校园打卡平台
对应论文第3章数据库设计（表2.4） + 第4章4.2.3节核心打卡模块
包含打卡记录、打卡照片、积分记录三个模型
支持位置打卡、照片上传、审核流程、连续打卡、积分发放
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class CheckIn(models.Model):
    """打卡记录模型（核心模型）"""
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='checkins',
        verbose_name='打卡用户'
    )
    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.CASCADE,
        related_name='checkins',
        verbose_name='所属活动'
    )
    registration = models.OneToOneField(
        'activities.ActivityRegistration',
        on_delete=models.CASCADE,
        related_name='checkin',
        verbose_name='关联报名记录'
    )

    # 打卡内容
    remark = models.TextField('打卡备注', blank=True)

    # 定位信息（支持地图打卡）
    location_name = models.CharField('位置名称', max_length=200, blank=True)
    latitude = models.DecimalField('纬度', max_digits=10, decimal_places=7)
    longitude = models.DecimalField('经度', max_digits=10, decimal_places=7)
    accuracy = models.FloatField('精度(米)', null=True, blank=True)

    # 审核状态（论文中未强制要求，但你已实现，保留）
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_checkins',
        verbose_name='审核人'
    )
    review_note = models.TextField('审核备注', blank=True)

    # 积分奖励
    points_earned = models.PositiveIntegerField('获得积分', default=0)

    # 时间戳
    created_at = models.DateTimeField('打卡时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '打卡记录'
        verbose_name_plural = '打卡记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity', 'status']),
        ]
        # 防重复打卡：同一用户同一天同一活动只能打一次
        unique_together = ('user', 'activity', 'created_at')

    def __str__(self):
        return f"{self.user.username} - {self.activity.title} - {self.created_at.strftime('%Y-%m-%d')}"

    def approve(self, reviewer=None, note=''):
        """审核通过 + 发放积分 + 更新用户统计（核心逻辑）"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.review_note = note
        self.points_earned = self.activity.points   # 从活动设置获取积分

        # 更新用户积分和打卡统计（按论文User模型字段）
        self.user.points += self.points_earned
        self.user.total_points += self.points_earned
        self.user.checkin_count += 1
        self.user.save(update_fields=['points', 'total_points', 'checkin_count'])

        # 更新报名状态
        self.registration.status = 'completed'
        self.registration.save(update_fields=['status'])

        self.save()

    def reject(self, reviewer=None, note=''):
        """审核拒绝"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.review_note = note
        self.save()


class CheckInPhoto(models.Model):
    """打卡照片模型（支持多张照片）"""
    checkin = models.ForeignKey(
        CheckIn,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='所属打卡'
    )
    image = models.ImageField('照片', upload_to='checkins/%Y/%m/%d/')
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        verbose_name = '打卡照片'
        verbose_name_plural = '打卡照片'

    def __str__(self):
        return f"照片 - {self.checkin}"


class PointRecord(models.Model):
    """积分记录模型（用于积分历史和后台统计）"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_records',
        verbose_name='用户'
    )
    points = models.IntegerField('积分变化', help_text='正数为增加，负数为减少')
    reason = models.CharField('获得原因', max_length=100, help_text='如：每日打卡、连续打卡奖励等')
    related_checkin = models.ForeignKey(          # 新增关联，便于追溯
        CheckIn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联打卡记录'
    )
    created_at = models.DateTimeField('记录时间', auto_now_add=True)

    class Meta:
        verbose_name = "积分记录"
        verbose_name_plural = "积分记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} +{self.points}分 - {self.reason}"