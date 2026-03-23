"""
活动表单 - 校园打卡平台
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import Activity, ActivityComment, Category


class ActivityForm(forms.ModelForm):
    """活动创建/编辑表单"""
    class Meta:
        model = Activity
        fields = [
            'title', 'description', 'cover_image', 'category',
            'start_time', 'end_time', 'registration_deadline',
            'location', 'location_lat', 'location_lng',
            'max_participants', 'min_participants', 'points',
            'requirements', 'allow_checkin_before_start', 'checkin_radius',
            'managers',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': '请输入活动标题'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': '请详细描述活动内容'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'registration_deadline': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'location': forms.TextInput(attrs={
                'placeholder': '请输入活动地点'
            }),
            'location_lat': forms.NumberInput(attrs={
                'placeholder': '纬度（可选）',
                'step': 'any'
            }),
            'location_lng': forms.NumberInput(attrs={
                'placeholder': '经度（可选）',
                'step': 'any'
            }),
            'max_participants': forms.NumberInput(attrs={
                'min': 1
            }),
            'min_participants': forms.NumberInput(attrs={
                'min': 1
            }),
            'points': forms.NumberInput(attrs={
                'min': 0
            }),
            'requirements': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '参与要求（可选）'
            }),
            'allow_checkin_before_start': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'checkin_radius': forms.NumberInput(attrs={
                'min': 0,
                'placeholder': '允许打卡的范围（米）'
            }),
            'managers': forms.SelectMultiple(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 设置分类选项
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = '选择分类'

        # 设置活动管理者选项
        User = get_user_model()
        self.fields['managers'].queryset = User.objects.exclude(role='admin')
        self.fields['managers'].required = False
        self.fields['managers'].label = '活动管理者（可选）'
        self.fields['managers'].help_text = '可选，活动管理者可以协助编辑活动内容'

        # 为所有字段添加 Bootstrap 样式（除了特殊字段）
        for field_name, field in self.fields.items():
            if field_name == 'allow_checkin_before_start':
                # 复选框
                field.widget.attrs['class'] = 'form-check-input'
            elif field_name in ['category', 'managers']:
                # 下拉框 / 多选框
                field.widget.attrs['class'] = 'form-select'
            elif field_name == 'cover_image':
                # 文件上传
                field.widget.attrs['class'] = 'form-control'
            else:
                # 其他输入框
                field.widget.attrs.setdefault('class', '')
                field.widget.attrs['class'] += ' form-control'

        # 设置默认值
        self.fields['max_participants'].initial = 50
        self.fields['points'].initial = 10
        self.fields['checkin_radius'].initial = 100

        # 设置必填字段
        self.fields['title'].required = True
        self.fields['category'].required = True
        self.fields['description'].required = True
        self.fields['start_time'].required = True
        self.fields['end_time'].required = True
        self.fields['location'].required = True
        self.fields['max_participants'].required = True
        self.fields['points'].required = True

    def clean(self):
        """表单验证"""
        cleaned_data = super().clean()

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        registration_deadline = cleaned_data.get('registration_deadline')

        # 验证开始时间早于结束时间
        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError('开始时间必须早于结束时间')

        # 验证报名截止时间早于活动开始时间
        if registration_deadline and start_time:
            if registration_deadline >= start_time:
                raise forms.ValidationError('报名截止时间必须早于活动开始时间')

        # 验证最大参与人数大于最小参与人数
        max_participants = cleaned_data.get('max_participants')
        min_participants = cleaned_data.get('min_participants')

        if max_participants and min_participants:
            if max_participants < min_participants:
                raise forms.ValidationError('最大参与人数不能小于最小参与人数')

        return cleaned_data

    def clean_title(self):
        """验证标题"""
        title = self.cleaned_data.get('title')
        if title and len(title) < 2:
            raise forms.ValidationError('标题至少需要2个字符')
        return title

    def clean_description(self):
        """验证描述"""
        description = self.cleaned_data.get('description')
        if description and len(description) < 10:
            raise forms.ValidationError('描述至少需要10个字符')
        return description


class ActivityCommentForm(forms.ModelForm):
    """活动评论表单"""
    class Meta:
        model = ActivityComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '发表评论...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['content'].required = True

    def clean_content(self):
        """验证评论内容"""
        content = self.cleaned_data.get('content')
        if content and len(content) < 2:
            raise forms.ValidationError('评论内容至少需要2个字符')
        return content