import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
import logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.json_serializer import safe_json_dump

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InformationFormInterface:
    """信息填写界面"""

    def __init__(self, key_prefix: str = ""):
        """初始化信息填写界面

        Args:
            key_prefix: 按钮key的前缀，用于避免重复key冲突
        """
        self.info_dir = Path("visiualization")
        self.info_dir.mkdir(exist_ok=True)
        self.key_prefix = key_prefix
        self.config = self._load_config()
        logger.info("InformationFormInterface初始化完成")

    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = Path("config/config.json")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def _get_available_test_models(self):
        """获取可用的测试模型列表"""
        if not self.config:
            return []

        models = []
        for model_key, model_config in self.config.get('LLM_test', {}).items():
            if model_config.get('enabled', False):
                display_name = model_config.get('display_name', model_key)
                models.append({
                    'key': model_key,
                    'display_name': display_name,
                    'description': model_config.get('description', '')
                })
        return models

    def _get_available_eval_models(self):
        """获取可用的评估模型列表"""
        if not self.config:
            return []

        models = []
        for model_key, model_config in self.config.get('eval_llm', {}).items():
            if model_config.get('enabled', False):
                display_name = model_config.get('display_name', model_key)
                models.append({
                    'key': model_key,
                    'display_name': display_name,
                    'description': model_config.get('description', '')
                })
        return models
    
    def render(self):
        """渲染信息填写界面"""
        st.header("📝 评估信息填写")
        st.markdown("请填写以下评估相关信息，所有信息将用于生成评估报告。")
        
        # 初始化时加载已存在的信息
        self._load_existing_info()
        
        # 检查是否已经填写过信息
        if self._check_existing_info():
            self._display_existing_info()
        else:
            self._render_form()
    
    def _render_form(self):
        """渲染信息填写表单"""
        with st.form("evaluation_info_form"):
            st.subheader("🔧 基本信息")

            # 获取可用模型列表
            test_models = self._get_available_test_models()
            eval_models = self._get_available_eval_models()

            # === 被评估模型选择 ===
            st.markdown("### 🤖 被评估模型（测试模型）")

            # 选择模式：下拉选择 or 自定义输入
            model_input_mode = st.radio(
                "选择输入方式",
                ["从列表选择", "自定义输入"],
                horizontal=True,
                key="model_input_mode",
                help="选择从配置的模型列表中选择，或输入自定义模型名称"
            )

            if model_input_mode == "从列表选择":
                if test_models:
                    model_options = [f"{m['display_name']}" for m in test_models]
                    selected_index = st.selectbox(
                        "选择被评估模型 *",
                        range(len(model_options)),
                        format_func=lambda x: model_options[x],
                        help="选择要评估的模型"
                    )

                    selected_model = test_models[selected_index]
                    model_name = selected_model['key']

                    # 显示模型说明 - 已禁用
                    # st.info(f"📝 {selected_model['description']}")
                else:
                    st.warning("⚠️ 配置文件中没有可用的测试模型")
                    model_name = st.text_input(
                        "请手动输入模型名称 *",
                        placeholder="例如：deepseek"
                    )
            else:
                model_name = st.text_input(
                    "自定义模型名称 *",
                    placeholder="例如：my-custom-model",
                    help="输入自定义模型名称，这将作为数据存储的目录名"
                )

            st.markdown("---")

            # === 评估模型选择 ===
            st.markdown("### 📊 评估模型（用于评分的模型）")

            if eval_models:
                eval_options = [f"{m['display_name']}" for m in eval_models]
                eval_selected_index = st.selectbox(
                    "选择评估模型 *",
                    range(len(eval_options)),
                    format_func=lambda x: eval_options[x],
                    help="选择用于评估的模型"
                )

                selected_eval_model = eval_models[eval_selected_index]
                eval_model_name = selected_eval_model['key']

                # 显示评估模型说明 - 已禁用
                # st.info(f"📝 {selected_eval_model['description']}")
            else:
                st.warning("⚠️ 配置文件中没有可用的评估模型")
                eval_model_name = st.text_input(
                    "请手动输入评估模型名称 *",
                    placeholder="例如：siliconflow_deepseek_v3"
                )

            st.markdown("---")

            # === 其他信息 ===
            st.markdown("### 📋 备注信息")

            # 备注（选填）
            remarks = st.text_area(
                "备注",
                placeholder="请输入任何相关的备注信息（可选）...",
                help="可选填写，用于记录评估的特殊说明或注意事项",
                height=100
            )

            # 提交按钮
            submitted = st.form_submit_button(
                "💾 保存信息并继续",
                type="primary",
                use_container_width=True
            )

            if submitted:
                if self._validate_form(model_name, eval_model_name):
                    self._save_info(model_name, remarks, eval_model_name)
                    st.success("✅ 信息保存成功！")
                    st.rerun()
    
    def _validate_form(self, model_name: str, eval_model_name: str = None) -> bool:
        """验证表单输入"""
        if not model_name or not model_name.strip():
            st.error("❌ 请填写被评估模型名称")
            return False

        if eval_model_name is not None and (not eval_model_name or not eval_model_name.strip()):
            st.error("❌ 请选择评估模型")
            return False

        # 检查模型名称是否包含特殊字符
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in model_name for char in invalid_chars):
            st.error(f"❌ 模型名称不能包含以下字符: {', '.join(invalid_chars)}")
            return False

        return True

    def _save_info(self, model_name: str, remarks: str, eval_model_name: str = None):
        """保存评估信息"""
        try:
            # 准备保存的数据
            info_data = {
                "model_name": model_name.strip(),
                "remarks": remarks.strip() if remarks else "",
                "eval_model_name": eval_model_name.strip() if eval_model_name else self.config.get('default_eval_model', 'siliconflow_deepseek_v3'),
                "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "updated_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 初始化FileManager并生成时间戳
            from utils.file_manager_singleton import get_file_manager
            file_manager = get_file_manager()
            timestamp = file_manager.start_new_test(model_name.strip())
            
            # 将时间戳保存到session state，确保整个会话使用同一个时间戳
            st.session_state.current_timestamp = timestamp
            st.session_state.timestamped_model_name = f"{model_name.strip()}{timestamp}"
            
            # 获取带时间戳的模型目录
            timestamped_model_dir = file_manager._get_timestamped_model_dir(model_name.strip())
            
            # 保存到带时间戳的模型目录
            info_file = timestamped_model_dir / "evaluation_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                safe_json_dump(info_data, f)
            
            # 如果是在文件上传界面中调用，设置标志以便继续流程
            if st.session_state.get('show_info_form_in_upload', False):
                st.session_state.ready_for_upload = True
            
            # 更新session state
            st.session_state.selected_model = model_name.strip()
            st.session_state.evaluation_info = info_data
            st.session_state.info_completed = True
            
            # 初始化FileManager并生成时间戳
            from utils.file_manager_singleton import get_file_manager
            file_manager = get_file_manager()
            timestamp = file_manager.start_new_test(model_name.strip())
            
            logger.info(f"评估信息保存成功: {model_name}, 时间戳: {timestamp}, 保存路径: {info_file}")
            
        except Exception as e:
            st.error(f"❌ 保存信息失败: {str(e)}")
            logger.error(f"保存评估信息失败: {e}")
    
    def _load_existing_info(self):
        """加载已存在的评估信息到session state"""
        try:
            # 如果session state中已有信息，直接返回
            if 'evaluation_info' in st.session_state:
                # 检查是否有时间戳，如果没有则需要初始化
                if not st.session_state.get('current_timestamp'):
                    model_name = st.session_state.get('selected_model', '')
                    if model_name:
                        from utils.file_manager_singleton import get_file_manager
                        file_manager = get_file_manager()
                        # 尝试找到现有的时间戳目录
                        latest_dir = file_manager.find_latest_timestamp_dir(model_name)
                        if latest_dir:
                            current_timestamp = file_manager.get_current_timestamp(model_name)
                            st.session_state.current_timestamp = current_timestamp
                            st.session_state.timestamped_model_name = f"{model_name}{current_timestamp}"
                            logger.info(f"使用现有时间戳: {current_timestamp}")
                        else:
                            # 只有在没有找到现有目录时才创建新的
                            timestamp = file_manager.start_new_test(model_name)
                            st.session_state.current_timestamp = timestamp
                            st.session_state.timestamped_model_name = f"{model_name}{timestamp}"
                            logger.info(f"创建新时间戳: {timestamp}")
                return
                
            from utils.file_manager_singleton import get_file_manager
            file_manager = get_file_manager()
            
            # 尝试从data目录中找到最新的评估信息
            data_dir = Path("data")
            if data_dir.exists():
                # 查找所有模型目录
                model_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
                if model_dirs:
                    # 按修改时间排序，获取最新的目录
                    latest_dir = max(model_dirs, key=lambda x: x.stat().st_mtime)
                    info_file = latest_dir / "evaluation_info.json"
                    
                    if info_file.exists():
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info_data = json.load(f)
                        
                        model_name = info_data.get('model_name', '')
                        if model_name:
                            # 设置时间戳信息
                            current_timestamp = file_manager.get_current_timestamp(model_name)
                            if not current_timestamp:
                                # 如果没有找到时间戳，从目录名中提取
                                dir_name = latest_dir.name
                                if len(dir_name) > len(model_name):
                                    current_timestamp = dir_name[len(model_name):]
                                    file_manager.current_timestamp = current_timestamp
                            
                            st.session_state.current_timestamp = current_timestamp
                            st.session_state.timestamped_model_name = f"{model_name}{current_timestamp}"
                            
                            # 设置session state
                            st.session_state.evaluation_info = info_data
                            st.session_state.selected_model = model_name
                            st.session_state.info_completed = True
                            
                            logger.info(f"从时间戳目录加载评估信息: {info_file}")
                            return
            
            # 如果data目录中没有找到，尝试从legacy位置加载（向后兼容）
            legacy_info_file = self.info_dir / "evaluation_info.json"
            if legacy_info_file.exists():
                with open(legacy_info_file, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                model_name = info_data.get('model_name', '')
                
                if model_name:
                    # 创建新的时间戳目录并迁移数据
                    timestamp = file_manager.start_new_test(model_name)
                    st.session_state.current_timestamp = timestamp
                    st.session_state.timestamped_model_name = f"{model_name}{timestamp}"
                    
                    # 将数据保存到新的时间戳目录
                    timestamped_dir = file_manager._get_timestamped_model_dir(model_name)
                    new_info_file = timestamped_dir / "evaluation_info.json"
                    with open(new_info_file, 'w', encoding='utf-8') as f:
                        safe_json_dump(info_data, f)
                    
                    # 设置session state
                    st.session_state.evaluation_info = info_data
                    st.session_state.selected_model = model_name
                    st.session_state.info_completed = True
                    
                    logger.info(f"从legacy目录迁移评估信息到: {new_info_file}")
                    
                    # 删除legacy文件
                    legacy_info_file.unlink()
                    logger.info("已删除legacy评估信息文件")
                
        except Exception as e:
            logger.error(f"加载评估信息失败: {e}")
    
    def _check_existing_info(self) -> bool:
        """检查是否已存在评估信息"""
        return st.session_state.get('info_completed', False) and st.session_state.get('evaluation_info') is not None
    
    def _display_existing_info(self):
        """显示已存在的评估信息"""
        try:
            # 从session state获取信息数据
            info_data = st.session_state.get('evaluation_info', {})
            
            # 显示信息卡片
            st.subheader("📋 当前评估信息")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 信息展示卡片
                with st.container():
                    st.markdown("""
                    <div style="
                        background-color: #f0f2f6;
                        padding: 1.5rem;
                        border-radius: 10px;
                        border-left: 4px solid #667eea;
                        margin-bottom: 1rem;
                    ">
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**🤖 被评估模型:** {info_data.get('model_name', 'N/A')}")
                    st.markdown(f"**📊 评估模型:** {info_data.get('eval_model_name', 'N/A')}")

                    # 显示当前会话的时间戳
                    current_timestamp = st.session_state.get('current_timestamp')
                    if current_timestamp:
                        timestamped_name = st.session_state.get('timestamped_model_name', f"{info_data.get('model_name', '')}{current_timestamp}")
                        st.markdown(f"**🕒 当前会话:** {timestamped_name}")

                    if info_data.get('remarks'):
                        st.markdown(f"**📝 备注信息:** {info_data.get('remarks')}")

                    st.markdown(f"**⏰ 创建时间:** {info_data.get('created_time', 'N/A')}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                # 操作按钮
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("✏️ 修改信息", use_container_width=True, key=f"{self.key_prefix}modify_info_button"):
                    self._modify_info()
                    st.rerun()
                
                if st.button("🗑️ 清除信息", use_container_width=True, type="secondary", key=f"{self.key_prefix}clear_info_button"):
                    if st.session_state.get('confirm_clear', False):
                        self._clear_info()
                        st.success("✅ 信息已清除")
                        st.rerun()
                    else:
                        st.session_state.confirm_clear = True
                        st.warning("⚠️ 再次点击确认清除")
            
            # 显示继续按钮
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📁 继续到文件上传", type="primary", use_container_width=True, key=f"{self.key_prefix}info_form_continue_button"):
                    st.success("✅ 信息确认完成，请切换到文件上传选项卡")
                    # 设置准备上传标志
                    st.session_state.ready_for_upload = True
                    # 如果是在文件上传界面中显示的信息填写表单，清除显示标志
                    if st.session_state.get('show_info_form_in_upload', False):
                        st.session_state.show_info_form_in_upload = False
                        st.rerun()
            
        except Exception as e:
            st.error(f"❌ 读取评估信息失败: {str(e)}")
            logger.error(f"读取评估信息失败: {e}")
    
    def _modify_info(self):
        """修改信息（保持当前时间戳，只清除界面状态）"""
        try:
            # 保存当前的时间戳信息，以便修改后仍保存到同一目录
            current_timestamp = st.session_state.get('current_timestamp')
            timestamped_model_name = st.session_state.get('timestamped_model_name')
            selected_model = st.session_state.get('selected_model')
            
            # 只清除界面相关的session state
            keys_to_clear = [
                'evaluation_info', 
                'info_completed', 
                'confirm_clear', 
                'ready_for_upload',
                'newly_uploaded_files',
                'selected_files'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 恢复时间戳信息，确保修改后的信息保存到同一目录
            if current_timestamp:
                st.session_state.current_timestamp = current_timestamp
            if timestamped_model_name:
                st.session_state.timestamped_model_name = timestamped_model_name
            if selected_model:
                st.session_state.selected_model = selected_model
            
            logger.info("进入修改模式，保持当前时间戳")
            
        except Exception as e:
            st.error(f"❌ 修改信息失败: {str(e)}")
            logger.error(f"修改评估信息失败: {e}")
    
    def _clear_info(self):
        """清除评估信息（完全重置，为新测试准备）"""
        try:
            # 完全清除所有session state，为新的测试做准备
            keys_to_clear = [
                'evaluation_info', 
                'info_completed', 
                'confirm_clear', 
                'ready_for_upload',
                'selected_model',
                'current_timestamp',
                'timestamped_model_name',
                'newly_uploaded_files',
                'selected_files'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            logger.info("评估信息已完全清除，准备开始新的测试")
            
        except Exception as e:
            st.error(f"❌ 清除信息失败: {str(e)}")
            logger.error(f"清除评估信息失败: {e}")
    
    def get_current_model(self) -> str:
        """获取当前选择的模型名称"""
        if hasattr(st.session_state, 'evaluation_info'):
            return st.session_state.evaluation_info.get('model_name', '')
        return st.session_state.get('selected_model', '')


def main():
    """测试信息填写界面"""
    st.set_page_config(
        page_title="信息填写测试",
        page_icon="📝",
        layout="wide"
    )
    
    interface = InformationFormInterface()
    interface.render()

if __name__ == "__main__":
    main()