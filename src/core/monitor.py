"""
社交媒体监控器
"""

import gc
import sys
from typing import List

from ..core.models import SimpleUser
from ..managers.config_manager import SocialMediaConfig
from ..managers.rss_manager import RSSManager


class SocialMediaMonitor:
    """社交媒体监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.config = SocialMediaConfig()
        self.rss_manager = RSSManager(self.config)
    
    def monitor_all_users(self) -> None:
        """监控所有配置的用户"""
        print("🚀 开始监控所有用户...")
        print("=" * 80)
        
        users = self.config.get_users()
        success_count = 0
        total_count = len(users)
        
        for user in users:
            feed, source_url = self.rss_manager.fetch_user_content(user)
            if feed and source_url:
                self.rss_manager.process_user_content(user, feed, source_url)
                success_count += 1
            print("\n" + "=" * 80 + "\n")
        
        print(f"📊 监控完成! 成功获取 {success_count}/{total_count} 个用户的内容")
    
    def monitor_specific_user(self, username: str) -> None:
        """监控指定用户"""
        users = self.config.get_users()
        target_user = None
        
        for user in users:
            if user.id.lower() == username.lower():
                target_user = user
                break
        
        if not target_user:
            print(f"❌ 未找到用户: {username}")
            print(f"💡 支持的用户列表:")
            for user in users:
                print(f"   - {user.id}: {user.name}")
            return
        
        feed, source_url = self.rss_manager.fetch_user_content(target_user)
        if feed and source_url:
            self.rss_manager.process_user_content(target_user, feed, source_url)
        else:
            print(f"😞 无法获取 {username} 的内容")
    
    def add_user(self, username: str, description: str, platform: str = "twitter") -> None:
        """动态添加用户"""
        # 验证平台是否支持
        supported_platforms = self.config.get_platforms()
        if platform not in supported_platforms:
            print(f"❌ 不支持的平台: {platform}")
            print(f"💡 支持的平台: {', '.join(supported_platforms)}")
            return
        
        new_user = SimpleUser(username, description, platform)
        print(f"📝 已添加用户: {description} (平台: {platform.upper()})")
        
        feed, source_url = self.rss_manager.fetch_user_content(new_user)
        if feed and source_url:
            self.rss_manager.process_user_content(new_user, feed, source_url)
        else:
            print(f"⚠️ 无法获取 {description} 的内容，请检查用户名")
    
    def list_users(self) -> None:
        """列出所有配置的用户"""
        users = self.config.get_users()
        print(f"📋 配置的用户列表 (共 {len(users)} 个):")
        print("=" * 50)
        
        for i, user in enumerate(users, 1):
            print(f"{i:2d}. {user.name} ({user.platform.upper()})")
            print(f"    ID: {user.id}")
        
        print("=" * 50)
    
    def get_platform_stats(self) -> None:
        """获取平台统计信息"""
        users = self.config.get_users()
        platform_counts = {}
        
        for user in users:
            platform = user.platform.upper()
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        print("📊 平台统计:")
        print("=" * 30)
        for platform, count in platform_counts.items():
            print(f"{platform}: {count} 个用户")
        print("=" * 30)
