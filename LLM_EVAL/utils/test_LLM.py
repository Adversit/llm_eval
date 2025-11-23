import json
import os
import sys
import requests
from dotenv import load_dotenv

class LLMTester:
    """LLM测试类，用于调用各种大语言模型API"""
    
    def __init__(self, config_path='config/config.json', env_path='config/.env'):
        """初始化LLM测试器
        
        Args:
            config_path: 配置文件路径
            env_path: 环境变量文件路径
        """
        self.config_path = config_path
        self.env_path = env_path
        self.config = None
        self._load_environment()
        self._load_config()
    
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
    
    def get_available_models(self):
        """获取可用模型列表"""
        if not self.config:
            return []
        return list(self.config.get('LLM_test', {}).keys())
    
    def call_llm(self, prompt, model_name='deepseek', content=""):
        """调用LLM API获取文本输出
        
        Args:
            prompt: 输入提示词
            model_name: 模型名称，默认为deepseek
            content: 其他内容，默认为空
            
        Returns:
            str: 模型返回的文本内容，如果失败返回错误信息
        """
        if not self.config:
            return "配置文件未加载"
        
        if model_name not in self.config['LLM_test']:
            return f"模型 '{model_name}' 未在配置中找到"
        
        model_config = self.config['LLM_test'][model_name]
        
        if not model_config.get('enabled', False):
            return f"模型 '{model_name}' 未启用"
        
        # 获取API密钥
        api_key = os.getenv(model_config['api_key_env'])
        if not api_key:
            return f"未找到环境变量: {model_config['api_key_env']}"
        
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
            'model': model_config['model'],
            'messages': [
                {'role': 'user', 'content': full_prompt}
            ],
            'max_tokens': model_config['max_tokens'],
            'temperature': model_config['temperature']
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
                f"{model_config['api_base']}/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
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
    
    def test_model(self, model_name='deepseek'):
        """测试指定模型是否可用
        
        Args:
            model_name: 模型名称
            
        Returns:
            tuple: (是否成功, 结果信息)
        """
        test_prompt = self.config.get('test_prompt', '你好，请简单介绍一下你自己。')
        result = self.call_llm(test_prompt, model_name)
        
        # 判断是否成功（简单检查是否包含错误关键词）
        error_keywords = ['失败', '异常', '未找到', '未启用', '未加载']
        is_success = not any(keyword in result for keyword in error_keywords)
        
        return is_success, result

def main():
    """主函数 - 测试LLM调用"""
    try:
        # 创建LLM测试器实例
        llm_tester = LLMTester()
        
        print("✓ LLM测试器初始化成功")
        print(f"✓ 可用模型: {', '.join(llm_tester.get_available_models())}")
        
        # 获取要测试的模型名称
        if len(sys.argv) > 1:
            model_name = sys.argv[1]
        else:
            model_name = input("请输入要测试的模型名称 (默认: deepseek): ").strip()
            model_name = model_name if model_name else "deepseek"
        
        print(f"✓ 选择测试模型: {model_name}")
        
        # 测试模型
        print(f"\n开始测试 {model_name} API...")
        success, result = llm_tester.test_model(model_name)
        
        if success:
            print(f"✓ {model_name} API调用成功!")
            print("✓ 模型响应内容:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        else:
            print(f"✗ {model_name} API调用失败: {result}")
        
        # 演示直接调用
        print("\n" + "="*50)
        print("演示直接调用:")
        user_input = input("请输入要测试的提示词 (回车跳过): ").strip()
        if user_input:
            # 询问是否需要添加额外内容
            extra_content = input("请输入额外内容 (可选，直接回车跳过): ").strip()
            
            print(f"\n调用 {model_name} 处理: {user_input}")
            if extra_content:
                print(f"附加内容: {extra_content[:100]}...")  # 只显示前100个字符
            
            response = llm_tester.call_llm(user_input, model_name, extra_content)
            print("响应:")
            print("-" * 30)
            print(response)
            print("-" * 30)
        
    except Exception as e:
        print(f"✗ 初始化失败: {e}")

if __name__ == "__main__":
    # 检测模型调用是否成功
    main()