import os
import subprocess
import sys
import time
import threading

def get_current_dir():
    return os.path.dirname(os.path.abspath(__file__))

def start_ollama_server():
    current_dir = get_current_dir()
    models_dir = os.path.join(current_dir, "modules")
    
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = models_dir
    print(f"设置 OLLAMA_MODELS 环境变量为: {models_dir}")
    
    ollama_exe = os.path.join(current_dir, "ollama.exe")
    if not os.path.exists(ollama_exe):
        print(f"错误: 找不到Ollama可执行文件: {ollama_exe}")
        return False
    
    print("正在启动Ollama服务...")
    server_process = subprocess.Popen(
        [ollama_exe, "serve"], 
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    time.sleep(3)
    return server_process.poll() is None

def start_model(model_name="gemma3:1b"):
    current_dir = get_current_dir()
    models_dir = os.path.join(current_dir, "modules")
    ollama_exe = os.path.join(current_dir, ".\\ollama\\ollama.exe")
    
    if not os.path.exists(ollama_exe):
        print(f"错误: 找不到Ollama可执行文件: {ollama_exe}")
        return False
    
    print(f"正在启动模型: {model_name}...")
    
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = models_dir
    
    try:
        subprocess.Popen(
            [ollama_exe, "run", model_name],
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return True
    except Exception as e:
        print(f"启动模型失败: {str(e)}")
        return False

def check_ollama_status():
    import requests
    
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except:
        return False

def main():
    if check_ollama_status():
        print("Ollama服务已经在运行")
    else:
        if not start_ollama_server():
            print("启动Ollama服务失败")
            return
    
    max_retries = 10
    for i in range(max_retries):
        if check_ollama_status():
            break
        print(f"等待Ollama服务启动... ({i+1}/{max_retries})")
        time.sleep(2)
    
    if not check_ollama_status():
        print("Ollama服务启动超时")
        return
    
    if start_model():
        print("Ollama服务和模型已成功启动")
    else:
        print("Ollama服务已启动，但模型启动失败")

if __name__ == "__main__":
    main()