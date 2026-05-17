"""
Hermes .env File Manager
Manages API keys and environment variables in ~/.hermes/.env
"""
import os
from pathlib import Path
from typing import Dict, Optional


class EnvManager:
    """Manager for ~/.hermes/.env file"""
    
    def __init__(self):
        self.hermes_dir = Path.home() / ".hermes"
        self.env_file = self.hermes_dir / ".env"
        self._ensure_env_file()
    
    def _ensure_env_file(self):
        """Ensure .env file exists"""
        self.hermes_dir.mkdir(parents=True, exist_ok=True)
        if not self.env_file.exists():
            self.env_file.touch()
    
    def read_env(self) -> Dict[str, str]:
        """Read all environment variables from .env file"""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars
    
    def write_env(self, env_vars: Dict[str, str]):
        """Write environment variables to .env file"""
        existing = self.read_env()
        existing.update(env_vars)
        
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write("# Hermes Environment Variables\n")
            f.write("# API Keys for different models\n\n")
            for key, value in sorted(existing.items()):
                if value:
                    f.write(f"{key}={value}\n")
    
    def get_api_key(self, model_id: str) -> Optional[str]:
        """Get API key for a specific model"""
        env_vars = self.read_env()
        
        # Map model to env key
        env_key_map = {
            'gpt-4o': 'OPENAI_API_KEY',
            'gpt-4o-mini': 'OPENAI_API_KEY',
            'gpt-3.5-turbo': 'OPENAI_API_KEY',
            'claude-3-5-sonnet': 'ANTHROPIC_API_KEY',
            'claude-3-opus': 'ANTHROPIC_API_KEY',
            'deepseek-chat': 'DEEPSEEK_API_KEY',
            'deepseek-coder': 'DEEPSEEK_API_KEY',
            'qwen-max': 'QWEN_API_KEY',
            'qwen-plus': 'QWEN_API_KEY',
            'glm-4': 'ZHIPU_API_KEY',
        }
        
        env_key = env_key_map.get(model_id)
        if env_key:
            return env_vars.get(env_key)
        
        # Try generic pattern: MODELNAME_API_KEY
        generic_key = f"{model_id.upper().replace('-', '_')}_API_KEY"
        return env_vars.get(generic_key)
    
    def set_api_key(self, model_id: str, api_key: str):
        """Set API key for a specific model"""
        env_key_map = {
            'gpt-4o': 'OPENAI_API_KEY',
            'gpt-4o-mini': 'OPENAI_API_KEY',
            'gpt-3.5-turbo': 'OPENAI_API_KEY',
            'claude-3-5-sonnet': 'ANTHROPIC_API_KEY',
            'claude-3-opus': 'ANTHROPIC_API_KEY',
            'deepseek-chat': 'DEEPSEEK_API_KEY',
            'deepseek-coder': 'DEEPSEEK_API_KEY',
            'qwen-max': 'QWEN_API_KEY',
            'qwen-plus': 'QWEN_API_KEY',
            'glm-4': 'ZHIPU_API_KEY',
        }
        
        env_key = env_key_map.get(model_id)
        if not env_key:
            env_key = f"{model_id.upper().replace('-', '_')}_API_KEY"
        
        self.write_env({env_key: api_key})
    
    def mask_api_key(self, api_key: str) -> str:
        """Mask API key for display (show first 3 and last 2 chars)"""
        if not api_key or len(api_key) < 6:
            return "****"
        return f"{api_key[:3]}{'*' * (len(api_key) - 5)}{api_key[-2:]}"
    
    def has_api_key(self, model_id: str) -> bool:
        """Check if API key exists for a model"""
        api_key = self.get_api_key(model_id)
        return bool(api_key and api_key.strip())


env_manager = EnvManager()
