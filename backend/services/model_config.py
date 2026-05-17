"""
Hermes Model Config Manager
Manages model configurations from ~/.hermes/config.yaml
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ModelProfile:
    """Model profile configuration"""
    id: str
    name: str
    provider: str
    api_base_url: str
    api_key_env: str
    temperature: float = 0.7
    max_tokens: int = 2048
    configured: bool = False


class ModelConfigManager:
    """Manager for model configurations"""
    
    def __init__(self):
        self.hermes_config_path = Path.home() / ".hermes" / "config.yaml"
        self._builtin_models = self._get_builtin_models()
    
    def _get_builtin_models(self) -> Dict[str, ModelProfile]:
        """Get builtin model configurations"""
        return {
            'gpt-4o': ModelProfile(
                id='gpt-4o',
                name='GPT-4o',
                provider='openai',
                api_base_url='https://api.openai.com/v1',
                api_key_env='OPENAI_API_KEY'
            ),
            'gpt-4o-mini': ModelProfile(
                id='gpt-4o-mini',
                name='GPT-4o Mini',
                provider='openai',
                api_base_url='https://api.openai.com/v1',
                api_key_env='OPENAI_API_KEY'
            ),
            'gpt-3.5-turbo': ModelProfile(
                id='gpt-3.5-turbo',
                name='GPT-3.5 Turbo',
                provider='openai',
                api_base_url='https://api.openai.com/v1',
                api_key_env='OPENAI_API_KEY'
            ),
            'claude-3-5-sonnet': ModelProfile(
                id='claude-3-5-sonnet',
                name='Claude 3.5 Sonnet',
                provider='anthropic',
                api_base_url='https://api.anthropic.com/v1',
                api_key_env='ANTHROPIC_API_KEY'
            ),
            'claude-3-opus': ModelProfile(
                id='claude-3-opus',
                name='Claude 3 Opus',
                provider='anthropic',
                api_base_url='https://api.anthropic.com/v1',
                api_key_env='ANTHROPIC_API_KEY'
            ),
            'deepseek-chat': ModelProfile(
                id='deepseek-chat',
                name='DeepSeek Chat',
                provider='deepseek',
                api_base_url='https://api.deepseek.com/v1',
                api_key_env='DEEPSEEK_API_KEY'
            ),
            'deepseek-coder': ModelProfile(
                id='deepseek-coder',
                name='DeepSeek Coder',
                provider='deepseek',
                api_base_url='https://api.deepseek.com/v1',
                api_key_env='DEEPSEEK_API_KEY'
            ),
            'qwen-max': ModelProfile(
                id='qwen-max',
                name='通义千问 Max',
                provider='qwen',
                api_base_url='https://dashscope.aliyuncs.com/api/v1',
                api_key_env='QWEN_API_KEY'
            ),
            'qwen-plus': ModelProfile(
                id='qwen-plus',
                name='通义千问 Plus',
                provider='qwen',
                api_base_url='https://dashscope.aliyuncs.com/api/v1',
                api_key_env='QWEN_API_KEY'
            ),
            'glm-4': ModelProfile(
                id='glm-4',
                name='智谱 GLM-4',
                provider='zhipu',
                api_base_url='https://open.bigmodel.cn/api/paas/v4',
                api_key_env='ZHIPU_API_KEY'
            ),
        }
    
    def read_hermes_config(self) -> Dict:
        """Read Hermes config.yaml"""
        if not self.hermes_config_path.exists():
            return {}
        
        try:
            with open(self.hermes_config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[ModelConfig] Failed to read config: {e}")
            return {}
    
    def get_available_models(self) -> List[Dict]:
        """Get all available models from config.yaml + builtin"""
        models = {}
        
        # Load from Hermes config.yaml
        config = self.read_hermes_config()
        if 'models' in config:
            for model_id, model_config in config['models'].items():
                models[model_id] = {
                    'id': model_id,
                    'name': model_config.get('name', model_id),
                    'provider': model_config.get('provider', 'unknown'),
                    'api_base_url': model_config.get('api_base_url', ''),
                    'api_key_env': model_config.get('api_key_env', f"{model_id.upper()}_API_KEY"),
                    'temperature': model_config.get('temperature', 0.7),
                    'max_tokens': model_config.get('max_tokens', 2048),
                }
        
        # Merge with builtin models
        for model_id, profile in self._builtin_models.items():
            if model_id not in models:
                models[model_id] = {
                    'id': profile.id,
                    'name': profile.name,
                    'provider': profile.provider,
                    'api_base_url': profile.api_base_url,
                    'api_key_env': profile.api_key_env,
                    'temperature': profile.temperature,
                    'max_tokens': profile.max_tokens,
                }
        
        return list(models.values())
    
    def get_model_config(self, model_id: str) -> Optional[Dict]:
        """Get configuration for a specific model"""
        models = self.get_available_models()
        for model in models:
            if model['id'] == model_id:
                return model
        return None
    
    def add_custom_model(self, model_config: Dict) -> bool:
        """Add a custom model to config.yaml"""
        try:
            config = self.read_hermes_config()
            
            if 'models' not in config:
                config['models'] = {}
            
            model_id = model_config['id']
            config['models'][model_id] = {
                'name': model_config.get('name', model_id),
                'provider': model_config.get('provider', 'custom'),
                'api_base_url': model_config.get('api_base_url', ''),
                'api_key_env': model_config.get('api_key_env', f"{model_id.upper()}_API_KEY"),
                'temperature': model_config.get('temperature', 0.7),
                'max_tokens': model_config.get('max_tokens', 2048),
            }
            
            # Write back to config.yaml
            self.hermes_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.hermes_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            print(f"[ModelConfig] Failed to add model: {e}")
            return False
    
    def delete_custom_model(self, model_id: str) -> bool:
        """Delete a custom model from config.yaml"""
        try:
            config = self.read_hermes_config()
            
            if 'models' in config and model_id in config['models']:
                del config['models'][model_id]
                
                with open(self.hermes_config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
                return True
            return False
        except Exception as e:
            print(f"[ModelConfig] Failed to delete model: {e}")
            return False
    
    def get_default_model(self) -> str:
        """Get default model from Hermes config"""
        config = self.read_hermes_config()
        
        if 'model' in config:
            model_config = config['model']
            if 'default' in model_config:
                return model_config['default']
            if 'provider' in model_config:
                return model_config['provider']
        
        return 'deepseek-chat'


model_config_manager = ModelConfigManager()
