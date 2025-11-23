import json
import os
import sys
import requests
from dotenv import load_dotenv

class EvalLLM:
    """评估用LLM类，专门用于模型评估和分析任务"""
    
    def __init__(self, config_path='config/config.json', env_path='config/.env', model_name='siliconflow_deepseek'):
        """初始化评估LLM
        
        Args:
            config_path: 配置文件路径
            env_path: 环境变量文件路径
            model_name: 模型名称，默认使用硅基流动的deepseek
        """
        self.config_path = config_path
        self.env_path = env_path
        self.model_name = model_name
        self.config = None
        self.model_config = None
        self._load_environment()
        self._load_config()
        self._setup_model()
    
    def _load_environment(self):
        """加载环境变量"""
        load_dotenv(self.env_path)
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            raise Exception(f"配置文件加载失败: {e}")
    
    def _setup_model(self):
        """设置模型配置"""
        if not self.config or 'eval_llm' not in self.config:
            raise Exception("配置文件中未找到eval_llm配置")
        
        if self.model_name not in self.config['eval_llm']:
            raise Exception(f"模型 '{self.model_name}' 未在eval_llm配置中找到")
        
        self.model_config = self.config['eval_llm'][self.model_name]
        
        if not self.model_config.get('enabled', False):
            raise Exception(f"模型 '{self.model_name}' 未启用")
    
    def get_available_models(self):
        """获取可用的评估模型列表"""
        if not self.config or 'eval_llm' not in self.config:
            return []
        return list(self.config['eval_llm'].keys())
    
    def call(self, prompt, content=""):
        """调用LLM API获取输出
        
        Args:
            prompt: 输入提示词
            content: 其他内容，默认为空
            
        Returns:
            str: 模型返回的文本内容，如果失败返回错误信息
        """
        # 获取API密钥
        api_key = os.getenv(self.model_config['api_key_env'])
        if not api_key:
            return f"未找到环境变量: {self.model_config['api_key_env']}"
        
        # 构建请求头
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 构建完整的用户输入
        if content:
            full_prompt = f"{prompt}\n\n{content}"
        else:
            full_prompt = prompt
        
        # 构建请求数据
        data = {
            'model': self.model_config['model'],
            'messages': [
                {'role': 'user', 'content': full_prompt}
            ],
            'max_tokens': self.model_config['max_tokens'],
            'temperature': self.model_config['temperature']
        }
        
        try:
            # 自动检测并使用系统代理（如果存在）
            proxies = None
            http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
            https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')

            if http_proxy or https_proxy:
                proxies = {
                    'http': http_proxy,
                    'https': https_proxy
                }

            # 发送API请求
            response = requests.post(
                f"{self.model_config['api_base']}/chat/completions",
                headers=headers,
                json=data,
                timeout=60,
                proxies=proxies
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content
            else:
                return f"API调用失败: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"请求异常: {str(e)}"
    
    def evaluate(self, prompt, content=""):
        """评估方法，与call方法相同，提供更语义化的接口
        
        Args:
            prompt: 输入提示词
            content: 其他内容，默认为空
            
        Returns:
            str: 模型返回的文本内容
        """
        return self.call(prompt, content)
    
    def test_connection(self):
        """测试模型连接是否正常
        
        Returns:
            tuple: (是否成功, 结果信息)
        """
        test_prompt = self.config.get('test_prompt', '你好，请简单介绍一下你自己。')
        result = self.call(test_prompt)
        
        # 判断是否成功（简单检查是否包含错误关键词）
        error_keywords = ['失败', '异常', '未找到', '未启用', '未加载', 'API调用失败', '请求异常']
        is_success = not any(keyword in result for keyword in error_keywords)
        
        return is_success, result
    
    def get_model_info(self):
        """获取当前模型信息"""
        return {
            'model_name': self.model_name,
            'api_base': self.model_config['api_base'],
            'model': self.model_config['model'],
            'max_tokens': self.model_config['max_tokens'],
            'temperature': self.model_config['temperature'],
            'enabled': self.model_config['enabled']
        }

def main():
    """主函数 - 检测模型调用是否成功"""
    try:
        # 创建评估LLM实例
        eval_llm = EvalLLM()
        
        print("✓ 评估LLM初始化成功")
        print(f"✓ 当前模型: {eval_llm.model_name}")
        print(f"✓ 可用模型: {', '.join(eval_llm.get_available_models())}")
        
        # 显示模型信息
        model_info = eval_llm.get_model_info()
        print(f"✓ 模型详情: {model_info['model']} @ {model_info['api_base']}")
        
        # 测试连接
        print(f"\n开始测试 {eval_llm.model_name} 连接...")
        success, result = eval_llm.test_connection()
        
        if success:
            print(f"✓ {eval_llm.model_name} 连接测试成功!")
            print("✓ 模型响应内容:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        else:
            print(f"✗ {eval_llm.model_name} 连接测试失败: {result}")
            return
        
        # 交互式测试
        print("\n" + "="*50)
        print("交互式测试:")
        while True:
            user_input = input("\n请输入测试提示词 (输入 'quit' 退出): ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            if user_input:
                # 询问是否需要添加额外内容
                extra_content = input("请输入额外内容 (可选，直接回车跳过): ").strip()
                
                print(f"\n调用 {eval_llm.model_name}...")
                response = eval_llm.call(user_input, extra_content)
                print("响应:")
                print("-" * 30)
                print(response)
                print("-" * 30)
        
    except Exception as e:
        print(f"✗ 初始化失败: {e}")

if __name__ == "__main__":
    # 检测模型调用是否成功
    main()