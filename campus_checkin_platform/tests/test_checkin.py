import pytest
from django.test import TestCase
from django.db.utils import IntegrityError
from datetime import date, timedelta
from apps.users.models import User
from apps.activities.models import Activity
from apps.checkins.models import CheckIn, PointRecord

@pytest.mark.django_db
class TestCheckInLogic(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test",
            password="123456",
            student_id="224324"
        )
        self.activity = Activity.objects.create(
            title="每日阅读",
            category="学习",
            creator=self.user,
            start_date=date.today()
        )

    def test_continuous_checkin_days(self):
        """测试连续打卡天数计算"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 今天打卡
        CheckIn.objects.create(
            user=self.user,
            activity=self.activity,
            content="Day1 打卡",
            check_in_date=today
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.continuous_days, 1)

        # 昨天打卡 → 连续2天
        CheckIn.objects.create(
            user=self.user,
            activity=self.activity,
            content="Day2 打卡",
            check_in_date=yesterday
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.continuous_days, 2)

    def test_checkin_points_award(self):
        """测试打卡成功后发放积分与积分记录"""
        old_points = self.user.points

        checkin = CheckIn.objects.create(
            user=self.user,
            activity=self.activity,
            content="今日完成阅读打卡，坚持学习！"
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.points, old_points + 10)  # 基础10分
        self.assertTrue(
            PointRecord.objects.filter(
                user=self.user,
                points=10,
                reason__icontains="打卡"
            ).exists()
        )

    def test_same_day_checkin_unique(self):
        """测试同一天同一活动不能重复打卡"""
        CheckIn.objects.create(
            user=self.user,
            activity=self.activity,
            content="第一次打卡"
        )

        # 重复创建 → 数据库唯一约束报错
        with self.assertRaises(IntegrityError):
            CheckIn.objects.create(
                user=self.user,
                activity=self.activity,
                content="重复打卡"
            )

    def test_checkin_content_not_empty(self):
        """测试打卡内容不能为空"""
        with self.assertRaises(Exception):  # 根据你实际校验改为 ValidationError
            CheckIn.objects.create(
                user=self.user,
                activity=self.activity,
                content=""  # 空内容不允许
            )