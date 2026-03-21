"""
用户模型 - 校园打卡平台
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """自定义用户模型"""
    GENDER_CHOICES = [
        ('male', '男'),
        ('female', '女'),
        ('secret', '保密'),
    ]

    ROLE_CHOICES = [
        ('student', '学生'),
        ('teacher', '教师'),
        ('admin', '管理员'),
    ]

    # 基本信息
    student_id = models.CharField(
        '学号',
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )
    real_name = models.CharField('真实姓名', max_length=50, default='')
    gender = models.CharField(
        '性别',
        max_length=10,
        choices=GENDER_CHOICES,
        default='secret'
    )
    phone = models.CharField(
        '手机号',
        max_length=11,
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '请输入有效的手机号')],
        blank=True
    )

    # 学校信息
    department = models.CharField('院系', max_length=100, blank=True)
    major = models.CharField('专业', max_length=100, blank=True)
    grade = models.CharField('年级', max_length=20, blank=True)

    # 角色与状态
    role = models.CharField(
        '角色',
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )

    def is_student(self):
        return self.role == 'student'

    def is_activity_manager(self):
        return self.role == 'teacher'

    def is_platform_admin(self):
        return self.role == 'admin'

    def can_create_activity(self):
        return self.role in ['teacher', 'admin']

    def can_manage_activity(self, activity):
        if self.role == 'admin':
            return True
        if self.role == 'teacher' and activity.creator_id == self.id:
            return True
        return False

    is_verified = models.BooleanField('是否认证', default=False)

    # 个人资料
    avatar = models.ImageField(
        '头像',
        upload_to='avatars/%Y/%m/',
        default='avatars/default.png',
        blank=True
    )
    bio = models.TextField('个人简介', max_length=500, blank=True)

    # 积分系统
    points = models.PositiveIntegerField('当前积分', default=0)
    total_checkins = models.PositiveIntegerField('累计打卡次数', default=0)

    # 连续打卡统计 - 新增
    streak_days = models.PositiveIntegerField('当前连续打卡天数', default=0)
    longest_streak = models.PositiveIntegerField('最长连续打卡天数', default=0)
    last_checkin_date = models.DateField('最后打卡日期', null=True, blank=True)

    # 活动统计 - 新增
    activities_joined = models.PositiveIntegerField('参与活动数', default=0)
    activities_created = models.PositiveIntegerField('创建活动数', default=0)

    # 等级系统 - 新增
    level = models.PositiveIntegerField('当前等级', default=1)
    level_title = models.CharField('等级称号', max_length=20, default='新手')

    # 社交数据
    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        through='FollowRelation',
        blank=True
    )

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    # 设置相关字段 - 新增
    notify_activity = models.BooleanField('活动提醒', default=True)
    notify_checkin = models.BooleanField('打卡提醒', default=True)
    notify_system = models.BooleanField('系统公告', default=True)
    public_profile = models.BooleanField('公开个人资料', default=True)
    show_checkin = models.BooleanField('显示打卡记录', default=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['department']),
            models.Index(fields=['points']),
            models.Index(fields=['streak_days']),
        ]

    def __str__(self):
        return f"{self.username} ({self.real_name or '未实名'})"

    def get_full_name(self):
        """获取完整姓名"""
        return self.real_name or self.username

    def get_short_name(self):
        """获取简称"""
        return self.username

    @property
    def streak_days_calc(self):
        """计算连续打卡天数（动态计算）"""
        if not hasattr(self, '_streak_cache'):
            from apps.checkins.models import CheckIn

            checkins = CheckIn.objects.filter(
                user=self,
                status='approved'
            ).order_by('-created_at')

            if not checkins.exists():
                self._streak_cache = 0
                return 0

            streak = 0
            today = timezone.now().date()
            check_dates = set(c.created_at.date() for c in checkins)

            # 如果今天没打卡，从昨天开始算
            if today not in check_dates:
                today -= timedelta(days=1)

            while today in check_dates:
                streak += 1
                today -= timedelta(days=1)

            self._streak_cache = streak

        return self._streak_cache

    def update_streak(self):
        """更新连续打卡天数"""
        from apps.checkins.models import CheckIn

        today = timezone.now().date()

        # 检查今天是否已打卡
        today_checkin = CheckIn.objects.filter(
            user=self,
            created_at__date=today,
            status='approved'
        ).exists()

        if today_checkin:
            # 检查昨天是否打卡
            yesterday = today - timedelta(days=1)
            yesterday_checkin = CheckIn.objects.filter(
                user=self,
                created_at__date=yesterday,
                status='approved'
            ).exists()

            if yesterday_checkin or self.streak_days == 0:
                self.streak_days += 1
            # 如果昨天没打但之前打了，说明是断开后重新开始，保持1

            self.last_checkin_date = today

            # 更新最长连续记录
            if self.streak_days > self.longest_streak:
                self.longest_streak = self.streak_days

            self.save(update_fields=['streak_days', 'longest_streak', 'last_checkin_date'])

    def check_streak_break(self):
        """检查连续打卡是否中断"""
        if not self.last_checkin_date:
            return

        today = timezone.now().date()
        days_since_last = (today - self.last_checkin_date).days

        # 如果超过1天没打卡，重置连续天数
        if days_since_last > 1:
            self.streak_days = 0
            self.save(update_fields=['streak_days'])

    def add_points(self, points, description=''):
        """添加积分"""
        self.points += points
        self.save(update_fields=['points'])

        # 记录积分历史
        PointHistory.objects.create(
            user=self,
            amount=points,
            description=description
        )

        # 检查等级提升
        self.check_level_up()

    def check_level_up(self):
        """检查是否升级"""
        new_level = self.calculate_level()
        if new_level > self.level:
            self.level = new_level
            self.level_title = self.get_level_title(new_level)
            self.save(update_fields=['level', 'level_title'])

    def calculate_level(self):
        """根据积分计算等级"""
        points = self.points
        if points < 100:
            return 1
        elif points < 300:
            return 2
        elif points < 600:
            return 3
        elif points < 1000:
            return 4
        elif points < 1500:
            return 5
        elif points < 2200:
            return 6
        elif points < 3000:
            return 7
        elif points < 4000:
            return 8
        elif points < 5500:
            return 9
        else:
            return 10

    @staticmethod
    def get_level_title(level):
        """获取等级称号"""
        titles = {
            1: '新手',
            2: '活跃者',
            3: '打卡达人',
            4: '校园明星',
            5: '活动专家',
            6: '社交达人',
            7: '资深玩家',
            8: '传奇人物',
            9: '校园传说',
            10: '打卡之神',
        }
        return titles.get(level, '未知')

    def get_next_level_points(self):
        """获取下一级所需积分"""
        level_thresholds = {
            1: 100,
            2: 300,
            3: 600,
            4: 1000,
            5: 1500,
            6: 2200,
            7: 3000,
            8: 4000,
            9: 5500,
            10: 999999,
        }
        return level_thresholds.get(self.level, 999999)

    def get_level_progress(self):
        """获取当前等级进度百分比"""
        current_threshold = self.get_level_threshold(self.level)
        next_threshold = self.get_next_level_points()

        if next_threshold == 999999:
            return 100

        progress = ((self.points - current_threshold) /
                   (next_threshold - current_threshold)) * 100
        return min(100, max(0, progress))

    @staticmethod
    def get_level_threshold(level):
        """获取等级起始积分"""
        thresholds = {
            1: 0,
            2: 100,
            3: 300,
            4: 600,
            5: 1000,
            6: 1500,
            7: 2200,
            8: 3000,
            9: 4000,
            10: 5500,
        }
        return thresholds.get(level, 0)

    def increment_checkin_count(self):
        """增加打卡计数"""
        self.total_checkins += 1
        self.save(update_fields=['total_checkins'])

    def increment_activity_joined(self):
        """增加参与活动计数"""
        self.activities_joined += 1
        self.save(update_fields=['activities_joined'])

    def increment_activity_created(self):
        """增加创建活动计数"""
        self.activities_created += 1
        self.save(update_fields=['activities_created'])

    def get_achievement_count(self):
        """获取成就数量"""
        return self.achievements.count()

    def has_achievement(self, achievement_type):
        """检查是否拥有某成就"""
        return self.achievements.filter(achievement_type=achievement_type).exists()

    def award_achievement(self, achievement_type, name, description, level='bronze'):
        """授予成就"""
        achievement, created = UserAchievement.objects.get_or_create(
            user=self,
            achievement_type=achievement_type,
            defaults={
                'name': name,
                'description': description,
                'level': level
            }
        )
        return created


class FollowRelation(models.Model):
    """关注关系模型"""
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follow_relations_as_follower',
        verbose_name='关注者'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follow_relations_as_following',
        verbose_name='被关注者'
    )
    created_at = models.DateTimeField('关注时间', auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'following']
        verbose_name = '关注关系'
        verbose_name_plural = '关注关系'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower.username} 关注 {self.following.username}"


class UserAchievement(models.Model):
    """用户成就模型"""
    ACHIEVEMENT_TYPES = [
        ('first_checkin', '首次打卡'),
        ('streak_3', '连续3天'),
        ('streak_7', '连续7天'),
        ('streak_30', '连续30天'),
        ('streak_100', '连续100天'),
        ('points_100', '积分破百'),
        ('points_500', '积分破五百'),
        ('points_1000', '积分破千'),
        ('creator', '活动创建者'),
        ('popular', '人气王'),
        ('social', '社交达人'),
    ]

    LEVEL_CHOICES = [
        ('bronze', '铜'),
        ('silver', '银'),
        ('gold', '金'),
        ('platinum', '白金'),
        ('diamond', '钻石'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='achievements',
        verbose_name='用户'
    )
    achievement_type = models.CharField(
        '成就类型',
        max_length=20,
        choices=ACHIEVEMENT_TYPES
    )
    name = models.CharField('成就名称', max_length=50)
    description = models.TextField('成就描述', blank=True)
    icon = models.CharField('图标', max_length=50, default='🏅')
    level = models.CharField(
        '等级',
        max_length=10,
        choices=LEVEL_CHOICES,
        default='bronze'
    )
    earned_at = models.DateTimeField('获得时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户成就'
        verbose_name_plural = '用户成就'
        unique_together = ['user', 'achievement_type']
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class PointHistory(models.Model):
    """积分历史记录"""
    TRANSACTION_TYPES = [
        ('earn', '获得'),
        ('spend', '消费'),
        ('deduct', '扣除'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='point_history',
        verbose_name='用户'
    )
    amount = models.IntegerField('积分变动')
    transaction_type = models.CharField(
        '交易类型',
        max_length=10,
        choices=TRANSACTION_TYPES,
        default='earn'
    )
    description = models.CharField('描述', max_length=200)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '积分记录'
        verbose_name_plural = '积分记录'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.username}: {sign}{self.amount} ({self.description})"


class UserSettings(models.Model):
    """用户设置（可选的独立设置表）"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings_detail',
        verbose_name='用户'
    )

    # 通知设置
    email_notification = models.BooleanField('邮件通知', default=True)
    push_notification = models.BooleanField('推送通知', default=True)

    # 隐私设置
    show_email = models.BooleanField('公开邮箱', default=False)
    show_phone = models.BooleanField('公开手机', default=False)

    # 界面设置
    dark_mode = models.BooleanField('深色模式', default=False)
    language = models.CharField('语言', max_length=10, default='zh-CN')

    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '用户设置'
        verbose_name_plural = '用户设置'

    def __str__(self):
        return f"{self.user.username} 的设置"