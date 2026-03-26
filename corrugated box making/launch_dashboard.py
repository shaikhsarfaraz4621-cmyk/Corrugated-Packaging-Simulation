import os
import sys
import subprocess

if __name__ == "__main__":
    # Get the absolute directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    print("🚀 Booting Corrugated Factory Digital Twin...")
    print(f"Targeting: {app_path}")
    
    # Use python's executable to run the streamlit module
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
