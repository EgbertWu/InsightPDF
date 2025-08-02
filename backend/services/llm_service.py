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
        default_prompt = f""" 你是一个专业的应用题识别和分析专家。请仔细分析这张图片中的应用题内容。
        **重要：你必须严格按照以下要求回答：**
        1. 只能用中文回答
        2. 只能返回JSON格式，不要任何其他内容
        3. 不要返回markdown代码块
        4. 不要返回文本提取结果
        5. 必须分析题目内容，不是提取文字
        **如果图片中有应用题，按以下JSON格式返回：**
        {{
          "questions": [
            {{
              "id": 1,
                "content": "完整的题目内容",
                "answer": "答案（推理得到答案）",
                "explanation": "解析（详细解析题目，给出推理过程）",
                "knowledge_points": ["知识点1", "知识点2"],
                "difficulty": "easy",
                "confidence": 0.9,
                "source": "{filename}"
            }}
          ]
        }}
        **如果图片中没有应用题，返回：**
        {{"questions": []}}
        请开始分析图片中的应用题：
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
                
                # 增强的响应格式检查
                logger.debug(f"通义千问API原始响应类型: {type(response)}")
                logger.debug(f"通义千问API原始响应: {response}")
                
                # 检查响应格式
                if isinstance(response, list):
                    # 如果返回的是列表，说明是OCR结果，不是我们要的题目分析
                    logger.warning("API返回OCR文本提取结果而非题目分析，跳过此图片")
                    return []
                elif isinstance(response, dict):
                    if "choices" in response and len(response["choices"]) > 0:
                        # 标准OpenAI格式
                        choice = response["choices"][0]
                        if isinstance(choice, dict) and "message" in choice:
                            content = choice["message"]["content"]
                        else:
                            logger.error(f"意外的choice格式: {choice}")
                            return []
                    elif "output" in response:
                        # 通义千问原生格式
                        content = response["output"].get("text", "")
                    elif "text" in response:
                        # 简化格式
                        content = response["text"]
                    else:
                        logger.error(f"无法识别的响应格式: {list(response.keys())}")
                        return []
                else:
                    logger.error(f"意外的响应类型: {type(response)}")
                    return []
            else:
                raise ValueError(f"不支持的大模型提供商: {provider}")
            
            # 检查内容是否为空
            if not content or not content.strip():
                logger.warning("API返回空内容")
                return []
            
            # 检查是否是OCR文本提取结果（包含start_char, end_char等字段）
            if "start_char" in content or "end_char" in content or "text_content" in content:
                logger.warning("检测到OCR文本提取结果，跳过此图片")
                return []
            
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
                
                # 再次检查是否是OCR结果
                if cleaned_content.startswith('[') and '"start_char"' in cleaned_content:
                    logger.warning("清理后仍然是OCR文本提取结果，跳过此图片")
                    return []
                
                # 解析清理后的JSON内容
                result = json.loads(cleaned_content)
                
                # 检查结果格式
                if isinstance(result, list):
                    # 如果结果是列表，检查是否是OCR结果
                    if result and isinstance(result[0], dict) and "start_char" in result[0]:
                        logger.warning("解析结果是OCR文本提取，跳过此图片")
                        return []
                    else:
                        # 可能是题目列表，尝试转换
                        logger.warning("API返回题目列表而非标准格式，尝试转换")
                        questions_data = result
                elif isinstance(result, dict):
                    questions_data = result.get("questions", [])
                else:
                    logger.error(f"无法识别的JSON结果类型: {type(result)}")
                    return []
                
                # 转换为Question对象
                questions = []
                for i, q_data in enumerate(questions_data, 1):
                    try:
                        # 数据格式标准化处理
                        standardized_data = {}
                        
                        # 处理ID字段
                        if "id" in q_data:
                            standardized_data["id"] = q_data["id"]
                        elif "question_id" in q_data:
                            standardized_data["id"] = int(q_data["question_id"]) if str(q_data["question_id"]).isdigit() else i
                        else:
                            standardized_data["id"] = i
                        
                        # 处理content字段 - 增加中文字段支持
                        if "content" in q_data:
                            standardized_data["content"] = q_data["content"]
                        elif "text" in q_data:
                            standardized_data["content"] = q_data["text"]
                        elif "question" in q_data:
                            standardized_data["content"] = q_data["question"]
                        elif "题目内容" in q_data:  # 新增中文字段支持
                            standardized_data["content"] = q_data["题目内容"]
                        elif "题目" in q_data:  # 新增中文字段支持
                            standardized_data["content"] = q_data["题目"]
                        elif "问题" in q_data:  # 新增中文字段支持
                            standardized_data["content"] = q_data["问题"]
                        else:
                            # 如果没有明确的题目内容，跳过这个数据
                            logger.warning(f"跳过无题目内容的数据: {q_data}")
                            continue
                        
                        # 处理类型字段 - 增加中文字段支持
                        question_type = q_data.get("type") or q_data.get("题目类型") or q_data.get("类型") or "应用题"
                        
                        # 处理其他字段，设置默认值
                        standardized_data["answer"] = q_data.get("answer") or q_data.get("答案") or ""
                        standardized_data["explanation"] = q_data.get("explanation") or q_data.get("解释") or q_data.get("解答过程") or ""
                        standardized_data["knowledge_points"] = q_data.get("knowledge_points") or q_data.get("知识点") or []
                        
                        # 处理difficulty字段
                        difficulty = q_data.get("difficulty", "medium")
                        if difficulty not in ["easy", "medium", "hard"]:
                            difficulty = "medium"
                        standardized_data["difficulty"] = difficulty
                        
                        standardized_data["confidence"] = float(q_data.get("confidence", 0.8))
                        
                        # 确保source字段正确设置
                        standardized_data["source"] = q_data.get("source", filename)
                        
                        # 创建Question对象
                        question = Question(**standardized_data)
                        questions.append(question)
                        
                    except Exception as e:
                        logger.warning(f"跳过无效题目数据: {q_data}, 错误: {str(e)}")
                        continue
                
                logger.info(f"成功识别 {len(questions)} 道应用题")
                return questions
                
            except json.JSONDecodeError as e:
                logger.error(f"解析API返回内容失败: {str(e)}")
                logger.error(f"原始内容: {content}")
                logger.error(f"清理后内容: {cleaned_content if 'cleaned_content' in locals() else 'N/A'}")
                return []
                
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            # 不再抛出异常，而是返回空列表，让批处理继续
            return []