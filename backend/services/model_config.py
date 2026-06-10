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
    """Manager for Hermes Agent model configurations"""
    
    def __init__(self):
        # Hermes Agent 配置文件位置
        self.hermes_dir = Path.home() / ".hermes"
        self.hermes_config_path = self.hermes_dir / "config.yaml"
    
    def read_hermes_config(self) -> Dict:
        """Read Hermes Agent config.yaml"""
        if not self.hermes_config_path.exists():
            # Create default Hermes config
            self.hermes_dir.mkdir(parents=True, exist_ok=True)
            default_config = {
                'model': {
                    'default': 'deepseek-v4-flash'
                },
                'models': {}
            }
            with open(self.hermes_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            return default_config
        
        try:
            with open(self.hermes_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                if 'models' not in config:
                    config['models'] = {}
                if 'model' not in config:
                    config['model'] = {}
                return config
        except Exception as e:
            print(f"[ModelConfig] Failed to read config: {e}")
            return {'model': {'default': ''}, 'models': {}}
    
    def get_available_models(self) -> List[Dict]:
        """Get all available models from config.yaml"""
        models = {}
        config = self.read_hermes_config()
        
        # Load from models field (old format)
        if 'models' in config and config['models']:
            for model_id, model_config in config['models'].items():
                models[model_id] = {
                    'id': model_id,
                    'name': model_config.get('name', model_id),
                    'provider': model_config.get('provider', 'custom'),
                    'api_base_url': model_config.get('api_base_url', ''),
                    'api_key_env': model_config.get('api_key_env', f"{model_id.upper().replace('-', '_')}_API_KEY"),
                    'temperature': model_config.get('temperature', 0.7),
                    'max_tokens': model_config.get('max_tokens', 2048),
                }
        
        # Also check current model from model.default field
        current_model = config.get('model', {}).get('default', '')
        current_provider = config.get('model', {}).get('provider', '')
        
        # If current model is set but not in models list, add it
        if current_model and current_model not in models:
            models[current_model] = {
                'id': current_model,
                'name': current_model,
                'provider': current_provider or 'custom',
                'api_base_url': '',
                'api_key_env': f"{current_model.upper().replace('-', '_')}_API_KEY",
                'temperature': 0.7,
                'max_tokens': 2048,
            }
        
        # If no models found, check providers field (new v0.14.0 format)
        if not models and 'providers' in config:
            providers = config['providers']
            if providers and isinstance(providers, dict):
                for provider_name, provider_config in providers.items():
                    model_id = provider_config.get('model', provider_name)
                    models[model_id] = {
                        'id': model_id,
                        'name': provider_config.get('name', model_id),
                        'provider': provider_name,
                        'api_base_url': provider_config.get('api_base_url', ''),
                        'api_key_env': provider_config.get('api_key_env', f"{model_id.upper().replace('-', '_')}_API_KEY"),
                        'temperature': provider_config.get('temperature', 0.7),
                        'max_tokens': provider_config.get('max_tokens', 2048),
                    }
        
        # If still no models, create default from current model
        if not models and current_model:
            models[current_model] = {
                'id': current_model,
                'name': current_model,
                'provider': current_provider or 'custom',
                'api_base_url': '',
                'api_key_env': f"{current_model.upper().replace('-', '_')}_API_KEY",
                'temperature': 0.7,
                'max_tokens': 2048,
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
        """Add a model to Hermes Agent config.yaml"""
        try:
            config = self.read_hermes_config()
            
            if 'models' not in config:
                config['models'] = {}
            
            model_id = model_config['id']
            config['models'][model_id] = {
                'name': model_config.get('name', model_id),
                'provider': model_config.get('provider', 'custom'),
                'api_base_url': model_config.get('api_base_url', ''),
                'api_key_env': model_config.get('api_key_env', f"{model_id.upper().replace('-', '_')}_API_KEY"),
                'temperature': model_config.get('temperature', 0.7),
                'max_tokens': model_config.get('max_tokens', 2048),
            }
            
            # 如果是第一个模型，设为默认
            if len(config['models']) == 1:
                if 'model' not in config:
                    config['model'] = {}
                config['model']['default'] = model_id
            
            # Write back to config.yaml
            self.hermes_dir.mkdir(parents=True, exist_ok=True)
            with open(self.hermes_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"[ModelConfig] Added model {model_id} to Hermes config")
            return True
        except Exception as e:
            print(f"[ModelConfig] Failed to add model: {e}")
            return False
    
    def delete_custom_model(self, model_id: str) -> bool:
        """Delete a model from Hermes Agent config.yaml"""
        try:
            config = self.read_hermes_config()
            
            if 'models' in config and model_id in config['models']:
                del config['models'][model_id]
                
                # 如果删除的是默认模型，更新默认值
                if 'model' in config and config['model'].get('default') == model_id:
                    # 选择下一个可用模型作为默认
                    remaining = list(config.get('models', {}).keys())
                    config['model']['default'] = remaining[0] if remaining else ''
                
                with open(self.hermes_config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
                print(f"[ModelConfig] Deleted model {model_id} from Hermes config")
                return True
            return False
        except Exception as e:
            print(f"[ModelConfig] Failed to delete model: {e}")
            return False
    
    def set_default_model(self, model_id: str) -> bool:
        """Set default model for Hermes Agent — also syncs provider and base_url"""
        try:
            config = self.read_hermes_config()
            
            if 'model' not in config:
                config['model'] = {}
            
            config['model']['default'] = model_id
            
            # Sync provider and base_url from models block
            models = config.get('models', {})
            if model_id in models:
                model_info = models[model_id]
                config['model']['provider'] = model_info.get('provider', '')
                config['model']['base_url'] = model_info.get('api_base_url', '')
                print(f"[ModelConfig] Synced provider={model_info.get('provider')} base_url={model_info.get('api_base_url')}")
            
            with open(self.hermes_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"[ModelConfig] Set default model to {model_id}")
            return True
        except Exception as e:
            print(f"[ModelConfig] Failed to set default model: {e}")
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
        
        return 'deepseek-v4-flash'


model_config_manager = ModelConfigManager()
