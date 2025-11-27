#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
import time
import socket
import urllib.request
import urllib.error
import json
import traceback
from datetime import datetime

# Configuration
TEST_REPORT_FILE = "test_report.html"
REQUIRED_PYTHON_MAJOR = 3
REQUIRED_PYTHON_MINOR = 11
APP_HOST = "127.0.0.1"
APP_PORT = 8000
APP_URL = f"http://{APP_HOST}:{APP_PORT}"
REQUIREMENTS_FILE = "requirements.txt"
ENV_FILE = ".env"
ENV_EXAMPLE_FILE = ".env.example"

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{'='*40}")
    print(f"{msg}")
    print(f"{'='*40}{Colors.ENDC}")

def print_step(step, total, msg):
    print(f"\n[{step}/{total}] {Colors.BOLD}{msg}{Colors.ENDC}")

def print_success(msg):
    print(f"  ✅ {Colors.OKGREEN}{msg}{Colors.ENDC}")

def print_fail(msg):
    print(f"  ❌ {Colors.FAIL}{msg}{Colors.ENDC}")

def print_warn(msg):
    print(f"  ⚠️  {Colors.WARNING}{msg}{Colors.ENDC}")

def print_info(msg):
    print(f"  ℹ️  {msg}")

class TestRunner:
    def __init__(self):
        self.results = {
            "env_check": [],
            "dep_install": [],
            "env_config": [],
            "app_start": [],
            "api_test": [],
            "diagnostics": []
        }
        self.app_process = None
        self.start_time = time.time()
        self.api_key = None
        self.log_file = None

    def check_environment(self):
        print_step(1, 6, "环境检查 (Environment Check)")
        
        # Check Python Version
        v = sys.version_info
        version_str = f"{v.major}.{v.minor}.{v.micro}"
        if v.major == REQUIRED_PYTHON_MAJOR and v.minor >= REQUIRED_PYTHON_MINOR:
            self.results["env_check"].append(f"Python Version: {version_str}")
            print_success(f"Python 版本: {version_str}")
        else:
            msg = f"Python 版本不兼容: {version_str} (需要 {REQUIRED_PYTHON_MAJOR}.{REQUIRED_PYTHON_MINOR}+)"
            self.results["env_check"].append(msg)
            print_warn(msg) # Warn but try to proceed as 3.12 is likely fine if deps are compatible

        # Check pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
            self.results["env_check"].append("pip available")
            print_success("pip 可用")
        except subprocess.CalledProcessError:
            self.results["env_check"].append("pip missing")
            print_fail("pip 不可用")

        # Check requirements.txt
        if os.path.exists(REQUIREMENTS_FILE):
            self.results["env_check"].append("requirements.txt exists")
            print_success("requirements.txt 存在")
        else:
            self.results["env_check"].append("requirements.txt missing")
            print_fail("requirements.txt 不存在")
            sys.exit(1)

    def install_dependencies(self):
        print_step(2, 6, "依赖安装 (Dependency Installation)")
        
        # Check specific packages
        packages_to_check = ["tomli", "pydantic-settings"]
        missing_packages = []

        for pkg in packages_to_check:
            try:
                # Basic check by importing (handle hyphen to underscore)
                module_name = pkg.replace("-", "_")
                # pydantic-settings imports as pydantic_settings
                __import__(module_name)
                self.results["dep_install"].append(f"{pkg} installed")
                print_success(f"{pkg} 已安装")
            except ImportError:
                missing_packages.append(pkg)

        if missing_packages:
            print_info(f"安装缺失包: {', '.join(missing_packages)}")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install"] + missing_packages, check=True)
                for pkg in missing_packages:
                    self.results["dep_install"].append(f"{pkg} installed (auto)")
                    print_success(f"{pkg} 自动安装成功")
            except subprocess.CalledProcessError as e:
                print_fail(f"安装缺失包失败: {e}")
                self.results["dep_install"].append(f"Failed to install {missing_packages}")

        # Install all requirements
        print_info("运行 pip install -r requirements.txt ...")
        try:
            # Using capture_output=True to keep it clean unless error
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], check=True, capture_output=True)
            self.results["dep_install"].append("All dependencies installed")
            print_success("所有依赖已安装")
        except subprocess.CalledProcessError as e:
            print_fail("依赖安装失败")
            # Print stderr for debugging
            if e.stderr:
                print(e.stderr.decode())
            self.results["dep_install"].append("Dependency installation failed")

    def configure_environment(self):
        print_step(3, 6, "环境配置 (Configuration)")
        
        if os.path.exists(ENV_FILE):
            self.results["env_config"].append(".env exists")
            print_success(".env 已配置")
        else:
            if os.path.exists(ENV_EXAMPLE_FILE):
                shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)
                self.results["env_config"].append(".env created from example")
                print_warn(".env 不存在，已从 .env.example 复制")
            else:
                self.results["env_config"].append(".env and .env.example missing")
                print_fail(".env 和 .env.example 都不存在")
                return

        # Check and fix DATABASE_URL in .env
        # Read file lines
        try:
            with open(ENV_FILE, 'r') as f:
                lines = f.readlines()
            
            modified = False
            new_lines = []
            for line in lines:
                # Check for dummy value in .env.example
                if line.strip().startswith("DATABASE_URL=postgresql://user:password@host:port/dbname"):
                    new_lines.append(f"# {line}")
                    modified = True
                    print_info("自动注释掉示例 DATABASE_URL 以使用本地 SQLite")
                else:
                    new_lines.append(line)
            
            if modified:
                 with open(ENV_FILE, 'w') as f:
                    f.writelines(new_lines)
        except Exception as e:
            print_fail(f"无法自动修正 .env: {e}")

        # Load env vars to check critical ones
        env_vars = {}
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    env_vars[key.strip()] = val.strip()

        self.api_key = env_vars.get("API_KEY")
        
        required_vars = ["API_KEY"]
        missing_vars = [v for v in required_vars if v not in env_vars or not env_vars[v]]
        
        if not missing_vars:
            self.results["env_config"].append("Critical variables present")
            print_success("必需变量检查通过")
        else:
            msg = f"缺少必需变量: {', '.join(missing_vars)}"
            self.results["env_config"].append(msg)
            print_warn(msg)

    def start_app(self):
        print_step(4, 6, "应用启动 (Application Startup)")
        
        # Command to start uvicorn
        # We need to make sure we run python-multipart if needed, or just run the app module.
        # "uvicorn" executable might be in the venv bin, but calling python -m uvicorn is safer across platforms
        cmd = [sys.executable, "-m", "uvicorn", "src.main:app", "--host", APP_HOST, "--port", str(APP_PORT)]
        
        try:
            start_ts = time.time()
            # Open file for logs
            self.log_file = open("app_startup.log", "w")
            self.app_process = subprocess.Popen(
                cmd,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd()
            )
            
            # Wait for port to be open
            max_retries = 30
            for i in range(max_retries):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((APP_HOST, APP_PORT))
                sock.close()
                if result == 0:
                    startup_time = time.time() - start_ts
                    msg = f"FastAPI 启动成功 ({startup_time:.2f}s)"
                    self.results["app_start"].append(msg)
                    print_success(msg)
                    print_success(f"Uvicorn 监听 {APP_URL}")
                    return True
                
                if self.app_process.poll() is not None:
                    # Process died
                    print_fail("应用启动失败 (进程退出)")
                    self.results["app_start"].append("App process exited prematurely")
                    return False
                    
                time.sleep(1)
            
            print_fail("应用启动超时")
            self.results["app_start"].append("Startup timed out")
            return False

        except Exception as e:
            print_fail(f"启动异常: {e}")
            self.results["app_start"].append(f"Exception: {e}")
            return False

    def test_api(self):
        print_step(5, 6, "API 测试 (API Testing)")
        
        if not self.app_process or self.app_process.poll() is not None:
            print_fail("应用未运行，跳过 API 测试")
            return

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Helper for requests
        def make_request(endpoint, method="GET", data=None):
            url = f"{APP_URL}{endpoint}"
            try:
                req = urllib.request.Request(url, method=method, headers=headers)
                if data:
                    req.data = json.dumps(data).encode('utf-8')
                    req.add_header('Content-Type', 'application/json')
                
                with urllib.request.urlopen(req) as response:
                    return response.status, "OK"
            except urllib.error.HTTPError as e:
                return e.code, e.reason
            except urllib.error.URLError as e:
                return -1, str(e.reason)
            except Exception as e:
                return -1, str(e)

        # 1. Health check (fallback to root if 404)
        code, msg = make_request("/health")
        if code == 200:
            print_success("GET /health → 200")
            self.results["api_test"].append("GET /health: 200 OK")
        else:
             # Try root instead
            code_root, msg_root = make_request("/")
            if code_root == 200:
                 print_success("GET / → 200 (Health Check fallback)")
                 self.results["api_test"].append("GET /: 200 OK")
            else:
                 print_warn(f"GET /health → {code} {msg}")
                 self.results["api_test"].append(f"GET /health: {code} {msg}")

        # 2. /v1/models
        code, msg = make_request("/v1/models")
        if code == 200:
            print_success("GET /v1/models → 200")
            self.results["api_test"].append("GET /v1/models: 200 OK")
        else:
            print_fail(f"GET /v1/models → {code} {msg}")
            self.results["api_test"].append(f"GET /v1/models: {code} {msg}")

        # 3. /v1/chat/completions
        payload = {
            "model": "veo",
            "messages": [{"role": "user", "content": "test"}],
            "stream": False
        }
        code, msg = make_request("/v1/chat/completions", method="POST", data=payload)
        
        if code == 200:
            print_success("POST /v1/chat/completions → 200")
            self.results["api_test"].append("POST /v1/chat/completions: 200 OK")
        elif code == 503:
             print_warn(f"POST /v1/chat/completions → 503 ({msg}) - 可能缺少环境变量")
             self.results["api_test"].append(f"POST /v1/chat/completions: 503 {msg}")
        elif code == 500:
             print_warn(f"POST /v1/chat/completions → 500 ({msg}) - 可能是生成错误(正常)")
             self.results["api_test"].append(f"POST /v1/chat/completions: 500 {msg}")
        else:
             print_fail(f"POST /v1/chat/completions → {code} {msg}")
             self.results["api_test"].append(f"POST /v1/chat/completions: {code} {msg}")


    def generate_report(self):
        print_step(6, 6, "诊断报告 (Diagnostic Report)")
        
        # Cleanup
        if self.app_process:
            print_info("停止应用...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
            if self.log_file:
                self.log_file.close()

        # Summary
        app_started = any("启动成功" in s or "Startup successful" in s for s in self.results["app_start"]) or \
                      any("FastAPI 启动成功" in s for s in self.results["app_start"])
        
        if app_started:
            print_success("应用启动: 成功")
        else:
            print_fail("应用启动: 失败")

        # Report content
        html_content = f"""
        <html>
        <head>
            <title>Flow2API 自动化测试报告</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                h1 {{ color: #333; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
                .warn {{ color: orange; }}
                .section {{ margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }}
                ul {{ list-style-type: none; padding-left: 0; }}
                li {{ margin-bottom: 5px; }}
            </style>
        </head>
        <body>
            <h1>Flow2API 测试报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="section">
                <h2>环境检查</h2>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in self.results['env_check'])}
                </ul>
            </div>
            
            <div class="section">
                <h2>依赖安装</h2>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in self.results['dep_install'])}
                </ul>
            </div>
            
             <div class="section">
                <h2>环境配置</h2>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in self.results['env_config'])}
                </ul>
            </div>

             <div class="section">
                <h2>应用启动</h2>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in self.results['app_start'])}
                </ul>
            </div>

             <div class="section">
                <h2>API 测试</h2>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in self.results['api_test'])}
                </ul>
            </div>

            <div class="section">
                <h2>修复建议</h2>
                <ul>
                    {'<li>配置 FLOW_API_KEY 后重新测试</li>' if not self.api_key or self.api_key == "han1234" else ''}
                    {'<li>检查 app_startup.log 查看详细错误日志</li>' if not app_started else ''}
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open(TEST_REPORT_FILE, "w", encoding='utf-8') as f:
            f.write(html_content)
        
        print_info(f"建议: 检查 {TEST_REPORT_FILE} 获取详细信息")
        
        print_header(f"测试完成！报告已保存到: {TEST_REPORT_FILE}")

def ensure_venv():
    # Check if we are in a virtual environment
    # sys.prefix != sys.base_prefix is the standard way to check for venv
    is_venv = (sys.prefix != sys.base_prefix)
    if is_venv:
        return

    print_info("检测到未在虚拟环境中运行，正在自动配置虚拟环境...")
    
    venv_dir = os.path.join(os.getcwd(), ".venv")
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(venv_python):
        print_info(f"创建虚拟环境: {venv_dir}")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        except subprocess.CalledProcessError as e:
            print_fail(f"创建虚拟环境失败: {e}")
            sys.exit(1)
    
    print_info("在虚拟环境中重新启动脚本...")
    
    # Check if we should use the venv python to re-execute
    try:
        # Pass all arguments forward
        # Using subprocess.call to wait for it to finish, then exit
        ret = subprocess.call([venv_python] + sys.argv)
        sys.exit(ret)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except Exception as e:
        print_fail(f"无法重启脚本: {e}")
        sys.exit(1)

def main():
    print_header("Flow2API 本地部署自动化测试")
    
    # Ensure Venv
    ensure_venv()
    
    runner = TestRunner()
    
    try:
        runner.check_environment()
        runner.install_dependencies()
        runner.configure_environment()
        success = runner.start_app()
        if success:
            runner.test_api()
        runner.generate_report()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        if runner.app_process:
            runner.app_process.terminate()
    except Exception as e:
        print_fail(f"测试脚本发生意外错误: {e}")
        traceback.print_exc()
        if runner.app_process:
            runner.app_process.terminate()

if __name__ == "__main__":
    main()
