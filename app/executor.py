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
    def run(self, code: str, obj_base64: Optional[str], language: str) -> Dict[str, Any]:
        raise NotImplementedError

class PythonRunner(BaseRunner):
    def run(self, code: str, obj_base64: Optional[str], language: str) -> Dict[str, Any]:
        allowed = config["runtimes"].get(language, {}).get("allowed_packages", [])
        error = SecurityChecker.check_python_imports(code, allowed)
        if error:
            return {"stdout": "", "error": error, "success": False}

        cmd = config["runtimes"].get(language, {}).get("command", "python3")
        indented_code = "\n    ".join(code.splitlines())
        wrapper_script = """
import base64
import json
import sys

def run_user_code():
    # 用户定义的代码
    {user_code}
    
    obj_base64 = "{obj_b64}"
    obj = None
    if obj_base64:
        try:
            decoded = base64.b64decode(obj_base64).decode('utf-8')
            obj = json.loads(decoded)
        except Exception as e:
            print(f"Error decoding input: {e}", file=sys.stderr)
            return

    # 调用 main(obj)
    if 'main' in locals():
        try:
            result = main(obj)
            if result is not None:
                print(result)
        except Exception as e:
            print(f"Error in main(obj): {e}", file=sys.stderr)
            raise e
    else:
        # 如果没有 main 函数，直接执行的代码已经运行了
        pass

if __name__ == "__main__":
    run_user_code()
""".replace("{user_code}", indented_code).replace("{obj_b64}", obj_base64 or "")
        return self._execute_subprocess([cmd, "-c", wrapper_script], is_nodejs=False)

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

class NodeJSRunner(BaseRunner):
    def run(self, code: str, obj_base64: Optional[str], language: str) -> Dict[str, Any]:
        allowed = config["runtimes"].get(language, {}).get("allowed_packages", [])
        error = SecurityChecker.check_nodejs_imports(code, allowed)
        if error:
            return {"stdout": "", "error": error, "success": False}

        cmd = config["runtimes"].get(language, {}).get("command", "node")
        wrapper_script = """
const base64 = "{obj_b64}";
let obj = null;
if (base64) {
    try {
        obj = JSON.parse(Buffer.from(base64, 'base64').toString('utf-8'));
    } catch (e) {
        process.stderr.write("Error decoding input: " + e + "\\n");
    }
}

// 用户代码
{user_code}

async function run() {
    if (typeof main === 'function') {
        try {
            const result = await main(obj);
            if (result !== undefined) console.log(result);
        } catch (e) {
            process.stderr.write("Error in main(obj): " + e + "\\n");
            process.exit(1);
        }
    }
}
run();
""".replace("{user_code}", code).replace("{obj_b64}", obj_base64 or "")
        return self._execute_subprocess([cmd, "-e", wrapper_script], is_nodejs=True)

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

class ExecutorFactory:
    @staticmethod
    def get_runner(language: str) -> BaseRunner:
        if language.startswith("python"):
            return PythonRunner()
        elif language == "nodejs":
            return NodeJSRunner()
        else:
            raise ValueError(f"Unsupported language: {language}")
