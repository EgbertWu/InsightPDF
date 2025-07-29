import asyncio
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from backend.services.llm_service import LLMService
from backend.models.schemas import LLMProvider, Question
from backend.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SingleImageTester:
    """
    单图片分析测试器
    用于测试单个图片的分析功能并导出CSV结果
    """
    
    def __init__(self):
        self.llm_service = LLMService()
    
    async def analyze_single_image(self, 
                                 image_path: str, 
                                 provider: LLMProvider = LLMProvider.QWEN,
                                 custom_prompt: Optional[str] = None) -> List[Question]:
        """
        分析单个图片
        
        Args:
            image_path: 图片文件路径
            provider: 大模型提供商
            custom_prompt: 自定义提示词
            
        Returns:
            List[Question]: 识别出的题目列表
        """
        try:
            # 检查图片文件是否存在
            if not Path(image_path).exists():
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            logger.info(f"开始分析图片: {image_path}")
            logger.info(f"使用模型: {provider.value}")
            
            # 调用LLM服务分析图片
            questions = await self.llm_service.analyze_image(
                image_path=image_path,
                provider=provider,
                filename=Path(image_path).name,
                # 移除：page_number=1,
                custom_prompt=custom_prompt
            )
            
            logger.info(f"分析完成，识别到 {len(questions)} 道题目")
            return questions
            
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            raise
    
    def export_to_csv(self, 
                     questions: List[Question], 
                     output_path: Optional[str] = None,
                     image_name: str = "test_image") -> str:
        """
        将题目导出为CSV文件
        
        Args:
            questions: 题目列表
            output_path: 输出文件路径，如果为None则自动生成
            image_name: 图片名称，用于生成文件名
            
        Returns:
            str: CSV文件路径
        """
        try:
            # 生成输出文件路径
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{Path(image_name).stem}_{timestamp}_questions.csv"
                output_path = Path("test_outputs") / filename
            
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 写入CSV文件
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    '题目ID', '题目内容', '难度等级', '知识点', 
                    '答案', '解析', '来源文件', '置信度'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 写入表头
                writer.writeheader()
                
                # 写入数据
                for question in questions:
                    writer.writerow({
                        '题目ID': question.id,
                        # 移除：'页码': question.page_number,
                        '题目内容': question.content,
                        '难度等级': question.difficulty.value if question.difficulty else '',
                        '知识点': ', '.join(question.knowledge_points) if question.knowledge_points else '',
                        '答案': question.answer if question.answer else '',
                        '解析': question.explanation if question.explanation else '',
                        '来源文件': question.source,
                        '置信度': question.confidence if question.confidence else ''
                    })
            
            logger.info(f"成功导出 {len(questions)} 道题目到 {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"CSV导出失败: {str(e)}")
            raise
    
    def print_questions_summary(self, questions: List[Question]):
        """
        打印题目摘要信息
        
        Args:
            questions: 题目列表
        """
        if not questions:
            print("\n❌ 没有识别到任何题目")
            return
        
        print(f"\n✅ 成功识别到 {len(questions)} 道题目:")
        print("-" * 80)
        
        for i, question in enumerate(questions, 1):
            print(f"\n题目 {i}:")
            print(f"  ID: {question.id}")
            print(f"  内容: {question.content[:100]}{'...' if len(question.content) > 100 else ''}")
            print(f"  难度: {question.difficulty.value if question.difficulty else '未知'}")
            print(f"  知识点: {', '.join(question.knowledge_points) if question.knowledge_points else '无'}")
            if question.answer:
                print(f"  答案: {question.answer[:50]}{'...' if len(question.answer) > 50 else ''}")
        
        print("-" * 80)

async def main():
    """
    主函数 - 运行单图片分析测试
    """
    # 配置参数
    image_path = input("请输入图片文件路径: ").strip()
    
    # 选择模型
    print("\n选择分析模型:")
    print("1. OpenAI (gpt-4-vision-preview)")
    print("2. 通义千问 (qwen-vl-plus)")
    
    choice = input("请选择 (1 或 2，默认为 2): ").strip() or "2"
    provider = LLMProvider.OPENAI if choice == "1" else LLMProvider.QWEN
    
    # 自定义提示词
    custom_prompt = input("\n请输入自定义提示词 (可选，直接回车跳过): ").strip() or None
    
    # 创建测试器
    tester = SingleImageTester()
    
    try:
        print(f"\n🚀 开始分析图片: {image_path}")
        print(f"📊 使用模型: {provider.value}")
        
        # 分析图片
        questions = await tester.analyze_single_image(
            image_path=image_path,
            provider=provider,
            custom_prompt=custom_prompt
        )
        
        # 打印结果摘要
        tester.print_questions_summary(questions)
        
        # 导出CSV
        if questions:
            csv_path = tester.export_to_csv(
                questions=questions,
                image_name=Path(image_path).name
            )
            print(f"\n📄 CSV文件已保存到: {csv_path}")
        
        print("\n✅ 测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())