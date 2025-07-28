"""
内容解析器
"""

from typing import Any


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
