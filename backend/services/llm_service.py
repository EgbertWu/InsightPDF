import base64
import httpx
import logging
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config.settings import settings
from backend.models.schemas import Question, LLMProvider

logger = logging.getLogger(__name__)

class LLMService:
    """
    大模型服务类
    负责调用OpenAI和通义千问API进行图像识别和文本理解
    """
    
    def __init__(self):
        """
        初始化大模型服务
        """
        self.timeout = settings.api_timeout_seconds
        self.max_retries = settings.max_retries
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """
        将图片编码为base64字符串
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            str: base64编码的图片字符串
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def build_prompt(self, filename: str, custom_prompt: Optional[str] = None) -> str:
        """
        构建用于应用题识别的提示词
        
        Args:
            filename: PDF文件名
            custom_prompt: 自定义提示词
            
        Returns:
            str: 完整的提示词
        """
        if custom_prompt:
            return custom_prompt
        
        default_prompt = f"""
你是一个专业的应用题识别和分析专家。请仔细分析这张图片中的应用题内容。

**关键要求：**
1. 必须用中文回答
2. 必须严格按照JSON格式返回结果
3. 不要添加任何markdown代码块标记
4. 不要添加任何解释文字
5. 直接返回纯JSON格式

分析要求：
1. 识别图片中的所有应用题，按顺序编号
2. 完整提取每道题的题目内容
3. 如果图片中包含答案，请提取答案
4. 如果有解题过程或解析，请提取解析
5. 分析每道题涉及的知识点
6. 评估题目难度（easy/medium/hard）
7. 给出识别置信度（0-1之间的小数）

**输出格式示例（必须严格遵循）：**
{{
  "questions": [
    {{
      "id": 1,
      "content": "题目内容",
      "answer": "答案（如果有）",
      "explanation": "解析（如果有）",
      "knowledge_points": ["考点1", "考点2"],
      "difficulty": "medium",
      "confidence": 0.95,
      "source": "{filename}"
    }}
  ]
}}

注意：
- 如果图片中没有应用题，返回：{{"questions": []}}
- 如果某些信息不确定，可以设置为空字符串
- 必须返回有效的JSON格式
- 必须用中文描述题目内容和解析
"""
        return default_prompt
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_openai_api(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """
        调用OpenAI API进行图像识别
        
        Args:
            image_base64: base64编码的图片
            prompt: 提示词
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        config = settings.get_llm_config("openai")
        
        if not config["api_key"]:
            raise ValueError("OpenAI API密钥未配置")
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_qwen_api(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """
        调用通义千问API进行图像识别
        
        Args:
            image_base64: base64编码的图片
            prompt: 提示词
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        config = settings.get_llm_config("qwen")
        
        if not config["api_key"]:
            raise ValueError("通义千问API密钥未配置")
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        # 使用OpenAI兼容格式
        payload = {
            "model": config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的中文应用题识别专家。请始终用中文回答，并严格按照JSON格式返回结果。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0,  # 改为0以获得更确定的输出
            "response_format": {"type": "json_object"}  # 强制JSON格式
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 添加 /chat/completions 路径
            response = await client.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def analyze_image(self, image_path: str, provider: LLMProvider, 
                          filename: str, custom_prompt: Optional[str] = None) -> List[Question]:
        """
        分析图片中的应用题
        
        Args:
            image_path: 图片文件路径
            provider: 大模型提供商
            filename: PDF文件名
            custom_prompt: 自定义提示词
            
        Returns:
            List[Question]: 识别出的应用题列表
        """
        try:
            # 编码图片
            image_base64 = self.encode_image_to_base64(image_path)
            
            # 构建提示词
            prompt = self.build_prompt(filename, custom_prompt)
            
            # 调用对应的API
            if provider == LLMProvider.OPENAI:
                response = await self.call_openai_api(image_base64, prompt)
                content = response["choices"][0]["message"]["content"]
            elif provider == LLMProvider.QWEN:
                response = await self.call_qwen_api(image_base64, prompt)
                # 修复：通义千问现在使用 OpenAI 兼容格式
                content = response["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"不支持的大模型提供商: {provider}")
            
            # 解析返回的JSON内容
            import json
            import re
            try:
                cleaned_content = content.strip()
                
                # 如果内容被包装在markdown代码块中，提取JSON部分
                if cleaned_content.startswith('```'):
                    # 使用正则表达式提取JSON内容
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned_content)
                    if json_match:
                        cleaned_content = json_match.group(1).strip()
                    else:
                        # 如果正则匹配失败，手动移除代码块标记
                        lines = cleaned_content.split('\n')
                        if lines[0].startswith('```'):
                            lines = lines[1:]
                        if lines and lines[-1].startswith('```'):
                            lines = lines[:-1]
                        cleaned_content = '\n'.join(lines).strip()
                
                # 解析清理后的JSON内容
                result = json.loads(cleaned_content)
                questions_data = result.get("questions", [])
                
                # 转换为Question对象
                questions = []
                for q_data in questions_data:
                    # 确保source字段正确设置
                    if "source" not in q_data or not q_data["source"]:
                        q_data["source"] = filename
                    
                    question = Question(**q_data)
                    questions.append(question)
                
                logger.info(f"成功识别 {len(questions)} 道应用题")
                return questions
                
            except json.JSONDecodeError as e:
                logger.error(f"解析API返回内容失败: {str(e)}")
                logger.error(f"原始内容: {content}")
                logger.error(f"清理后内容: {cleaned_content if 'cleaned_content' in locals() else 'N/A'}")
                return []
                
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            raise Exception(f"图片分析失败: {str(e)}")