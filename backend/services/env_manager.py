"""
Hermes .env File Manager
Manages API keys and environment variables in ~/.hermes/.env
"""
import os
from pathlib import Path
from typing import Dict, Optional


class EnvManager:
    """Manager for Hermes Agent .env file"""
    
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
    
    def _get_env_key_for_model(self, model_id: str, api_key_env: str = None) -> str:
        """Get environment variable key for a model"""
        # If api_key_env is specified in model config, use it
        if api_key_env:
            return api_key_env
        
        # Otherwise, generate from model_id
        # Example: deepseek-chat -> DEEPSEEK_CHAT_API_KEY
        # Example: gpt-4o -> GPT_4O_API_KEY
        return f"{model_id.upper().replace('-', '_')}_API_KEY"
    
    def get_api_key(self, model_id: str, api_key_env: str = None) -> Optional[str]:
        """Get API key for a specific model"""
        # First try to read from .env file
        env_vars = self.read_env()
        env_key = self._get_env_key_for_model(model_id, api_key_env)
        
        if env_key in env_vars:
            return env_vars[env_key]
        
        # Fallback: read from Hermes config.yaml (model.api_key field)
        try:
            import yaml
            config_path = self.hermes_dir / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    
                # Check if this is the current model
                current_model = config.get('model', {}).get('default', '')
                if current_model == model_id:
                    api_key = config.get('model', {}).get('api_key', '')
                    if api_key:
                        return api_key
        except Exception:
            pass
        
        return None
    
    def set_api_key(self, model_id: str, api_key: str, api_key_env: str = None):
        """Set API key for a specific model"""
        env_key = self._get_env_key_for_model(model_id, api_key_env)
        self.write_env({env_key: api_key})
    
    def mask_api_key(self, api_key: str) -> str:
        """Mask API key for display (show first 3 and last 2 chars)"""
        if not api_key or len(api_key) < 6:
            return "****"
        return f"{api_key[:3]}{'*' * (len(api_key) - 5)}{api_key[-2:]}"
    
    def delete_api_key(self, model_id: str, api_key_env: str = None):
        """Delete API key for a specific model"""
        env_key = self._get_env_key_for_model(model_id, api_key_env)
        
        # Read existing env vars
        env_vars = self.read_env()
        
        # Remove the key
        if env_key in env_vars:
            del env_vars[env_key]
            
            # Write back
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# Hermes Environment Variables\n")
                f.write("# API Keys for different models\n\n")
                for key, value in sorted(env_vars.items()):
                    if value:
                        f.write(f"{key}={value}\n")
        
        return True
    
    def has_api_key(self, model_id: str, api_key_env: str = None) -> bool:
        """Check if API key exists for a model"""
        api_key = self.get_api_key(model_id, api_key_env)
        return bool(api_key and api_key.strip())


env_manager = EnvManager()
