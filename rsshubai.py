import feedparser
import time
import gc
import sys
import yaml
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

class Platform(Enum):
    """支持的社交媒体平台"""
    TWITTER = "twitter"
    WEIBO = "weibo"

@dataclass
class SimpleUser:
    """极简用户配置"""
    id: str  # 用于RSS URL填充
    name: str  # 用于显示的用户名

class SocialMediaConfig:
    """社交媒体平台配置管理"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """初始化配置，从YAML文件读取"""
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载YAML配置文件"""
        try:
            if not os.path.exists(self.config_file):
                raise FileNotFoundError(f"配置文件 {self.config_file} 不存在")
            
            with open(self.config_file, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                print(f"✅ 成功加载配置文件: {self.config_file}")
                return config
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)
    
    def get_users(self) -> List[SimpleUser]:
        """从配置文件获取所有用户"""
        users = []
        platforms = self.config.get('platforms', {})
        
        for platform_name, platform_config in platforms.items():
            names = platform_config.get('names', [])
            for user_config in names:
                if isinstance(user_config, dict):
                    user_id = user_config.get('id', '')
                    user_name = user_config.get('name', f"{platform_name.upper()} 用户")
                    users.append(SimpleUser(user_id, user_name))
        
        return users
    
    def get_rss_templates(self) -> Dict[Platform, List[str]]:
        """获取RSS模板配置"""
        templates = {}
        platforms = self.config.get('platforms', {})
        
        for platform_name, platform_config in platforms.items():
            if platform_name == 'twitter':
                templates[Platform.TWITTER] = platform_config.get('rss_url', [])
            elif platform_name == 'weibo':
                templates[Platform.WEIBO] = platform_config.get('rss_url', [])
        
        return templates
    
    def generate_urls_for_platform(self, user: SimpleUser, platform: Platform) -> List[str]:
        """为指定平台生成用户的RSS URLs"""
        urls = []
        rss_templates = self.get_rss_templates()
        
        if platform not in rss_templates:
            return urls
        
        templates = rss_templates[platform]
        
        # 使用用户ID生成URLs
        for template in templates:
            url = template.format(username=user.id)
            urls.append(url)
        
        return urls
    
    def get_all_platforms_for_user(self, user: SimpleUser) -> List[Platform]:
        """获取用户可能存在的所有平台"""
        platforms = []
        config_platforms = self.config.get('platforms', {})
        
        for platform_name, platform_config in config_platforms.items():
            names = platform_config.get('names', [])
            for user_config in names:
                if isinstance(user_config, dict) and user_config.get('id') == user.id:
                    if platform_name == 'twitter':
                        platforms.append(Platform.TWITTER)
                    elif platform_name == 'weibo':
                        platforms.append(Platform.WEIBO)
                    break
        
        # 如果在配置中没有找到，尝试所有平台
        if not platforms:
            platforms = [Platform.TWITTER, Platform.WEIBO]
        
        return platforms

class ContentParser:
    """内容解析器"""
    
    @staticmethod
    def safe_str(value: Any, max_length: int = 20000) -> str:
        """安全地转换为字符串并限制长度"""
        try:
            if value is None:
                return "无内容"
            
            str_value = str(value)
            if len(str_value) > max_length:
                return str_value[:max_length] + "..."
            return str_value
        except Exception as e:
            return f"内容解析错误: {e}"
    
    @staticmethod
    def format_entry(entry: dict, index: int, platform: Platform) -> str:
        """格式化单个条目"""
        try:
            content_type = {
                Platform.TWITTER: "推文",
                Platform.WEIBO: "微博"
            }.get(platform, "内容")
            
            formatted = f"第 {index} 篇{content_type}:\n"
            id = entry.get('id', '无ID')
            formatted += f"ID: {id}\n"
            formatted += f"标题: {ContentParser.safe_str(entry.get('title', '无标题'))}\n"
            formatted += f"链接: {ContentParser.safe_str(entry.get('link', '无链接'))}\n"
            formatted += f"作者: {ContentParser.safe_str(entry.get('author', '无作者'))}\n"
            formatted += f"发布时间: {ContentParser.safe_str(entry.get('published', '无时间'))}\n"
            formatted += f"摘要: {ContentParser.safe_str(entry.get('summary', '无摘要'))}\n"
            formatted += "-" * 50
            return formatted
        except Exception as e:
            return f"格式化第 {index} 条内容时出错: {e}\n" + "-" * 50

class RSSManager:
    """RSS源管理器"""
    
    def __init__(self, config: SocialMediaConfig):
        """初始化RSS管理器"""
        self.config = config
    
    def try_rss_source(self, url: str) -> Tuple[Optional[Any], bool]:
        """尝试获取指定 RSS 源"""
        print(f"正在尝试 RSS 源: {url}")
        
        try:
            feed = feedparser.parse(url)
            
            status = getattr(feed, 'status', '未知')
            title = getattr(feed.feed, 'title', '无标题') if hasattr(feed, 'feed') else '无标题'
            entry_count = len(feed.entries) if hasattr(feed, 'entries') else 0
            
            print(f"  状态码: {status}")
            print(f"  RSS 标题: {title}")
            print(f"  文章数量: {entry_count}")
            
            if hasattr(feed, 'status') and feed.status == 200 and entry_count > 0:
                return feed, True
            elif entry_count > 0:
                return feed, True
            else:
                if hasattr(feed, 'bozo') and feed.bozo:
                    error_msg = str(getattr(feed, 'bozo_exception', '未知错误'))
                    print(f"  错误: {error_msg}")
                return None, False
                
        except Exception as e:
            print(f"  连接错误: {e}")
            return None, False
        finally:
            gc.collect()
    
    def fetch_user_content(self, user: SimpleUser) -> Tuple[Optional[Any], Optional[Platform]]:
        """智能获取用户内容，尝试所有可能的RSS源，一旦成功就停止"""
        print(f"\n🔍 正在尝试获取 {user.name}")
        print(f"📝 用户ID: {user.id}")
        print("=" * 60)
        
        # 获取用户可能存在的平台
        platforms = self.config.get_all_platforms_for_user(user)
        
        # 收集所有可能的RSS源和对应的平台信息
        all_sources = []
        for platform in platforms:
            urls = self.config.generate_urls_for_platform(user, platform)
            for url in urls:
                all_sources.append((url, platform))
        
        print(f"📡 共找到 {len(all_sources)} 个RSS源，开始逐一尝试...")
        print("-" * 60)
        
        # 逐一尝试所有RSS源，一旦成功就立即返回
        for i, (url, platform) in enumerate(all_sources, 1):
            print(f"\n[{i}/{len(all_sources)}] 🎯 平台: {platform.value.upper()}")
            
            feed, success = self.try_rss_source(url)
            if success:
                print(f"✅ 成功获取 {user.name} 的内容! (平台: {platform.value.upper()})")
                print(f"🎉 使用RSS源: {url}")
                return feed, platform
            
            print(f"❌ 此源不可用，继续尝试下一个...")
        
        print(f"😞 {user.name} 的所有RSS源都不可用")
        return None, None
    
    def display_content(self, feed: Any, user: SimpleUser, platform: Platform) -> None:
        """显示RSS内容"""
        if not feed:
            return
            
        print(f"\n🎉 {platform.value.upper()} - {user.name} 内容:")
        print("=" * 60)
        
        entries = getattr(feed, 'entries', [])
        for i, entry in enumerate(entries[:10], 1):
            try:
                formatted_content = ContentParser.format_entry(entry, i, platform)
                print(formatted_content)
                
                if i % 5 == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f"处理第 {i} 条内容时出错: {e}")
                continue

class SocialMediaMonitor:
    """社交媒体监控主类"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config = SocialMediaConfig(config_file)
        self.rss_manager = RSSManager(self.config)
    
    def monitor_all_users(self) -> None:
        """监控所有用户"""
        print("🚀 开始监控所有用户...")
        print("=" * 80)
        
        users = self.config.get_users()
        success_count = 0
        total_count = len(users)
        
        for user in users:
            feed, platform = self.rss_manager.fetch_user_content(user)
            if feed and platform:
                self.rss_manager.display_content(feed, user, platform)
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
        
        feed, platform = self.rss_manager.fetch_user_content(target_user)
        if feed and platform:
            self.rss_manager.display_content(feed, target_user, platform)
        else:
            print(f"😞 无法获取 {username} 的内容")
    
    def add_user(self, username: str, description: str) -> None:
        """动态添加用户 - 极简版本"""
        new_user = SimpleUser(username, description)
        print(f"📝 已添加用户: {description}")
        
        feed, platform = self.rss_manager.fetch_user_content(new_user)
        if feed and platform:
            self.rss_manager.display_content(feed, new_user, platform)
        else:
            print(f"⚠️ 无法获取 {description} 的内容，请检查用户名")

def main():
    """主函数"""
    try:
        monitor = SocialMediaMonitor()
        
        print("🌟 极简社交媒体RSS监控工具")
        print("=" * 50)
        print("✨ 只需配置用户名和描述，自动检测平台!")
        print("支持: Twitter、微博")
        print("=" * 50)
        
        # 监控所有用户
        monitor.monitor_all_users()
        
        # 示例：监控特定用户
        # monitor.monitor_specific_user("GitHub_Daily")
        
        # 示例：动态添加用户（只需用户名和描述）
        # monitor.add_user("elonmusk", "Elon Musk")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断监控")
    except Exception as e:
        print(f"❌ 程序执行出现错误: {e}")
        sys.exit(1)
    finally:
        gc.collect()
        print("\n🔚 监控结束")

if __name__ == "__main__":
    main()