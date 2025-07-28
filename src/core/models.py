"""
核心数据模型
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SimpleUser:
    """极简用户配置"""
    id: str  # 用于RSS URL填充
    name: str  # 用于显示的用户名
    platform: str  # 用户所属平台
