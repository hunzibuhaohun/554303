"""
API分页配置
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页配置"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
