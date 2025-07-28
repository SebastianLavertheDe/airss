"""
Notion 图片上传功能
"""

import os
import re
import requests
import mimetypes
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs


class NotionImageUploader:
    """Notion 图片上传器"""
    
    def __init__(self, notion_client):
        self.client = notion_client
    
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
    
    def upload_image_to_notion(self, image_url: str) -> Optional[str]:
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
    
    def convert_twitter_image_url(self, url: str) -> str:
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
    
    def extract_image_urls(self, text: str) -> List[str]:
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
                converted_url = self.convert_twitter_image_url(url)
                image_urls.append(converted_url)

        return image_urls
