#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型调用脚本
用于测试LLM服务的图片解析功能
"""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from backend.services.llm_service import LLMService
from backend.models.schemas import LLMProvider
from backend.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelTester:
    """
    模型测试类
    用于测试不同LLM提供商的图片解析功能
    """
    
    def __init__(self):
        """初始化测试器"""
        self.llm_service = LLMService()
        
    def encode_image_to_base64(self, image_path: str) -> str:
        """
        将图片编码为base64格式
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            str: base64编码的图片数据
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                logger.info(f"图片编码成功: {image_path}")
                return encoded_string
        except Exception as e:
            logger.error(f"图片编码失败: {str(e)}")
            raise
    
    async def test_openai_api(self, image_path: str, custom_prompt: Optional[str] = None) -> dict:
        """
        测试OpenAI API调用
        
        Args:
            image_path: 图片文件路径
            custom_prompt: 自定义提示词
            
        Returns:
            dict: API响应结果
        """
        try:
            logger.info("开始测试OpenAI API...")
            
            # 编码图片
            image_base64 = self.encode_image_to_base64(image_path)
            
            # 构建提示词
            prompt = self.llm_service.build_prompt("test_image.png", custom_prompt)
            logger.info(f"使用提示词: {prompt}")
            
            # 调用API
            response = await self.llm_service.call_openai_api(image_base64, prompt)
            logger.info("OpenAI API调用成功")
            
            return response
            
        except Exception as e:
            logger.error(f"OpenAI API测试失败: {str(e)}")
            raise
    
    async def test_qwen_api(self, image_path: str, custom_prompt: Optional[str] = None) -> dict:
        """
        测试通义千问API调用
        
        Args:
            image_path: 图片文件路径
            custom_prompt: 自定义提示词
            
        Returns:
            dict: API响应结果
        """
        try:
            logger.info("开始测试通义千问API...")
            
            # 编码图片
            image_base64 = self.encode_image_to_base64(image_path)
            
            # 构建提示词
            prompt = self.llm_service.build_prompt("test_image.png", custom_prompt)
            logger.info(f"使用提示词: {prompt}")
            
            # 调用API
            response = await self.llm_service.call_qwen_api(image_base64, prompt)
            logger.info("通义千问API调用成功")
            
            return response
            
        except Exception as e:
            logger.error(f"通义千问API测试失败: {str(e)}")
            raise
    
    async def test_analyze_image(self, image_path: str, provider: LLMProvider, 
                                custom_prompt: Optional[str] = None) -> list:
        """
        测试完整的图片分析流程
        
        Args:
            image_path: 图片文件路径
            provider: LLM提供商
            custom_prompt: 自定义提示词
            
        Returns:
            list: 识别出的题目列表
        """
        try:
            logger.info(f"开始测试图片分析流程，提供商: {provider.value}")
            
            # 调用分析方法
            questions = await self.llm_service.analyze_image(
                image_path=image_path,
                provider=provider,
                filename="test_image.png",
                page_number=1,
                custom_prompt=custom_prompt
            )
            
            logger.info(f"图片分析完成，识别出 {len(questions)} 道题目")
            return questions
            
        except Exception as e:
            logger.error(f"图片分析测试失败: {str(e)}")
            raise
    
    def print_questions(self, questions: list):
        """
        打印识别出的题目信息
        
        Args:
            questions: 题目列表
        """
        if not questions:
            print("\n❌ 没有识别出任何题目")
            return
        
        print(f"\n✅ 成功识别出 {len(questions)} 道题目:")
        print("=" * 80)
        
        for i, question in enumerate(questions, 1):
            print(f"\n📝 题目 {i}:")
            print(f"   ID: {question.id}")
            print(f"   页码: {question.page_number}")
            print(f"   内容: {question.content}")
            print(f"   难度: {question.difficulty.value if question.difficulty else '未知'}")
            print(f"   知识点: {', '.join(question.knowledge_points) if question.knowledge_points else '无'}")
            print(f"   答案: {question.answer if question.answer else '无'}")
            print(f"   解题步骤: {', '.join(question.solution_steps) if question.solution_steps else '无'}")
            print(f"   来源: {question.source}")
            print("-" * 40)
    
    def save_response_to_file(self, response: dict, filename: str):
        """
        保存API响应到文件
        
        Args:
            response: API响应数据
            filename: 保存的文件名
        """
        try:
            output_dir = Path("test_outputs")
            output_dir.mkdir(exist_ok=True)
            
            output_file = output_dir / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            
            logger.info(f"响应已保存到: {output_file}")
            
        except Exception as e:
            logger.error(f"保存响应失败: {str(e)}")

async def main():
    """
    主测试函数
    """
    print("🚀 LLM模型测试工具")
    print("=" * 50)
    
    # 检查配置
    print("\n📋 配置检查:")
    print(f"   OpenAI API Key: {'✅ 已配置' if settings.openai_api_key else '❌ 未配置'}")
    print(f"   通义千问 API Key: {'✅ 已配置' if settings.qwen_api_key else '❌ 未配置'}")
    print(f"   OpenAI Base URL: {settings.openai_base_url}")
    print(f"   通义千问 Base URL: {settings.qwen_base_url}")
    
    # 获取用户输入
    print("\n📁 请输入要测试的图片路径:")
    image_path = input("图片路径: ").strip()
    
    if not image_path:
        print("❌ 图片路径不能为空")
        return
    
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    print("\n🎯 请选择测试模式:")
    print("1. 测试OpenAI API")
    print("2. 测试通义千问API")
    print("3. 测试完整图片分析流程 (OpenAI)")
    print("4. 测试完整图片分析流程 (通义千问)")
    print("5. 测试所有功能")
    
    choice = input("请选择 (1-5): ").strip()
    
    # 获取自定义提示词
    print("\n💬 自定义提示词 (可选，直接回车使用默认):")
    custom_prompt = input("提示词: ").strip() or None
    
    # 创建测试器
    tester = ModelTester()
    
    try:
        if choice == "1":
            # 测试OpenAI API
            if not settings.openai_api_key:
                print("❌ OpenAI API Key未配置")
                return
            
            response = await tester.test_openai_api(image_path, custom_prompt)
            print("\n📄 OpenAI API响应:")
            print(json.dumps(response, ensure_ascii=False, indent=2))
            tester.save_response_to_file(response, "openai_response.json")
            
        elif choice == "2":
            # 测试通义千问API
            if not settings.qwen_api_key:
                print("❌ 通义千问API Key未配置")
                return
            
            response = await tester.test_qwen_api(image_path, custom_prompt)
            print("\n📄 通义千问API响应:")
            print(json.dumps(response, ensure_ascii=False, indent=2))
            tester.save_response_to_file(response, "qwen_response.json")
            
        elif choice == "3":
            # 测试OpenAI完整流程
            if not settings.openai_api_key:
                print("❌ OpenAI API Key未配置")
                return
            
            questions = await tester.test_analyze_image(image_path, LLMProvider.OPENAI, custom_prompt)
            tester.print_questions(questions)
            
        elif choice == "4":
            # 测试通义千问完整流程
            if not settings.qwen_api_key:
                print("❌ 通义千问API Key未配置")
                return
            
            questions = await tester.test_analyze_image(image_path, LLMProvider.QWEN, custom_prompt)
            tester.print_questions(questions)
            
        elif choice == "5":
            # 测试所有功能
            print("\n🔄 开始全面测试...")
            
            if settings.openai_api_key:
                print("\n--- OpenAI测试 ---")
                try:
                    questions = await tester.test_analyze_image(image_path, LLMProvider.OPENAI, custom_prompt)
                    print(f"OpenAI识别结果: {len(questions)} 道题目")
                    tester.print_questions(questions)
                except Exception as e:
                    print(f"OpenAI测试失败: {str(e)}")
            
            if settings.qwen_api_key:
                print("\n--- 通义千问测试 ---")
                try:
                    questions = await tester.test_analyze_image(image_path, LLMProvider.QWEN, custom_prompt)
                    print(f"通义千问识别结果: {len(questions)} 道题目")
                    tester.print_questions(questions)
                except Exception as e:
                    print(f"通义千问测试失败: {str(e)}")
        
        else:
            print("❌ 无效的选择")
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())