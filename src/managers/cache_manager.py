"""
缓存管理器
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Tuple


class CacheManager:
    """本地文件缓存管理器"""
    
    def __init__(self, cache_file: str = "feed_cache.json"):
        """初始化缓存管理器"""
        self.cache_file = cache_file
        self.cache_data = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """加载缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as file:
                    cache_data = json.load(file)
                    print(f"✅ 成功加载缓存文件: {self.cache_file}")
                    return cache_data
            else:
                print(f"📁 缓存文件不存在，将创建新的缓存: {self.cache_file}")
                return {}
        except Exception as e:
            print(f"⚠️ 加载缓存文件失败: {e}，将使用空缓存")
            return {}
    
    def _save_cache(self) -> None:
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as file:
                json.dump(self.cache_data, file, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存缓存文件失败: {e}")
    
    def _generate_entry_id(self, entry: dict) -> str:
        """为feed条目生成唯一标识符"""
        # 优先使用entry的id，其次使用link，最后使用title和published的组合
        if entry.get('id'):
            unique_str = entry['id']
        elif entry.get('link'):
            unique_str = entry['link']
        else:
            # 使用title和published时间的组合
            title = entry.get('title', '')
            published = entry.get('published', '')
            unique_str = f"{title}_{published}"
        
        # 生成MD5哈希作为唯一标识符
        return hashlib.md5(unique_str.encode('utf-8')).hexdigest()
    
    def is_entry_cached(self, entry: dict) -> bool:
        """检查条目是否已被缓存"""
        entry_id = self._generate_entry_id(entry)
        return entry_id in self.cache_data
    
    def add_entry_to_cache(self, entry: dict) -> None:
        """将条目添加到缓存"""
        entry_id = self._generate_entry_id(entry)
        self.cache_data[entry_id] = {
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'author': entry.get('author', ''),
            'published': entry.get('published', ''),
            'cached_time': time.time()
        }
    
    def get_cache_stats(self) -> Tuple[int, int]:
        """获取缓存统计信息"""
        total_cached = len(self.cache_data)
        # 清理超过30天的旧缓存
        current_time = time.time()
        old_entries = [
            entry_id for entry_id, entry_data in self.cache_data.items()
            if current_time - entry_data.get('cached_time', 0) > 30 * 24 * 3600
        ]
        for entry_id in old_entries:
            del self.cache_data[entry_id]
        
        if old_entries:
            print(f"🧹 已清理 {len(old_entries)} 个超过30天的旧缓存条目")
            self._save_cache()
        
        return total_cached - len(old_entries), len(old_entries)
    
    def save(self) -> None:
        """保存缓存"""
        self._save_cache()
