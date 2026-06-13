import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

errors = []

try:
    from context import build_context
    print("context OK")
except Exception as e:
    errors.append(f"context: {e}")

try:
    from splitter import full_analyze
    print("splitter OK")
except Exception as e:
    errors.append(f"splitter: {e}")

try:
    from quality import quality_pipeline
    print("quality OK")
except Exception as e:
    errors.append(f"quality: {e}")

try:
    from bridge import analyze_then_create
    print("bridge OK")
except Exception as e:
    errors.append(f"bridge: {e}")

try:
    from novel import generate_chapter
    print("novel OK")
except Exception as e:
    errors.append(f"novel: {e}")

try:
    from gui import NovelFactoryGUI
    print("gui OK")
except Exception as e:
    errors.append(f"gui: {e}")

if errors:
    print("ERRORS:", errors)
else:
    print("ALL OK")

input("Press Enter...")
