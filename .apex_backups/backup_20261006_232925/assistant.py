import sys
import traceback

print("🔍 APEX DEBUGGER: دۆزینەوەی سەرچاوەی هەڵەی re.error...")

try:
    import app

    print("✅ فایلی app.py هیچ هەڵەیەکی تێدا نییە.")
except Exception as e:
    print("\n❌ هەڵەی سەرەکی دۆزرایەوە لەم ڕێڕەوەدا:\n")
    traceback.print_exc()
