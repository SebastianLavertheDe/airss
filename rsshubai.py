import feedparser
import time
import gc
import sys
import yaml
import os
import json
import hashlib
import re
import requests
import mimetypes
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from notion_client import Client
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

# 加载 .env 环境变量
load_dotenv()

@dataclass
class SimpleUser:
    """极简用户配置"""
    id: str  # 用于RSS URL填充
    name: str  # 用于显示的用户名
    platform: str  # 用户所属平台

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
                    users.append(SimpleUser(user_id, user_name, platform_name))
        
        return users
    
    def get_platforms(self) -> List[str]:
        """获取所有支持的平台"""
        return list(self.config.get('platforms', {}).keys())
    
    def get_rss_templates_for_platform(self, platform: str) -> List[str]:
        """获取指定平台的RSS模板"""
        platforms = self.config.get('platforms', {})
        platform_config = platforms.get(platform, {})
        return platform_config.get('rss_url', [])
    
    def generate_urls_for_user(self, user: SimpleUser) -> List[str]:
        """为用户生成RSS URLs（用户平台固定）"""
        urls = []
        templates = self.get_rss_templates_for_platform(user.platform)
        
        # 使用用户ID生成URLs
        for template in templates:
            url = template.format(username=user.id)
            urls.append(url)
        
        return urls

class ContentParser:
    """内容解析器"""
    
    @staticmethod
    def safe_str(value: Any, max_length: int = 20000, truncate: bool = True) -> str:
        """安全地转换为字符串并可选择限制长度"""
        try:
            if value is None:
                return "无内容"
            
            str_value = str(value)
            if truncate and len(str_value) > max_length:
                return str_value[:max_length] + "......"
            return str_value
        except Exception as e:
            return f"内容解析错误: {e}"
    
    @staticmethod
    def format_entry(entry: dict, index: int, platform: str) -> str:
        """格式化单个条目"""
        try:
            content_type = {
                "twitter": "推文",
                "weibo": "微博"
            }.get(platform, "内容")
            
            formatted = f"第 {index} 篇{content_type}:\n"
            formatted += f"标题: {entry.get('title', '无标题')}\n"
            formatted += f"链接: {ContentParser.safe_str(entry.get('link', '无链接'))}\n"
            formatted += f"作者: {ContentParser.safe_str(entry.get('author', '无作者'))}\n"
            formatted += f"发布时间: {ContentParser.safe_str(entry.get('published', '无时间'))}\n"
            formatted += f"摘要: {ContentParser.safe_str(entry.get('summary', '无摘要'))}\n"
            formatted += "-" * 50
            return formatted
        except Exception as e:
            return f"格式化第 {index} 条内容时出错: {e}\n" + "-" * 50

class NotionManager:
    """Notion 数据库管理器"""
    
    def __init__(self, page_or_db_id: str = "2393c1497bd5808f93a2c7ba9c2d4edd", force_recreate: bool = False):
        """初始化 Notion 客户端"""
        self.page_or_db_id = page_or_db_id
        self.database_id = None
        self.force_recreate = force_recreate
        self.config_file = "notion_config.json"
        notion_key = os.getenv("notion_key")
        
        if not notion_key:
            print("❌ 未找到 notion_key 环境变量，Notion 推送功能将被禁用")
            self.client = None
            self.enabled = False
        else:
            try:
                self.client = Client(auth=notion_key)
                self.enabled = True
                print("✅ Notion 客户端初始化成功")
                
                # 检查并设置数据库
                self._setup_database()
                
            except Exception as e:
                print(f"❌ Notion 客户端初始化失败: {e}")
                self.client = None
                self.enabled = False
    
    def _load_notion_config(self) -> Dict[str, Any]:
        """加载 Notion 配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config = json.load(file)
                    print(f"✅ 成功加载 Notion 配置文件: {self.config_file}")
                    return config
            else:
                print(f"📁 Notion 配置文件不存在，将创建新的配置: {self.config_file}")
                return {}
        except Exception as e:
            print(f"⚠️ 加载 Notion 配置文件失败: {e}，将使用空配置")
            return {}
    
    def _save_notion_config(self, config: Dict[str, Any]) -> None:
        """保存 Notion 配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as file:
                json.dump(config, file, ensure_ascii=False, indent=2)
            print(f"💾 已保存 Notion 配置到: {self.config_file}")
        except Exception as e:
            print(f"❌ 保存 Notion 配置文件失败: {e}")
    
    def _get_saved_database_id(self) -> Optional[str]:
        """获取保存的数据库ID"""
        config = self._load_notion_config()
        return config.get("database_id")
    
    def _save_database_id(self, database_id: str) -> None:
        """保存数据库ID到配置文件"""
        config = self._load_notion_config()
        config["database_id"] = database_id
        config["page_id"] = self.page_or_db_id
        config["created_time"] = datetime.now(timezone.utc).isoformat()
        self._save_notion_config(config)
    
    def _setup_database(self):
        """检查并设置数据库"""
        try:
            # 如果强制重新创建，直接跳到创建步骤
            if not self.force_recreate:
                # 首先尝试使用保存的数据库ID
                saved_db_id = self._get_saved_database_id()
                if saved_db_id:
                    try:
                        response = self.client.databases.retrieve(database_id=saved_db_id)
                        self.database_id = saved_db_id
                        print(f"✅ 找到已保存的数据库: {response.get('title', [{}])[0].get('text', {}).get('content', 'AIRSS')}")
                        print(f"📋 数据库ID: {saved_db_id}")
                        return
                    except Exception as e:
                        print(f"⚠️ 保存的数据库ID无效 ({e})，将重新创建数据库")
                
                # 如果没有保存的ID，尝试直接使用页面ID作为数据库ID
                try:
                    response = self.client.databases.retrieve(database_id=self.page_or_db_id)
                    self.database_id = self.page_or_db_id
                    print(f"✅ 找到现有数据库: {response.get('title', [{}])[0].get('text', {}).get('content', 'AIRSS')}")
                    # 保存这个有效的数据库ID
                    self._save_database_id(self.database_id)
                    return
                except Exception:
                    pass
            
            # 尝试作为页面ID，并在其中创建新数据库
            try:
                page_response = self.client.pages.retrieve(page_id=self.page_or_db_id)
                if self.force_recreate:
                    print(f"✅ 找到页面，正在重新创建包含摘要字段的 AIRSS 数据库...")
                else:
                    print(f"✅ 找到页面，正在创建 AIRSS 数据库...")
                self._create_database_in_page(self.page_or_db_id)
            except Exception as e:
                print(f"❌ 无法访问指定的页面或数据库: {e}")
                self.enabled = False
                
        except Exception as e:
            print(f"❌ 数据库设置失败: {e}")
            self.enabled = False
    
    def _create_database_in_page(self, page_id: str):
        """在页面中创建 AIRSS 数据库"""
        try:
            # 定义数据库结构
            properties = {
                "标题": {
                    "title": {}
                },
                "链接": {
                    "url": {}
                },
                "作者": {
                    "rich_text": {}
                },
                "发布时间": {
                    "date": {}
                },
                "平台": {
                    "select": {
                        "options": [
                            {"name": "TWITTER", "color": "blue"},
                            {"name": "WEIBO", "color": "red"},
                            {"name": "X", "color": "default"}
                        ]
                    }
                },
                "用户": {
                    "rich_text": {}
                },
                                 "状态": {
                     "select": {
                         "options": [
                             {"name": "新增", "color": "green"},
                             {"name": "已读", "color": "gray"}
                         ]
                     }
                 },
                 "摘要": {
                     "rich_text": {}
                 }
            }
            
            # 创建数据库
            response = self.client.databases.create(
                parent={
                    "type": "page_id",
                    "page_id": page_id
                },
                title=[
                    {
                        "type": "text",
                        "text": {
                            "content": "AIRSS - RSS 订阅内容"
                        }
                    }
                ],
                properties=properties
            )
            
            self.database_id = response["id"]
            print(f"✅ 成功创建 AIRSS 数据库，ID: {self.database_id}")
            
            # 保存数据库ID到配置文件
            self._save_database_id(self.database_id)
            
        except Exception as e:
            print(f"❌ 创建数据库失败: {e}")
            self.enabled = False
    
    def _parse_published_time(self, published_str: str) -> str:
        """解析发布时间并格式化为 ISO 格式"""
        try:
            if not published_str or published_str == "无时间":
                return datetime.now(timezone.utc).isoformat()

            # 尝试解析常见的时间格式
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(published_str)
            return dt.isoformat()
        except Exception as e:
            print(f"⚠️ 时间解析失败: {e}, 使用当前时间")
            return datetime.now(timezone.utc).isoformat()

    def _download_image_from_url(self, url: str, save_dir: str = "./downloads") -> str:
        """下载远程图片并保存到本地"""
        try:
            os.makedirs(save_dir, exist_ok=True)

            # 获取基本文件名
            path_part = urlparse(url).path
            filename_base = os.path.basename(path_part) or "image"

            # 获取扩展名
            query = parse_qs(urlparse(url).query)
            ext = query.get("format", ["jpg"])[0] if query.get("format") else "jpg"

            # 如果文件名已经有扩展名，就不重复添加
            if not filename_base.endswith(f".{ext}"):
                filename = f"{filename_base}.{ext}"
            else:
                filename = filename_base

            filepath = os.path.join(save_dir, filename)

            # 下载图片
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            print(f"📥 图片下载成功: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ 图片下载失败: {url}\n错误: {e}")
            raise

    def _create_upload_object(self) -> dict:
        """创建Notion文件上传对象"""
        notion_key = os.getenv("notion_key")
        resp = requests.post(
            "https://api.notion.com/v1/file_uploads",
            headers={
                "Authorization": f"Bearer {notion_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={}  # 空JSON
        )
        resp.raise_for_status()
        return resp.json()

    def _send_upload_content(self, upload_id: str, filepath: str) -> dict:
        """发送文件内容到Notion"""
        notion_key = os.getenv("notion_key")
        mime = mimetypes.guess_type(filepath)[0] or "image/png"

        with open(filepath, "rb") as f:
            r = requests.post(
                f"https://api.notion.com/v1/file_uploads/{upload_id}/send",
                headers={
                    "Authorization": f"Bearer {notion_key}",
                    "Notion-Version": "2022-06-28"
                },
                files={"file": (os.path.basename(filepath), f, mime)}
            )
        r.raise_for_status()
        return r.json()

    def _upload_image_to_notion(self, image_url: str) -> Optional[str]:
        """将图片上传到Notion并返回file_upload_id"""
        try:
            print(f"🔄 开始上传图片到Notion: {image_url}")

            # 1. 下载图片到本地
            local_path = self._download_image_from_url(image_url)

            # 2. 创建上传对象
            upload_obj = self._create_upload_object()
            upload_id = upload_obj["id"]
            print(f"📤 创建上传对象成功: {upload_id}")

            # 3. 发送文件内容
            self._send_upload_content(upload_id, local_path)
            print(f"✅ 图片上传成功: {upload_id}")

            # 4. 清理本地文件
            try:
                os.remove(local_path)
                print(f"🗑️ 已清理本地文件: {local_path}")
            except:
                pass

            return upload_id

        except Exception as e:
            print(f"❌ 图片上传失败: {e}")
            return None
    
    def _convert_twitter_image_url(self, url: str) -> str:
        """将Twitter图片URL转换为代理URL，避免Notion访问被拒绝"""
        try:
            # 解码HTML实体
            import html
            from urllib.parse import quote_plus

            decoded_url = html.unescape(url).strip()

            # 检查是否是Twitter图片
            if 'pbs.twimg.com' in decoded_url or 'twimg.com' in decoded_url:
                # 移除https://前缀，因为代理服务不需要
                clean_url = decoded_url.replace('https://', '').replace('http://', '')

                # 使用images.weserv.nl代理服务
                proxy_url = f'https://images.weserv.nl/?url={quote_plus(clean_url)}'

                print(f"🔄 Twitter图片代理转换:")
                print(f"   原始URL: {decoded_url}")
                print(f"   代理URL: {proxy_url}")

                return proxy_url

            # 非Twitter图片直接返回
            return decoded_url

        except Exception as e:
            print(f"⚠️ 图片URL转换失败: {e}")
            return url

    def _extract_image_urls(self, text: str) -> List[str]:
        """从HTML内容中提取图片URL"""
        if not text:
            return []

        # 匹配 <img> 标签中的 src 属性
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, text, re.IGNORECASE)
 
        # 过滤出有效的图片URL，解码HTML实体，并转换Twitter图片为代理URL
        image_urls = []
        for url in matches:
            # 确保是完整的URL
            if url.startswith('http'):
                # 转换Twitter图片URL为代理URL
                converted_url = self._convert_twitter_image_url(url)
                image_urls.append(converted_url)

        return image_urls

    def _clean_text(self, text: str) -> str:
        """清理文本内容，移除HTML标签"""
        if not text or text == "无内容":
            return ""

        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', str(text))
        # 移除多余的空白字符
        clean_text = ' '.join(clean_text.split())

        return clean_text

    def _split_text_to_blocks(self, text: str, max_length: int = 1900) -> List[str]:
        """将长文本按指定长度分段"""
        if not text:
            return []

        # 如果文本长度在限制内，直接返回
        if len(text) <= max_length:
            return [text]

        # 按 max_length 字符分段
        segments = []
        for i in range(0, len(text), max_length):
            segment = text[i:i + max_length]
            segments.append(segment)

        return segments

    def _build_paragraph_blocks(self, text: str) -> List[Dict[str, Any]]:
        """将文本构建为多个段落块"""
        blocks = []
        segments = self._split_text_to_blocks(text)

        for segment in segments:
            if segment.strip():  # 只添加非空段落
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": segment}
                        }]
                    }
                })

        return blocks
    
    def push_entry_to_notion(self, entry: dict, user_name: str, platform: str) -> bool:
        """将RSS条目推送到Notion数据库"""
        if not self.enabled:
            return False

        try:
            # 准备数据
            title = entry.get('title', '无标题')[:100]  # Notion标题限制
            url = entry.get('link', '')
            author = entry.get('author', user_name)[:100]
            published_time = self._parse_published_time(entry.get('published', ''))
            summary = self._clean_text(entry.get('summary', '无摘要'))

            # 提取图片URL
            raw_summary = entry.get('summary', '')
            image_urls = self._extract_image_urls(raw_summary)

            # 构建 Notion 页面属性
            properties = {
                "标题": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "链接": {
                    "url": url if url else None
                },
                "作者": {
                    "rich_text": [
                        {
                            "text": {
                                "content": author
                            }
                        }
                    ]
                },
                "发布时间": {
                    "date": {
                        "start": published_time
                    }
                },
                "平台": {
                    "select": {
                        "name": platform.upper()
                    }
                },
                                 "用户": {
                     "rich_text": [
                         {
                             "text": {
                                 "content": user_name
                             }
                         }
                     ]
                 },
                 "状态": {
                     "select": {
                         "name": "新增"
                     }
                 },
                 "摘要": {
                     "rich_text": [
                         {
                             "text": {
                                 "content": summary[:2000]  # Notion rich_text 限制
                             }
                         }
                     ]
                 }
            }
            
            # 创建页面内容（摘要和图片）
            children = []

            # 添加摘要文本 - 使用分块功能处理长文本
            if summary:
                # 使用新的分块功能，自动将长文本拆分为多个段落
                summary_blocks = self._build_paragraph_blocks(summary)
                children.extend(summary_blocks)

                # 显示分块信息
                if len(summary_blocks) > 1:
                    print(f"📝 长文本已分为 {len(summary_blocks)} 个段落")
                else:
                    print(f"📝 文本长度: {len(summary)} 字符")

            # 添加图片块 - 使用文件上传方式
            if image_urls:
                for img_url in image_urls[:5]:  # 最多添加5张图片
                    try:
                        print(f"📷 处理图片: {img_url}")

                        # 尝试上传图片到Notion
                        file_upload_id = self._upload_image_to_notion(img_url)

                        if file_upload_id:
                            # 使用file_upload方式
                            children.append({
                                "object": "block",
                                "type": "image",
                                "image": {
                                    "type": "file_upload",
                                    "file_upload": {
                                        "id": file_upload_id
                                    }
                                }
                            })
                            print(f"✅ 图片上传成功: {file_upload_id}")
                        else:
                            # 上传失败，改为文本链接
                            print(f"⚠️ 图片上传失败，改为文本链接")
                            children.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": "�️ 图片: "
                                            }
                                        },
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": img_url,
                                                "link": {
                                                    "url": img_url
                                                }
                                            }
                                        }
                                    ]
                                }
                            })

                    except Exception as img_error:
                        print(f"⚠️ 图片处理失败: {img_error}")
                        # 添加错误信息作为文本
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {
                                        "content": f"❌ 图片处理失败: {img_url}"
                                    }
                                }]
                            }
                        })
                        continue

            # 推送到 Notion
            # 打印推送信息
            print(f"正在推送至 Notion: children: {children}")
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )

            # 显示推送结果
            image_count = len(image_urls) if image_urls else 0
            if image_count > 0:
                print(f"✅ 已推送到 Notion: {title[:50]}... (包含 {min(image_count, 5)} 张图片)")
            else:
                print(f"✅ 已推送到 Notion: {title[:50]}...")
            return True

        except Exception as e:
            print(f"❌ Notion 推送失败: {e}")
            return False
    
    def test_connection(self) -> bool:
        """测试 Notion 连接"""
        if not self.enabled or not self.database_id:
            return False
            
        try:
            # 尝试获取数据库信息
            response = self.client.databases.retrieve(database_id=self.database_id)
            print(f"✅ Notion 连接测试成功，数据库名称: {response.get('title', [{}])[0].get('text', {}).get('content', 'AIRSS')}")
            return True
        except Exception as e:
            print(f"❌ Notion 连接测试失败: {e}")
            return False

class RSSManager:
    """RSS源管理器"""
    
    def __init__(self, config: SocialMediaConfig):
        """初始化RSS管理器"""
        self.config = config
        self.cache_manager = CacheManager()
        self.notion_manager = NotionManager()
        
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
        print(f"\n🔍 正在尝试获取 {user.name}")
        print(f"📝 用户ID: {user.id}")
        print(f"🎯 平台: {user.platform.upper()}")
        print("=" * 60)
        
        # 获取该用户固定平台的所有RSS源
        urls = self.config.generate_urls_for_user(user)
        
        print(f"📡 共找到 {len(urls)} 个RSS源，开始逐一尝试...")
        print("-" * 60)
        
        # 逐一尝试该平台的所有RSS源，一旦成功就立即返回
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 🎯 平台: {user.platform.upper()}")
            
            feed, success = self.try_rss_source(url)
            if success:
                print(f"✅ 成功获取 {user.name} 的内容! (平台: {user.platform.upper()})")
                print(f"🎉 使用RSS源: {url}")
                return feed, user.platform
            
            print(f"❌ 此源不可用，继续尝试下一个...")
        
        print(f"😞 {user.name} 在 {user.platform.upper()} 平台的所有RSS源都不可用")
        return None, None
    
    def display_content(self, feed: Any, user: SimpleUser, platform: str) -> None:
        """显示RSS内容（仅显示未缓存的新内容）"""
        if not feed:
            return
            
        print(f"\n🎉 {platform.upper()} - {user.name} 内容:")
        print("=" * 60)
        
        entries = getattr(feed, 'entries', [])
        new_entries = []
        cached_entries_count = 0
        
        # 首先过滤出未缓存的条目
        for entry in entries:
            if not self.cache_manager.is_entry_cached(entry):
                new_entries.append(entry)
            else:
                cached_entries_count += 1
        
        print(f"📊 总条目数: {len(entries)}, 新条目: {len(new_entries)}, 已缓存: {cached_entries_count}")
        
        if not new_entries:
            print("✨ 所有内容都已在缓存中，没有新内容需要显示")
            return
        
        print(f"🆕 显示 {len(new_entries)} 个新条目:")
        print("-" * 60)
        
        # 显示新条目并添加到缓存
        notion_success_count = 0
        for i, entry in enumerate(new_entries[:10], 1):  # 最多显示10个新条目
            try:
                formatted_content = ContentParser.format_entry(entry, i, platform)
                print("formatted_content-----:", formatted_content)
                
                # 推送到 Notion 数据库
                if self.notion_manager.enabled:
                    notion_success = self.notion_manager.push_entry_to_notion(
                        entry, user.name, platform
                    )
                    if notion_success:
                        notion_success_count += 1
                
                # 将新条目添加到缓存
                self.cache_manager.add_entry_to_cache(entry)
                
                if i % 5 == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f"处理第 {i} 条内容时出错: {e}")
                continue
        
        # 保存缓存
        self.cache_manager.save()
        print(f"💾 已将 {len(new_entries[:10])} 个新条目添加到缓存")
        
        # 显示 Notion 推送统计
        if self.notion_manager.enabled:
            print(f"📤 Notion 推送统计: {notion_success_count}/{len(new_entries[:10])} 成功")
        else:
            print("⚠️ Notion 推送功能未启用")

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
        
        feed, result_platform = self.rss_manager.fetch_user_content(new_user)
        if feed and result_platform:
            self.rss_manager.display_content(feed, new_user, result_platform)
        else:
            print(f"⚠️ 无法获取 {description} 的内容，请检查用户名")

def main():
    """主函数"""
    try:
        monitor = SocialMediaMonitor()
        
        print("🌟 智能社交媒体RSS监控工具")
        print("=" * 50)
        print("✨ 动态平台配置，用户平台固定!")
        
        # 显示支持的平台
        platforms = monitor.config.get_platforms()
        print(f"🎯 支持平台: {', '.join(p.upper() for p in platforms)}")
        print("=" * 50)
        
        # 测试：只监控特定用户
        monitor.monitor_specific_user("dotey")
        
        # 监控所有用户
        # monitor.monitor_all_users()
        
        # 示例：监控特定用户
        # monitor.monitor_specific_user("GitHub_Daily")
        
        # 示例：动态添加用户（需要指定平台）
        # monitor.add_user("elonmusk", "Elon Musk", "twitter")
        # monitor.add_user("5722964389", "某微博用户", "weibo")
        
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