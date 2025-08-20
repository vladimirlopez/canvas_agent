"""Centralized configuration management for CanvasAgent."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class CanvasConfig:
    """Canvas API configuration."""
    base_url: str
    token: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 1.0

@dataclass 
class LLMConfig:
    """LLM configuration."""
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    timeout: int = 60
    max_tokens: int = 2000

@dataclass
class CacheConfig:
    """Caching configuration."""
    enabled: bool = True
    ttl_seconds: int = 300
    max_size: int = 1000

@dataclass
class AppConfig:
    """Application configuration."""
    canvas: CanvasConfig
    llm: LLMConfig
    cache: CacheConfig
    debug: bool = False
    log_level: str = "INFO"

class ConfigManager:
    """Centralized configuration manager."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[AppConfig] = None
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in standard locations."""
        search_paths = [
            Path.cwd() / "config.json",
            Path.cwd() / ".canvasagent.json", 
            Path.home() / ".canvasagent.json",
            Path(__file__).parent / "config.json"
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        return None
    
    def load_config(self) -> AppConfig:
        """Load configuration from file and environment."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config_dict = self._get_default_config()
        
        # Override with file config if exists
        if self.config_path and self.config_path.exists():
            with open(self.config_path) as f:
                file_config = json.load(f)
            config_dict = self._merge_config(config_dict, file_config)
        
        # Override with environment variables
        env_config = self._get_env_config()
        config_dict = self._merge_config(config_dict, env_config)
        
        # Create typed config
        self._config = AppConfig(
            canvas=CanvasConfig(**config_dict['canvas']),
            llm=LLMConfig(**config_dict['llm']),
            cache=CacheConfig(**config_dict['cache']),
            debug=config_dict['debug'],
            log_level=config_dict['log_level']
        )
        
        return self._config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'canvas': {
                'base_url': '',
                'token': '',
                'timeout': 30,
                'max_retries': 3,
                'rate_limit_delay': 1.0
            },
            'llm': {
                'model': 'llama3.2',
                'base_url': 'http://localhost:11434',
                'timeout': 60,
                'max_tokens': 2000
            },
            'cache': {
                'enabled': True,
                'ttl_seconds': 300,
                'max_size': 1000
            },
            'debug': False,
            'log_level': 'INFO'
        }
    
    def _get_env_config(self) -> Dict[str, Any]:
        """Extract configuration from environment variables."""
        config = {'canvas': {}, 'llm': {}, 'cache': {}}
        
        # Canvas config from env
        if os.getenv('CANVAS_BASE_URL'):
            config['canvas']['base_url'] = os.getenv('CANVAS_BASE_URL')
        if os.getenv('CANVAS_TOKEN') or os.getenv('CANVAS_API_TOKEN'):
            config['canvas']['token'] = os.getenv('CANVAS_TOKEN') or os.getenv('CANVAS_API_TOKEN')
        
        # LLM config from env  
        if os.getenv('LLM_MODEL'):
            config['llm']['model'] = os.getenv('LLM_MODEL')
        if os.getenv('LLM_BASE_URL'):
            config['llm']['base_url'] = os.getenv('LLM_BASE_URL')
        
        # App config from env
        if os.getenv('DEBUG'):
            config['debug'] = os.getenv('DEBUG').lower() in ('1', 'true', 'yes')
        if os.getenv('LOG_LEVEL'):
            config['log_level'] = os.getenv('LOG_LEVEL').upper()
        
        return config
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_config(self, config: AppConfig, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        save_path = path or self.config_path or Path.cwd() / "config.json"
        
        config_dict = {
            'canvas': {
                'base_url': config.canvas.base_url,
                'token': '***' if config.canvas.token else '',  # Don't save token
                'timeout': config.canvas.timeout,
                'max_retries': config.canvas.max_retries,
                'rate_limit_delay': config.canvas.rate_limit_delay
            },
            'llm': {
                'model': config.llm.model,
                'base_url': config.llm.base_url,
                'timeout': config.llm.timeout,
                'max_tokens': config.llm.max_tokens
            },
            'cache': {
                'enabled': config.cache.enabled,
                'ttl_seconds': config.cache.ttl_seconds,
                'max_size': config.cache.max_size
            },
            'debug': config.debug,
            'log_level': config.log_level
        }
        
        with open(save_path, 'w') as f:
            json.dump(config_dict, f, indent=2)

# Global config instance
_config_manager = ConfigManager()

def get_config() -> AppConfig:
    """Get the global application configuration."""
    return _config_manager.load_config()

def reload_config() -> AppConfig:
    """Reload configuration from files/environment."""
    _config_manager._config = None
    return _config_manager.load_config()
