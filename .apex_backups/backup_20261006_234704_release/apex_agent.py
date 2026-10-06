import sys
import os
import time
import json
import subprocess
import traceback


class ApexAIAgent:
    def __init__(self, memory_file="agent_memory.json"):
        self.memory_file = memory_file
        self.memory = self.load_memory()
        print("⚡ APEX AI Agent Workflow Orchestrator Initialized.")

    def load_memory(self):
        """خوێندنەوەی بیرگەی ئەیجێنتەکە"""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"fixed_errors": [], "logs": []}

    def save_memory(self):
        """پاشەکەوتکردنی زانیاری لە بیرگەدا"""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=4, ensure_ascii=False)

    def log_event(self, event_type, details):
        """تۆمارکردنی رووداوەکان لە بیرگەدا"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": event_type,
            "details": str(details),
        }
        self.memory["logs"].append(entry)
        self.save_memory()
        print(f"📝 [Memory Node] Saved: {event_type}")

    def scan_and_heal_environment(self):
        """پشکنینی مۆدیۆلە سەرەکییەکان"""
        print("🔍 [Trigger Node] Scanning system modules...")

        # تەنها فایلی run_app و dashboard دەپشکنێت
        core_modules = ["run_app", "dashboard"]

        for mod in core_modules:
            try:
                __import__(mod)
                print(f"✅ Module [{mod}] is healthy.")
            except Exception as e:
                print(f"⚠️ [Self-Healing] Issue detected in [{mod}]: {e}")
                self.log_event("ErrorDetected", f"Module {mod} error: {e}")
                return False
        return True

    def run_apex_platform(self):
        """دەستپێکردنی ئەپەکە لە ژێر چاودێری ئەیجێنتەکەدا"""
        if self.scan_and_heal_environment():
            self.log_event("HealthCheck", "System fully functional.")
            print("🚀 [Action Node] Starting APEX Platform via Streamlit...")
            subprocess.run([sys.executable, "-m", "streamlit", "run", "run_app.py"])
        else:
            print("❌ System requires manual review or automatic hot-fix.")


if __name__ == "__main__":
    agent = ApexAIAgent()
    agent.run_apex_platform()
