"""
用户表单 - 校园打卡平台
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.core.validators import RegexValidator
from .models import User


class UserRegistrationForm(UserCreationForm):
    """用户注册表单"""
    student_id = forms.CharField(
        label='学号',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入学号'
        })
    )
    real_name = forms.CharField(
        label='真实姓名',
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入真实姓名'
        })
    )
    email = forms.EmailField(
        label='邮箱',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入邮箱'
        })
    )
    phone = forms.CharField(
        label='手机号',
        max_length=11,
        required=False,
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '请输入有效的手机号')],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入手机号'
        })
    )
    department = forms.CharField(
        label='院系',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入院系'
        })
    )
    major = forms.CharField(
        label='专业',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入专业'
        })
    )
    grade = forms.CharField(
        label='年级',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '如：2022级'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'student_id', 'real_name', 'email', 'phone',
                  'department', 'major', 'grade', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入用户名'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 统一设置密码输入框样式
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请输入密码（至少8位）'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请再次输入密码'
        })

    def clean_student_id(self):
        """验证学号唯一性"""
        student_id = self.cleaned_data.get('student_id')
        if User.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('该学号已被注册')
        return student_id

    def clean_email(self):
        """验证邮箱唯一性"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已被注册')
        return email


class UserLoginForm(AuthenticationForm):
    """用户登录表单"""
    username = forms.CharField(
        label='用户名/学号',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入用户名或学号'
        })
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
    )


class UserProfileForm(forms.ModelForm):
    """用户资料编辑表单"""
    class Meta:
        model = User
        fields = ['real_name', 'gender', 'phone', 'department', 'major',
                  'grade', 'avatar', 'bio']
        widgets = {
            'real_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入真实姓名'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入手机号'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入院系'
            }),
            'major': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入专业'
            }),
            'grade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '如：2022级'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '介绍一下自己吧...'
            }),
        }


class UserSettingsForm(forms.ModelForm):
    """用户设置表单"""
    # 通知设置
    notify_activity = forms.BooleanField(
        label='活动提醒',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    notify_checkin = forms.BooleanField(
        label='打卡提醒',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    notify_system = forms.BooleanField(
        label='系统公告',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # 隐私设置
    public_profile = forms.BooleanField(
        label='公开个人资料',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    show_checkin = forms.BooleanField(
        label='显示打卡记录',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['email', 'phone']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入邮箱'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入手机号'
            }),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """自定义密码修改表单"""
    old_password = forms.CharField(
        label='当前密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入当前密码'
        })
    )
    new_password1 = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入新密码（至少8位）'
        }),
        help_text='密码必须包含至少8个字符，且不能全是数字'
    )
    new_password2 = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请再次输入新密码'
        })
    )


class PhoneBindForm(forms.Form):
    """手机号绑定表单"""
    phone = forms.CharField(
        label='手机号',
        max_length=11,
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '请输入有效的手机号')],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入手机号'
        })
    )
    verification_code = forms.CharField(
        label='验证码',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入验证码'
        })
    )


class PasswordResetRequestForm(forms.Form):
    """密码重置请求表单"""
    email = forms.EmailField(
        label='注册邮箱',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入注册时使用的邮箱'
        })
    )


class PasswordResetConfirmForm(forms.Form):
    """密码重置确认表单"""
    new_password = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入新密码'
        })
    )
    confirm_password = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请再次输入新密码'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('两次输入的密码不一致')

        return cleaned_data


class UserSearchForm(forms.Form):
    """用户搜索表单"""
    keyword = forms.CharField(
        label='搜索用户',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '输入用户名、学号或姓名'
        })
    )


class AvatarUploadForm(forms.ModelForm):
    """头像上传表单"""
    class Meta:
        model = User
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }