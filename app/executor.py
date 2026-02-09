import sys
import io
import traceback
import multiprocessing
import resource
import os
import signal
import base64
import json
import subprocess
import ast
import re
from typing import Dict, Any, Optional, List, Set
from .config import config

def set_resource_limits(is_nodejs=False):
    limits = config["resource_limits"]
    cpu_limit = limits["cpu_time_limit"]
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 2))
    
    # 调大内存限制以适应多语言运行时
    mem_limit = max(limits["memory_limit_mb"], 1024) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    
    file_limit = limits["file_size_limit_kb"] * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
    
    if not is_nodejs:
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))

class SecurityChecker:
    @staticmethod
    def check_python_imports(code: str, allowed: List[str]) -> Optional[str]:
        try:
            tree = ast.parse(code)
            allowed_set = set(allowed)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_module = alias.name.split('.')[0]
                        if base_module not in allowed_set:
                            return f"Unsupported package: {base_module}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base_module = node.module.split('.')[0]
                        if base_module not in allowed_set:
                            return f"Unsupported package: {base_module}"
            return None
        except Exception as e:
            return f"Code syntax error: {str(e)}"

    @staticmethod
    def check_nodejs_imports(code: str, allowed: List[str]) -> Optional[str]:
        allowed_set = set(allowed)
        # 匹配 require, import, 动态 import
        require_matches = re.findall(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", code)
        import_matches = re.findall(r"from\s*['\"]([^'\"]+)['\"]", code)
        dynamic_import_matches = re.findall(r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", code)
        
        all_imports = set(require_matches + import_matches + dynamic_import_matches)
        for pkg in all_imports:
            base_module = pkg.split('/')[0]
            if base_module not in allowed_set:
                return f"Unsupported package: {base_module}"
        return None

class BaseRunner:
    def run(self, code: str, language: str) -> Dict[str, Any]:
        raise NotImplementedError

    def _execute_subprocess(self, args, is_nodejs=False):
        timeout = config["resource_limits"]["timeout"]
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=lambda: set_resource_limits(is_nodejs)
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return {
                "stdout": stdout,
                "error": stderr,
                "success": process.returncode == 0
            }
        except subprocess.TimeoutExpired:
            process.kill()
            return {"stdout": "", "error": "Timeout", "success": False}
        except Exception as e:
            return {"stdout": "", "error": str(e), "success": False}

class PythonRunner(BaseRunner):
    def run(self, code: str, language: str) -> Dict[str, Any]:
        allowed = config["runtimes"].get(language, {}).get("allowed_packages", [])
        error = SecurityChecker.check_python_imports(code, allowed)
        if error:
            return {"stdout": "", "error": error, "success": False}

        cmd = config["runtimes"].get(language, {}).get("command", "python3")
        # 直接执行用户代码，不再进行包装
        return self._execute_subprocess([cmd, "-c", code], is_nodejs=False)

class NodeJSRunner(BaseRunner):
    def run(self, code: str, language: str) -> Dict[str, Any]:
        allowed = config["runtimes"].get(language, {}).get("allowed_packages", [])
        error = SecurityChecker.check_nodejs_imports(code, allowed)
        if error:
            return {"stdout": "", "error": error, "success": False}

        cmd = config["runtimes"].get(language, {}).get("command", "node")
        # 直接执行用户代码
        return self._execute_subprocess([cmd, "-e", code], is_nodejs=True)

class ExecutorFactory:
    @staticmethod
    def get_runner(language: str) -> BaseRunner:
        if language.startswith("python"):
            return PythonRunner()
        elif language == "nodejs":
            return NodeJSRunner()
        else:
            raise ValueError(f"Unsupported language: {language}")
