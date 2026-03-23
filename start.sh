#!/bin/bash
# 校园打卡平台启动脚本 (Linux/Mac)

echo "🚀 启动校园打卡平台..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt

# 数据库迁移
echo "🗄️ 执行数据库迁移..."
python manage.py migrate

# 收集静态文件
echo "📁 收集静态文件..."
python manage.py collectstatic --noinput

# 创建超级用户（如果不存在）
echo "👤 检查超级用户..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ 创建超级用户: admin / admin123")
EOF

# 启动开发服务器
echo "🌐 启动服务器..."
echo "访问地址: http://127.0.0.1:8000/"
echo "管理后台: http://127.0.0.1:8000/admin/ (admin / admin123)"
python manage.py runserver
