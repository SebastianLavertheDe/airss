"""
Twitter内容解析器 - 专门处理Twitter特有的内容结构
"""

import re
from typing import Dict, List, Optional, Tuple


class TwitterContentParser:
    """Twitter内容解析器"""
    
    def __init__(self):
        self.quote_patterns = [
            # RSShub的引用格式
            r'<div class="rsshub-quote">(.*?)</div>',
            # 其他可能的引用格式
            r'<blockquote[^>]*>(.*?)</blockquote>',
            # 简单的引用标记
            r'(?:^|\n)>\s*(.*?)(?=\n|$)',
        ]
    
    def extract_quoted_content(self, html_content: str) -> List[Dict[str, str]]:
        """从HTML内容中提取引用的推文"""
        if not html_content:
            return []

        # 直接使用正则表达式解析
        quoted_tweets = self._extract_with_regex(html_content)

        return quoted_tweets
    

    
    def _extract_with_regex(self, html_content: str) -> List[Dict[str, str]]:
        """使用正则表达式提取引用内容"""
        quoted_tweets = []
        
        for pattern in self.quote_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # 清理HTML标签
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                
                if clean_text:
                    author = self._extract_author_from_text(clean_text)
                    clean_content = self._clean_quoted_text(clean_text)
                    
                    quoted_tweets.append({
                        'type': 'quoted_tweet',
                        'author': author,
                        'content': clean_content,
                        'source': 'regex'
                    })
        
        return quoted_tweets
    
    def _extract_author_from_text(self, text: str) -> str:
        """从文本中提取作者信息"""
        # 常见的作者格式模式
        author_patterns = [
            r'^([^:：]+)[:：]\s*',  # "作者: 内容" 格式
            r'^@(\w+)',              # "@username" 格式
            r'^(\w+)\s*说',          # "某人说" 格式
            r'^(\w+)\s*：',          # "某人：" 格式
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, text.strip())
            if match:
                return match.group(1).strip()
        
        # 如果没有找到明确的作者，尝试提取第一行作为作者
        lines = text.strip().split('\n')
        if len(lines) > 1 and len(lines[0]) < 50:  # 第一行较短，可能是作者
            return lines[0].strip()
        
        return "引用内容"
    
    def _clean_quoted_text(self, text: str) -> str:
        """清理引用文本"""
        # 移除作者前缀
        author_patterns = [
            r'^[^:：]+[:：]\s*',
            r'^@\w+\s*',
            r'^\w+\s*说\s*',
            r'^\w+\s*：\s*',
        ]
        
        cleaned = text.strip()
        for pattern in author_patterns:
            cleaned = re.sub(pattern, '', cleaned, count=1)
        
        # 移除多余的空白
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def remove_quoted_content_from_main(self, html_content: str) -> str:
        """从主要内容中移除引用部分"""
        if not html_content:
            return html_content

        # 使用正则表达式移除引用内容
        cleaned = html_content
        for pattern in self.quote_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        return cleaned
    
    def parse_twitter_content(self, html_content: str) -> Tuple[str, List[Dict[str, str]]]:
        """解析Twitter内容，返回主要内容和引用内容"""
        # 提取引用内容
        quoted_tweets = self.extract_quoted_content(html_content)
        
        # 从主要内容中移除引用部分
        main_content = self.remove_quoted_content_from_main(html_content)
        
        return main_content, quoted_tweets
