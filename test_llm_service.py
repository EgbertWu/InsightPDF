import asyncio
import json
import logging
import csv
from pathlib import Path
from datetime import datetime
from backend.services.llm_service import LLMService
from backend.services.task_service import TaskService
from backend.models.schemas import LLMProvider, Question, DifficultyLevel
from backend.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMServiceTester:
    """
    LLM服务测试类
    用于测试修改后的LLMService的各种功能，包括CSV存储
    """
    
    def __init__(self):
        """
        初始化测试器
        """
        self.llm_service = LLMService()
        self.task_service = TaskService()
        self.test_image_path = None
        
    def setup_test_image(self):
        """
        设置测试图片路径
        """
        # 查找项目中的测试图片
        possible_paths = [
            "data/test_image.png",
            "data/test_image.jpg",
            "test_image.png",
            "test_image.jpg"
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                self.test_image_path = str(Path(path).absolute())
                logger.info(f"找到测试图片: {self.test_image_path}")
                return True
                
        logger.warning("未找到测试图片，请确保有可用的测试图片文件")
        return False
    
    def create_mock_questions(self) -> list[Question]:
        """
        创建模拟题目数据用于测试CSV存储
        
        Returns:
            list[Question]: 模拟题目列表
        """
        mock_questions = [
            Question(
                id=1,
                content="小明有5个苹果，小红有3个苹果，他们一共有多少个苹果？",
                answer="8个苹果",
                explanation="这是一道简单的加法题，5 + 3 = 8",
                knowledge_points=["加法运算", "应用题"],
                difficulty=DifficultyLevel.EASY,
                confidence=0.95,
                source="test.pdf"
            ),
            Question(
                id=2,
                content="一个长方形的长是8米，宽是6米，求这个长方形的面积。",
                answer="48平方米",
                explanation="长方形面积 = 长 × 宽 = 8 × 6 = 48平方米",
                knowledge_points=["长方形面积", "几何"],
                difficulty=DifficultyLevel.MEDIUM,
                confidence=0.90,
                source="test.pdf"
            ),
            Question(
                id=3,
                content="班级里有24名学生，如果每6人一组，可以分成几组？",
                answer="4组",
                explanation="这是除法应用题，24 ÷ 6 = 4组",
                knowledge_points=["除法运算", "分组问题"],
                difficulty=DifficultyLevel.EASY,
                confidence=0.88,
                source="test.pdf"
            )
        ]
        return mock_questions
    
    async def test_raw_qwen_api_response(self):
        """
        测试通义千问API的原始响应
        用于调试API返回格式
        """
        print("\n=== 测试通义千问API原始响应 ===")
        
        if not self.test_image_path:
            print("❌ 没有可用的测试图片")
            return
            
        try:
            # 编码图片
            image_base64 = self.llm_service.encode_image_to_base64(self.test_image_path)
            
            # 构建简单的测试提示词
            test_prompt = self.llm_service.build_prompt("test.pdf")
            
            # 调用API
            print("📡 正在调用通义千问API...")
            response = await self.llm_service.call_qwen_api(image_base64, test_prompt)
            
            # 打印原始响应结构
            print("\n📋 原始API响应结构:")
            print(f"响应类型: {type(response)}")
            print(f"响应键: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
            
            # 打印完整响应（格式化）
            print("\n📄 完整API响应:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            
            # 尝试提取内容
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                print("\n📝 提取的内容:")
                print(content)
                
                # 尝试解析JSON
                try:
                    parsed_json = json.loads(content)
                    print("\n✅ JSON解析成功:")
                    print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON解析失败: {e}")
                    print("尝试清理内容...")
                    
                    # 尝试清理内容
                    import re
                    cleaned_content = content.strip()
                    if cleaned_content.startswith('```'):
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned_content)
                        if json_match:
                            cleaned_content = json_match.group(1).strip()
                            print(f"清理后内容: {cleaned_content}")
                            try:
                                parsed_json = json.loads(cleaned_content)
                                print("✅ 清理后JSON解析成功:")
                                print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
                            except json.JSONDecodeError as e2:
                                print(f"❌ 清理后仍然解析失败: {e2}")
            else:
                print("❌ 响应格式异常，无法提取内容")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            logger.error(f"原始API测试失败: {str(e)}", exc_info=True)
    
    async def test_analyze_image_method(self):
        """
        测试analyze_image方法的完整流程
        """
        print("\n=== 测试analyze_image方法 ===")
        
        if not self.test_image_path:
            print("❌ 没有可用的测试图片")
            return
            
        try:
            print("📡 正在调用analyze_image方法...")
            questions = await self.llm_service.analyze_image(
                image_path=self.test_image_path,
                provider=LLMProvider.QWEN,
                filename="test.pdf"
            )
            
            print(f"\n✅ 成功识别 {len(questions)} 道题目")
            
            for i, question in enumerate(questions, 1):
                print(f"\n📝 题目 {i}:")
                print(f"  ID: {question.id}")
                print(f"  内容: {question.content[:100]}..." if len(question.content) > 100 else f"  内容: {question.content}")
                print(f"  答案: {question.answer}")
                print(f"  难度: {question.difficulty}")
                print(f"  置信度: {question.confidence}")
                print(f"  知识点: {question.knowledge_points}")
                print(f"  来源: {question.source}")
            
            return questions
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            logger.error(f"analyze_image测试失败: {str(e)}", exc_info=True)
            return []
    
    def test_csv_initialization(self):
        """
        测试CSV文件初始化功能
        """
        print("\n=== 测试CSV文件初始化 ===")
        
        try:
            # 测试CSV文件初始化
            task_id = "test_task_123"
            task_name = "测试任务"
            
            print("📄 正在初始化CSV文件...")
            csv_path = self.task_service._initialize_csv_file(task_id, task_name)
            
            print(f"✅ CSV文件创建成功: {csv_path}")
            
            # 验证文件是否存在
            if Path(csv_path).exists():
                print("✅ 文件确实存在")
                
                # 读取并显示表头
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    print(f"📋 CSV表头: {headers}")
            else:
                print("❌ 文件不存在")
                
            return csv_path
            
        except Exception as e:
            print(f"❌ CSV初始化测试失败: {str(e)}")
            logger.error(f"CSV初始化测试失败: {str(e)}", exc_info=True)
            return None
    
    def test_csv_append_questions(self, csv_path: str = None):
        """
        测试向CSV文件追加题目数据
        
        Args:
            csv_path: CSV文件路径，如果为None则先创建新文件
        """
        print("\n=== 测试CSV追加题目数据 ===")
        
        try:
            # 如果没有提供CSV路径，先创建一个
            if not csv_path:
                csv_path = self.test_csv_initialization()
                if not csv_path:
                    print("❌ 无法创建CSV文件，跳过追加测试")
                    return
            
            # 创建模拟题目数据
            mock_questions = self.create_mock_questions()
            
            print(f"📝 正在向CSV文件追加 {len(mock_questions)} 道题目...")
            self.task_service._append_questions_to_csv(csv_path, mock_questions)
            
            print("✅ 题目数据追加成功")
            
            # 验证数据是否正确写入
            self.verify_csv_content(csv_path)
            
        except Exception as e:
            print(f"❌ CSV追加测试失败: {str(e)}")
            logger.error(f"CSV追加测试失败: {str(e)}", exc_info=True)
    
    def verify_csv_content(self, csv_path: str):
        """
        验证CSV文件内容
        
        Args:
            csv_path: CSV文件路径
        """
        print("\n📋 验证CSV文件内容:")
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            print(f"✅ CSV文件包含 {len(rows)} 行数据")
            
            # 显示前几行数据
            for i, row in enumerate(rows[:3], 1):
                print(f"\n📝 第{i}行数据:")
                for key, value in row.items():
                    if len(str(value)) > 50:
                        print(f"  {key}: {str(value)[:50]}...")
                    else:
                        print(f"  {key}: {value}")
                        
            if len(rows) > 3:
                print(f"\n... 还有 {len(rows) - 3} 行数据")
                
        except Exception as e:
            print(f"❌ 验证CSV内容失败: {str(e)}")
    
    async def test_complete_workflow_with_csv(self):
        """
        测试完整的工作流程：图像识别 + CSV存储
        """
        print("\n=== 测试完整工作流程（图像识别 + CSV存储）===")
        
        if not self.test_image_path:
            print("❌ 没有可用的测试图片，使用模拟数据")
            questions = self.create_mock_questions()
        else:
            # 尝试真实的图像识别
            print("📡 正在进行图像识别...")
            questions = await self.test_analyze_image_method()
            
            # 如果识别失败，使用模拟数据
            if not questions:
                print("⚠️  图像识别失败，使用模拟数据")
                questions = self.create_mock_questions()
        
        if questions:
            print(f"\n📝 获得 {len(questions)} 道题目，开始CSV存储测试...")
            
            # 初始化CSV文件
            csv_path = self.test_csv_initialization()
            
            if csv_path:
                # 追加题目数据
                print("\n📄 正在将识别结果保存到CSV...")
                self.task_service._append_questions_to_csv(csv_path, questions)
                
                # 验证结果
                self.verify_csv_content(csv_path)
                
                print(f"\n🎉 完整工作流程测试成功！CSV文件保存在: {csv_path}")
            else:
                print("❌ CSV文件创建失败")
        else:
            print("❌ 没有题目数据可供测试")
    
    async def test_custom_prompt(self):
        """
        测试自定义提示词
        """
        print("\n=== 测试自定义提示词 ===")
        
        if not self.test_image_path:
            print("❌ 没有可用的测试图片")
            return
            
        custom_prompt = """
请分析这张图片中的数学题目。

要求：
1. 只用中文回答
2. 返回JSON格式
3. 如果有题目，按以下格式返回：
{"questions": [{"id": 1, "content": "题目内容", "answer": "答案", "explanation": "解析", "knowledge_points": ["知识点"], "difficulty": "easy", "confidence": 0.9, "source": "test.pdf"}]}
4. 如果没有题目，返回：{"questions": []}
"""
        
        try:
            print("📡 正在使用自定义提示词测试...")
            questions = await self.llm_service.analyze_image(
                image_path=self.test_image_path,
                provider=LLMProvider.QWEN,
                filename="test.pdf",
                custom_prompt=custom_prompt
            )
            
            print(f"\n✅ 自定义提示词测试成功，识别 {len(questions)} 道题目")
            return questions
            
        except Exception as e:
            print(f"❌ 自定义提示词测试失败: {str(e)}")
            logger.error(f"自定义提示词测试失败: {str(e)}", exc_info=True)
            return []
    
    async def test_error_handling(self):
        """
        测试错误处理
        """
        print("\n=== 测试错误处理 ===")
        
        # 测试不存在的图片文件
        try:
            print("📡 测试不存在的图片文件...")
            await self.llm_service.analyze_image(
                image_path="nonexistent.jpg",
                provider=LLMProvider.QWEN,
                filename="test.pdf"
            )
            print("❌ 应该抛出异常但没有")
        except Exception as e:
            print(f"✅ 正确捕获异常: {str(e)}")
        
        # 测试CSV错误处理
        try:
            print("\n📄 测试CSV错误处理（无效路径）...")
            self.task_service._append_questions_to_csv(
                "/invalid/path/test.csv", 
                self.create_mock_questions()
            )
            print("❌ 应该抛出异常但没有")
        except Exception as e:
            print(f"✅ 正确捕获CSV异常: {str(e)}")
    
    def print_current_config(self):
        """
        打印当前配置信息
        """
        print("\n=== 当前配置信息 ===")
        config = settings.get_llm_config("qwen")
        print(f"模型: {config['model']}")
        print(f"API基础URL: {config['base_url']}")
        print(f"API密钥: {'已配置' if config['api_key'] else '未配置'}")
        print(f"超时时间: {settings.api_timeout_seconds}秒")
        print(f"最大重试次数: {settings.max_retries}次")
        print(f"输出目录: {settings.output_path}")
        print(f"上传目录: {settings.upload_path}")
    
    async def run_all_tests(self):
        """
        运行所有测试
        """
        print("🚀 开始LLM服务完整测试（包括CSV存储）")
        
        # 打印配置信息
        self.print_current_config()
        
        # 设置测试图片
        if not self.setup_test_image():
            print("\n⚠️  警告: 没有找到测试图片，某些测试将使用模拟数据")
            print("请在项目根目录或data目录下放置测试图片文件（test_image.png 或 test_image.jpg）")
        
        # 运行各项测试
        await self.test_raw_qwen_api_response()
        await self.test_analyze_image_method()
        await self.test_custom_prompt()
        
        # CSV相关测试
        self.test_csv_initialization()
        self.test_csv_append_questions()
        
        # 完整工作流程测试
        await self.test_complete_workflow_with_csv()
        
        # 错误处理测试
        await self.test_error_handling()
        
        print("\n🎉 所有测试完成！")

def main():
    """
    主函数 - 提供交互式测试菜单
    """
    tester = LLMServiceTester()
    
    while True:
        print("\n" + "="*60)
        print("🧪 LLM服务完整测试工具（包括CSV存储）")
        print("="*60)
        print("1. 查看当前配置")
        print("2. 设置测试图片")
        print("3. 测试通义千问API原始响应")
        print("4. 测试analyze_image方法")
        print("5. 测试自定义提示词")
        print("6. 测试CSV文件初始化")
        print("7. 测试CSV追加题目数据")
        print("8. 测试完整工作流程（图像识别 + CSV存储）")
        print("9. 测试错误处理")
        print("10. 运行所有测试")
        print("0. 退出")
        print("="*60)
        
        choice = input("请选择测试项目 (0-10): ").strip()
        
        if choice == "0":
            print("👋 再见！")
            break
        elif choice == "1":
            tester.print_current_config()
        elif choice == "2":
            tester.setup_test_image()
        elif choice == "3":
            asyncio.run(tester.test_raw_qwen_api_response())
        elif choice == "4":
            asyncio.run(tester.test_analyze_image_method())
        elif choice == "5":
            asyncio.run(tester.test_custom_prompt())
        elif choice == "6":
            tester.test_csv_initialization()
        elif choice == "7":
            tester.test_csv_append_questions()
        elif choice == "8":
            asyncio.run(tester.test_complete_workflow_with_csv())
        elif choice == "9":
            asyncio.run(tester.test_error_handling())
        elif choice == "10":
            asyncio.run(tester.run_all_tests())
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()