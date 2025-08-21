"""
Notion 数据库管理器
"""

import os
import json
import re
import requests
import mimetypes
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from notion_client import Client
from urllib.parse import urlparse, parse_qs


class NotionManager:
    """Notion 数据库管理器"""
    
    def __init__(self, page_or_db_id: str = None, force_recreate: bool = False):
        """初始化 Notion 客户端"""
        # 从环境变量读取配置
        self.page_or_db_id = page_or_db_id or os.getenv("NOTION_PAGE_ID", "2393c1497bd5808f93a2c7ba9c2d4edd")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.force_recreate = force_recreate
        self.config_file = "notion_config.json"  # 保留用于备份
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
                # 首先尝试使用环境变量中的数据库ID
                if self.database_id:
                    try:
                        response = self.client.databases.retrieve(database_id=self.database_id)
                        print(f"✅ 找到环境变量配置的数据库: {response.get('title', [{}])[0].get('text', {}).get('content', 'AIRSS')}")
                        print(f"📋 数据库ID: {self.database_id}")
                        return
                    except Exception as e:
                        print(f"⚠️ 环境变量中的数据库ID无效 ({e})，尝试其他方法")

                # 尝试使用保存的数据库ID（备选方案）
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

                # 如果没有有效的数据库ID，尝试直接使用页面ID作为数据库ID
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
                },
                "AI总结": {
                    "rich_text": {}
                },
                "AI分类": {
                    "select": {
                        "options": [
                            {"name": "科技资讯", "color": "blue"},
                            {"name": "人工智能", "color": "purple"},
                            {"name": "开发工具", "color": "green"},
                            {"name": "编程技术", "color": "orange"},
                            {"name": "产品发布", "color": "red"},
                            {"name": "行业动态", "color": "yellow"},
                            {"name": "学习资源", "color": "pink"},
                            {"name": "开源项目", "color": "gray"},
                            {"name": "创业投资", "color": "brown"},
                            {"name": "社会热点", "color": "default"},
                            {"name": "生活娱乐", "color": "blue"},
                            {"name": "其他", "color": "gray"}
                        ]
                    }
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

    def _is_twitter_url(self, url: str) -> bool:
        """检查是否是有效的Twitter URL"""
        if not url:
            return False

        # 支持的Twitter域名
        twitter_domains = [
            'twitter.com',
            'x.com',
            'mobile.twitter.com',
            'm.twitter.com'
        ]

        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # 移除 www. 前缀
            if domain.startswith('www.'):
                domain = domain[4:]

            # 检查是否是Twitter域名且包含status路径
            is_twitter_domain = domain in twitter_domains
            has_status_path = '/status/' in parsed_url.path

            return is_twitter_domain and has_status_path

        except Exception:
            return False

    def _create_quote_block(self, quoted_tweet: dict) -> dict:
        """创建Notion引用块"""
        try:
            author = quoted_tweet.get('author', '引用内容')
            content = quoted_tweet.get('content', '')

            if not content:
                return None

            # 创建引用块
            quote_block = {
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"💬 {author}: {content}"
                            },
                            "annotations": {
                                "italic": True
                            }
                        }
                    ],
                    "color": "gray_background"
                }
            }

            return quote_block

        except Exception as e:
            print(f"⚠️ 创建引用块失败: {e}")
            return None

    def test_connection(self) -> bool:
        """测试 Notion 连接"""
        if not self.enabled:
            return False

        try:
            # 尝试获取数据库信息
            response = self.client.databases.retrieve(database_id=self.database_id)
            db_title = response.get('title', [{}])[0].get('text', {}).get('content', 'AIRSS')
            print(f"✅ Notion 连接测试成功，数据库: {db_title}")
            return True
        except Exception as e:
            print(f"❌ Notion 连接测试失败: {e}")
            self.enabled = False
            return False

    def push_entry_to_notion(self, entry: dict, user_name: str, platform: str, ai_analysis: dict = None) -> bool:
        """将RSS条目推送到Notion数据库"""
        if not self.enabled:
            return False

        try:
            from ..utils.text_utils import clean_text, build_paragraph_blocks, parse_published_time
            from ..notion.image_uploader import NotionImageUploader
            from ..parsers.twitter_parser import TwitterContentParser

            # 准备数据
            title = entry.get('title', '无标题')[:100]  # Notion标题限制
            url = entry.get('link', '')
            author = entry.get('author', user_name)[:100]
            published_time = parse_published_time(entry.get('published', ''))

            # 创建图片上传器和Twitter解析器
            image_uploader = NotionImageUploader(self.client)
            twitter_parser = TwitterContentParser()

            # 获取原始摘要
            raw_summary = entry.get('summary', '')

            # 如果是Twitter平台，解析引用内容
            quoted_tweets = []
            if platform.upper() == "TWITTER":
                main_content, quoted_tweets = twitter_parser.parse_twitter_content(raw_summary)
                summary = clean_text(main_content or '无摘要')
                print(f"🐦 检测到 {len(quoted_tweets)} 个引用推文")
            else:
                summary = clean_text(raw_summary or '无摘要')

            # 提取图片URL
            image_urls = image_uploader.extract_image_urls(raw_summary)

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
                "状态": {
                    "select": {
                        "name": "新增"
                    }
                },
                "摘要": {
                    "rich_text": [
                        {
                            "text": {
                                "content": summary[:1900]  # Notion rich_text 限制，留安全余量
                            }
                        }
                    ]
                }
            }

            # 添加AI分析结果到属性中
            if ai_analysis:
                properties["AI总结"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": ai_analysis.get('summary', '')[:1900]
                            }
                        }
                    ]
                }
                properties["AI分类"] = {
                    "select": {
                        "name": ai_analysis.get('category', '其他')
                    }
                }

            return self._create_page_with_content(properties, summary, image_urls, image_uploader, title, platform, url, quoted_tweets)

        except Exception as e:
            print(f"❌ Notion 推送失败: {e}")
            return False

    def _create_page_with_content(self, properties: dict, summary: str, image_urls: list, image_uploader, title: str, platform: str, original_url: str, quoted_tweets: list = None) -> bool:
        """创建包含内容的Notion页面"""
        try:
            from ..utils.text_utils import build_paragraph_blocks

            # 创建页面内容（摘要、引用、图片和Twitter嵌入）
            children = []

            # 添加摘要文本 - 使用分块功能处理长文本
            if summary:
                # 使用新的分块功能，自动将长文本拆分为多个段落
                summary_blocks = build_paragraph_blocks(summary)
                children.extend(summary_blocks)

                # 显示分块信息
                if len(summary_blocks) > 1:
                    print(f"📝 长文本已分为 {len(summary_blocks)} 个段落")
                else:
                    print(f"📝 文本长度: {len(summary)} 字符")

            # 添加引用推文块
            if quoted_tweets:
                for i, quoted_tweet in enumerate(quoted_tweets):
                    print(f"📝 添加引用推文 {i+1}: {quoted_tweet.get('author', '未知作者')}")

                    # 创建引用块
                    quote_block = self._create_quote_block(quoted_tweet)
                    if quote_block:
                        children.append(quote_block)

                        # 添加小的间距
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": []
                            }
                        })

            # 如果是Twitter平台，添加嵌入的原始帖子链接
            if platform.upper() == "TWITTER" and original_url and self._is_twitter_url(original_url):
                print(f"🐦 添加Twitter嵌入链接: {original_url}")
                children.append({
                    "object": "block",
                    "type": "embed",
                    "embed": {
                        "url": original_url
                    }
                })

                # 添加分隔线
                children.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })

            # 添加图片块 - 使用文件上传方式
            if image_urls:
                for img_url in image_urls[:5]:  # 最多添加5张图片
                    try:
                        print(f"📷 处理图片: {img_url}")

                        # 尝试上传图片到Notion
                        file_upload_id = image_uploader.upload_image_to_notion(img_url)

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
                                                "content": "🖼️ 图片: "
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
            print(f"❌ 页面创建失败: {e}")
            return False
