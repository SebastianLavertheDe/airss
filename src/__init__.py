"""
RSS Hub AI - 智能社交媒体RSS监控工具
"""

from .core.models import SimpleUser
from .core.monitor import SocialMediaMonitor
from .managers.cache_manager import CacheManager
from .managers.config_manager import SocialMediaConfig
from .managers.rss_manager import RSSManager
from .notion.notion_manager import NotionManager
from .notion.image_uploader import NotionImageUploader
from .parsers.content_parser import ContentParser
from .utils.text_utils import clean_text, split_text_to_blocks, build_paragraph_blocks

__version__ = "1.0.0"
__author__ = "RSS Hub AI Team"

__all__ = [
    "SimpleUser",
    "SocialMediaMonitor", 
    "CacheManager",
    "SocialMediaConfig",
    "RSSManager",
    "NotionManager",
    "NotionImageUploader",
    "ContentParser",
    "clean_text",
    "split_text_to_blocks", 
    "build_paragraph_blocks"
]
