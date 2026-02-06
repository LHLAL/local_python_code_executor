import yaml
import os
import copy

# 针对 Python 3.10 环境优化的默认配置
DEFAULT_CONFIG = {
    "server": {
        "port": 8000,
        "workers": 4,
        "max_concurrent_requests": 10,
        "max_queue_size": 20
    },
    "runtimes": {
        "python3": {
            "command": "/usr/bin/python3",
            "enabled": True,
            "allowed_packages": ["json", "base64", "math", "time", "requests", "re", "ast"]
        },
        "python310": {
            "command": "/usr/bin/python3",
            "enabled": True,
            "allowed_packages": ["json", "base64", "math", "time", "requests"]
        },
        "nodejs": {
            "command": "/usr/bin/node",
            "enabled": True,
            "allowed_packages": ["fs", "path", "crypto", "buffer", "util"]
        }
    },
    "resource_limits": {
        "cpu_time_limit": 10,
        "memory_limit_mb": 512,
        "file_size_limit_kb": 1024,
        "timeout": 10
    }
}

def load_config():
    final_config = copy.deepcopy(DEFAULT_CONFIG)
    config_path = os.getenv("SANDBOX_CONFIG_PATH", "config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    merge_configs(final_config, user_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}. Using defaults.")
    return final_config

def merge_configs(base, override):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_configs(base[key], value)
        else:
            base[key] = value

config = load_config()
