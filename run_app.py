import subprocess
import sys
import time
import os
from pathlib import Path

def main():
    print("==========================================================")
    print(" 📡 Launching Network Health-Check and Alarm Triage Agent")
    print("==========================================================")
    
    BASE_DIR = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR) + (os.pathsep + env.get("PYTHONPATH", ""))
    
    # 1. Start FastAPI REST API backend with uvicorn
    print("\n[1/2] Starting FastAPI REST API backend on http://localhost:8000 ...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(2)
    
    # 2. Start Streamlit UI
    print("\n[2/2] Starting Streamlit Interactive Dashboard on http://localhost:8501 ...")
    ui_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "ui/app.py", "--server.port", "8501"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    print("\n✅ System running successfully!")
    print(" - Streamlit Dashboard: http://localhost:8501")
    print(" - FastAPI OpenAPI Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop servers.\n")
    
    try:
        api_process.wait()
        ui_process.wait()
    except KeyboardInterrupt:
        print("\nStopping application processes...")
        api_process.terminate()
        ui_process.terminate()
        print("Application stopped cleanly.")

if __name__ == "__main__":
    main()
