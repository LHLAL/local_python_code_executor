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
from typing import Dict, Any, Optional
from .config import config

def set_resource_limits(is_nodejs=False):
    limits = config["resource_limits"]
    cpu_limit = limits["cpu_time_limit"]
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 2))
    
    # Node.js 22 在 Linux 下需要较大的虚拟内存空间来预留 CodeRange
    mem_limit = max(limits["memory_limit_mb"], 1024) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    
    file_limit = limits["file_size_limit_kb"] * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
    
    if not is_nodejs:
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))

class BaseRunner:
    def run(self, code: str, obj_base64: Optional[str], runtime: str) -> Dict[str, Any]:
        raise NotImplementedError

class PythonRunner(BaseRunner):
    def run(self, code: str, obj_base64: Optional[str], runtime: str) -> Dict[str, Any]:
        cmd = config["runtimes"].get(runtime, {}).get("command", "python3")
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
        print("Warning: main(obj) not found in code", file=sys.stderr)

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
    def run(self, code: str, obj_base64: Optional[str], runtime: str) -> Dict[str, Any]:
        cmd = config["runtimes"].get(runtime, {}).get("command", "node")
        # 移除双花括号，使用 replace 注入
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
    } else {
        process.stderr.write("Warning: main(obj) not found\\n");
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
    def get_runner(runtime: str) -> BaseRunner:
        if runtime.startswith("python"):
            return PythonRunner()
        elif runtime == "nodejs":
            return NodeJSRunner()
        else:
            raise ValueError(f"Unsupported runtime: {runtime}")
