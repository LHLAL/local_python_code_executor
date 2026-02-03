import yaml
import os

DEFAULT_CONFIG = {
    "server": {
        "port": 8000,
        "workers": 4,
        "max_concurrent_requests": 10,
        "max_queue_size": 20
    },
    "resource_limits": {
        "cpu_time_limit": 10,
        "memory_limit_mb": 256,
        "file_size_limit_kb": 1024,
        "timeout": 10
    }
}

def load_config():
    config_path = os.getenv("SANDBOX_CONFIG_PATH", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
            # 深度合并或简单覆盖
            for key, value in user_config.items():
                if key in DEFAULT_CONFIG and isinstance(value, dict):
                    DEFAULT_CONFIG[key].update(value)
                else:
                    DEFAULT_CONFIG[key] = value
    return DEFAULT_CONFIG

config = load_config()
