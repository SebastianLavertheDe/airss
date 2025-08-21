"""
DeepSeek AI 客户端
负责与DeepSeek API进行交互，实现文本总结和分类功能
"""

import os
import json
import time
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class DeepSeekClient:
    """DeepSeek AI 客户端"""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.model = os.getenv('AI_MODEL', 'deepseek-chat')
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未在环境变量中设置")
        
        # 初始化OpenAI客户端，指向DeepSeek API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
    
    def _make_request(self, messages: List[Dict], max_tokens: int = 1000) -> Optional[str]:
        """
        发起API请求
        
        Args:
            messages: 对话消息列表
            max_tokens: 最大token数
            
        Returns:
            API响应内容，失败时返回None
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,  # 降低随机性，提高一致性
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ DeepSeek API 请求失败: {e}")
            return None
    
    def summarize_text(self, text: str, max_length: int = 200) -> Optional[str]:
        """
        文本总结
        
        Args:
            text: 要总结的文本
            max_length: 总结最大长度
            
        Returns:
            总结文本，失败时返回None
        """
        if not text or len(text.strip()) < 10:
            return "内容过短，无需总结"
        
        messages = [
            {
                "role": "system",
                "content": f"""你是一个专业的文本总结专家。请对用户提供的文本进行精准、简洁的总结。

要求：
1. 总结长度控制在{max_length}字以内
2. 保留关键信息和核心观点
3. 使用简洁明了的中文表达
4. 突出重点，去除冗余信息
5. 如果是技术内容，保留关键术语"""
            },
            {
                "role": "user", 
                "content": f"请总结以下内容：\n\n{text}"
            }
        ]
        
        return self._make_request(messages, max_tokens=max_length + 50)
    
    def classify_text(self, text: str) -> Optional[Tuple[str, float]]:
        """
        文本分类
        
        Args:
            text: 要分类的文本
            
        Returns:
            (分类标签, 置信度)，失败时返回None
        """
        categories = [
            "科技资讯", "人工智能", "开发工具", "编程技术", 
            "产品发布", "行业动态", "学习资源", "开源项目",
            "创业投资", "社会热点", "生活娱乐", "其他"
        ]
        
        messages = [
            {
                "role": "system",
                "content": f"""你是一个专业的文本分类专家。请对用户提供的文本进行分类。

可选分类：{', '.join(categories)}

要求：
1. 从上述分类中选择最合适的一个
2. 返回JSON格式：{{"category": "分类名称", "confidence": 置信度(0-1的小数)}}
3. 置信度表示分类的确信程度
4. 如果不确定，选择"其他"类别"""
            },
            {
                "role": "user",
                "content": f"请对以下内容进行分类：\n\n{text}"
            }
        ]
        
        result = self._make_request(messages, max_tokens=100)
        if not result:
            return None
        
        try:
            # 尝试解析JSON
            parsed = json.loads(result)
            category = parsed.get('category', '其他')
            confidence = float(parsed.get('confidence', 0.5))
            
            # 验证分类是否在预定义列表中
            if category not in categories:
                category = '其他'
                confidence = 0.3
            
            return category, confidence
            
        except (json.JSONDecodeError, ValueError, TypeError):
            # 如果JSON解析失败，尝试从文本中提取分类
            for cat in categories:
                if cat in result:
                    return cat, 0.6
            return '其他', 0.3
    
    def analyze_content(self, title: str, content: str) -> Dict:
        """
        综合内容分析（总结+分类）
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            包含总结和分类结果的字典
        """
        full_text = f"{title}\n\n{content}" if title else content
        
        # 并行处理总结和分类（这里先串行，后续可优化为并行）
        summary = self.summarize_text(full_text)
        classification = self.classify_text(full_text)
        
        result = {
            'summary': summary or "总结生成失败",
            'category': '其他',
            'confidence': 0.0,
            'ai_processed': True,
            'timestamp': time.time()
        }
        
        if classification:
            result['category'] = classification[0]
            result['confidence'] = classification[1]
        
        return result
