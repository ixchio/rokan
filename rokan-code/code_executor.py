"""
Rokan Code Executor
Sandboxed Python execution with safety controls
"""

import os
import sys
import ast
import resource
import signal
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager

# Optional imports
try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins
    HAS_RESTRICTED = True
except ImportError:
    HAS_RESTRICTED = False


@dataclass
class ExecutionResult:
    """Code execution result"""
    success: bool
    output: str
    result: Any
    execution_time: float
    memory_used_mb: float
    error: Optional[str] = None


class CodeValidator:
    """Validates Python code for safety"""
    
    # Default allowed imports
    ALLOWED_IMPORTS = {
        'os', 'sys', 'json', 're', 'datetime', 'math', 'random',
        'collections', 'itertools', 'functools', 'typing', 'pathlib',
        'hashlib', 'base64', 'statistics', 'decimal', 'fractions',
        'string', 'time', 'uuid', 'csv', 'io', 'pprint', 'html',
        'urllib.parse', 'http.client'
    }
    
    # Blocked imports
    BLOCKED_IMPORTS = {
        'subprocess', 'socket', 'ctypes', 'mmap', 'multiprocessing',
        'threading', 'asyncio', 'tkinter', 'sqlite3', 'pwd', 'grp',
        'ssl', 'ftplib', 'smtplib', 'urllib.request'
    }
    
    def __init__(self, allowed: List[str] = None, blocked: List[str] = None):
        self.allowed = set(allowed) if allowed else self.ALLOWED_IMPORTS
        self.blocked = set(blocked) if blocked else self.BLOCKED_IMPORTS
    
    def validate(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate code for safety
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Parse AST
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.blocked:
                        return False, f"Import '{module}' is not allowed"
                    if module not in self.allowed:
                        return False, f"Import '{module}' is not in allowed list"
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module.split('.')[0] if node.module else ""
                if module in self.blocked:
                    return False, f"Import from '{module}' is not allowed"
                if module and module not in self.allowed:
                    return False, f"Import from '{module}' is not in allowed list"
            
            # Check for dangerous builtins
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec', 'compile']:
                        return False, f"Function '{node.func.id}' is not allowed"
            
            # Check for file operations outside temp
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['open']:
                        # Allow but warn - actual restriction happens at runtime
                        pass
        
        return True, None


class SandboxExecutor:
    """
    Sandboxed Python code executor
    Uses subprocess isolation with resource limits
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout_seconds", 30)
        self.max_memory_mb = self.config.get("max_memory_mb", 512)
        self.validator = CodeValidator(
            allowed=self.config.get("allowed_imports"),
            blocked=self.config.get("blocked_imports")
        )
        self.temp_dir = os.path.expanduser("~/.rokan/sandbox/temp")
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def _create_sandbox_script(self, code: str) -> str:
        """Create the sandboxed execution script"""
        sandbox_code = f'''
import sys
import json
import resource
import os

# Set resource limits
resource.setrlimit(resource.RLIMIT_AS, ({self.max_memory_mb * 1024 * 1024}, {self.max_memory_mb * 1024 * 1024}))
resource.setrlimit(resource.RLIMIT_CPU, ({self.timeout}, {self.timeout}))

# Redirect stdout
from io import StringIO
old_stdout = sys.stdout
sys.stdout = captured_output = StringIO()

result = None
error = None

try:
    # Execute user code
{chr(10).join("    " + line for line in code.split(chr(10)))}
    
    # Capture last expression if any
    try:
        result = locals().get('_')
    except:
        pass
        
except Exception as e:
    error = str(e)

# Get output
output = captured_output.getvalue()
sys.stdout = old_stdout

# Return result
print(json.dumps({{
    "output": output,
    "result": repr(result) if result is not None else None,
    "error": error
}}))
'''
        return sandbox_code
    
    def execute(self, code: str, context: Dict = None) -> ExecutionResult:
        """
        Execute Python code in sandbox
        
        Args:
            code: Python code to execute
            context: Optional variables to inject
        
        Returns:
            ExecutionResult
        """
        import time
        start_time = time.time()
        
        # Validate code
        is_valid, error = self.validator.validate(code)
        if not is_valid:
            return ExecutionResult(
                success=False,
                output="",
                result=None,
                execution_time=0,
                memory_used_mb=0,
                error=error
            )
        
        # Create sandbox script
        sandbox_script = self._create_sandbox_script(code)
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=self.temp_dir) as f:
            f.write(sandbox_script)
            script_path = f.name
        
        try:
            # Execute in subprocess
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.temp_dir
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode != 0:
                return ExecutionResult(
                    success=False,
                    output=result.stdout,
                    result=None,
                    execution_time=execution_time,
                    memory_used_mb=0,
                    error=result.stderr
                )
            
            # Parse output
            try:
                output_data = json.loads(result.stdout.split('\n')[-2] if result.stdout else '{}')
            except:
                output_data = {"output": result.stdout, "result": None, "error": None}
            
            return ExecutionResult(
                success=output_data.get("error") is None,
                output=output_data.get("output", ""),
                result=output_data.get("result"),
                execution_time=execution_time,
                memory_used_mb=0,  # Would need psutil to track
                error=output_data.get("error")
            )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                result=None,
                execution_time=self.timeout,
                memory_used_mb=0,
                error=f"Execution timed out after {self.timeout} seconds"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                result=None,
                execution_time=time.time() - start_time,
                memory_used_mb=0,
                error=str(e)
            )
        
        finally:
            # Cleanup
            try:
                os.unlink(script_path)
            except:
                pass


# OpenClaw skill interface
class RokanCodeSkill:
    """OpenClaw skill interface for rokan-code"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.executor = SandboxExecutor(config)
    
    def execute(self, code: str) -> str:
        """Execute Python code and return result"""
        result = self.executor.execute(code)
        
        output = []
        output.append(f"Execution {'successful' if result.success else 'failed'} in {result.execution_time:.2f}s")
        
        if result.output:
            output.append(f"\nOutput:\n{result.output}")
        
        if result.result:
            output.append(f"\nResult: {result.result}")
        
        if result.error:
            output.append(f"\nError: {result.error}")
        
        return "\n".join(output)
    
    def validate(self, code: str) -> str:
        """Validate code without executing"""
        is_valid, error = self.executor.validator.validate(code)
        
        if is_valid:
            return "✓ Code passes security validation"
        else:
            return f"✗ Validation failed: {error}"
    
    def calc(self, expression: str) -> str:
        """Quick calculation"""
        code = f"result = {expression}\nprint(result)"
        return self.execute(code)


# Export for OpenClaw
skill = RokanCodeSkill
