"""
RSS源管理器
"""

import gc
import feedparser
from typing import Any, Optional, Tuple, List

from ..core.models import SimpleUser
from ..managers.cache_manager import CacheManager
from ..managers.config_manager import SocialMediaConfig
from ..notion.notion_manager import NotionManager
from ..parsers.content_parser import ContentParser
from ..ai.deepseek_client import DeepSeekClient


class RSSManager:
    """RSS源管理器"""
    
    def __init__(self, config: SocialMediaConfig):
        """初始化RSS管理器"""
        self.config = config
        self.cache_manager = CacheManager()
        self.notion_manager = NotionManager()
        
        # 初始化AI客户端
        try:
            self.ai_client = DeepSeekClient()
            print("🤖 DeepSeek AI 客户端初始化成功")
        except Exception as e:
            print(f"⚠️ DeepSeek AI 客户端初始化失败: {e}")
            self.ai_client = None
        
        # 显示缓存统计信息
        cached_count, cleaned_count = self.cache_manager.get_cache_stats()
        print(f"📦 缓存状态: 已缓存 {cached_count} 个条目")
        if cleaned_count > 0:
            print(f"🧹 已清理 {cleaned_count} 个过期条目")
        
        # 测试 Notion 连接
        if self.notion_manager.enabled:
            self.notion_manager.test_connection()
    
    def try_rss_source(self, url: str) -> Tuple[Optional[Any], bool]:
        """尝试获取指定 RSS 源"""
        print(f"正在尝试 RSS 源: {url}")
        
        try:
            # 设置更长的超时时间（60秒）
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(60.0)
            
            feed = feedparser.parse(url)
            
            # 恢复原始超时设置
            socket.setdefaulttimeout(original_timeout)
            
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
    
    def fetch_user_content(self, user: SimpleUser) -> Tuple[Optional[Any], Optional[str]]:
        """获取用户内容，用户平台固定"""
        print(f"🔍 正在尝试获取 {user.name}")
        print(f"📝 用户ID: {user.id}")
        print(f"🎯 平台: {user.platform.upper()}")
        print("=" * 60)
        
        # 获取用户的RSS URLs
        urls = self.config.generate_urls_for_user(user)
        
        if not urls:
            print(f"❌ 没有为用户 {user.name} 找到RSS源配置")
            return None, None
        
        print(f"📡 共找到 {len(urls)} 个RSS源，开始逐一尝试...")
        print("-" * 60)
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 🎯 平台: {user.platform.upper()}")
            
            feed, success = self.try_rss_source(url)
            
            if success and feed:
                print(f"✅ 成功获取 {user.name} 的内容! (平台: {user.platform.upper()})")
                print(f"🎉 使用RSS源: {url}")
                return feed, url
            else:
                print(f"❌ RSS源 {i} 获取失败")
        
        print(f"❌ 所有RSS源都无法获取 {user.name} 的内容")
        return None, None
    
    def process_user_content(self, user: SimpleUser, feed: Any, source_url: str) -> None:
        """处理用户内容"""
        if not feed or not hasattr(feed, 'entries'):
            print(f"❌ {user.name} 的feed数据无效")
            return
        
        entries = feed.entries
        total_entries = len(entries)
        
        if total_entries == 0:
            print(f"📭 {user.name} 暂无新内容")
            return
        
        # 过滤新条目
        new_entries = []
        for entry in entries:
            if not self.cache_manager.is_entry_cached(entry):
                new_entries.append(entry)
        
        new_count = len(new_entries)
        cached_count = total_entries - new_count
        
        print(f"\n🎉 {user.platform.upper()} - {user.name} 内容:")
        print("=" * 60)
        print(f"📊 总条目数: {total_entries}, 新条目: {new_count}, 已缓存: {cached_count}")
        
        if new_count == 0:
            print("📭 没有新内容需要处理")
            return
        
        print(f"🆕 显示 {new_count} 个新条目:")
        print("-" * 60)
        
        # 处理新条目
        notion_success_count = 0
        ai_success_count = 0
        for i, entry in enumerate(new_entries, 1):
            # 格式化并显示内容
            formatted_content = ContentParser.format_entry(entry, i, user.platform)
            print(f"formatted_content-----: {formatted_content}")
            
            # AI 分析处理
            ai_analysis = None
            if self.ai_client:
                try:
                    print(f"🤖 正在对条目 {i} 进行AI分析...")
                    
                    # 提取文本内容用于AI分析
                    title = getattr(entry, 'title', '')
                    content = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                    
                    # 清理HTML标签（简单处理）
                    import re
                    content = re.sub(r'<[^>]+>', '', content)
                    
                    if title or content:
                        ai_analysis = self.ai_client.analyze_content(title, content)
                        if ai_analysis:
                            print(f"   📝 总结: {ai_analysis['summary'][:100]}...")
                            print(f"   🏷️  分类: {ai_analysis['category']} (置信度: {ai_analysis['confidence']:.2f})")
                            ai_success_count += 1
                        else:
                            print(f"   ❌ AI分析失败")
                    else:
                        print(f"   ⚠️ 内容为空，跳过AI分析")
                        
                except Exception as e:
                    print(f"   ❌ AI分析出错: {e}")
            
            # 推送到 Notion (包含AI分析结果)
            if self.notion_manager.enabled:
                success = self.notion_manager.push_entry_to_notion(
                    entry, user.name, user.platform.upper(), ai_analysis
                )
                if success:
                    notion_success_count += 1
            
            # 添加到缓存
            self.cache_manager.add_entry_to_cache(entry)
        
        # 保存缓存
        self.cache_manager.save()
        print(f"💾 已将 {new_count} 个新条目添加到缓存")
        
        # 显示处理统计
        print(f"\n📊 处理统计:")
        if self.ai_client:
            print(f"🤖 AI分析统计: {ai_success_count}/{new_count} 成功")
        else:
            print("⚠️ AI分析功能未启用")
            
        if self.notion_manager.enabled:
            print(f"📤 Notion推送统计: {notion_success_count}/{new_count} 成功")
        else:
            print("⚠️ Notion推送功能未启用")
