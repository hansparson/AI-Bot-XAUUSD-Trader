import os
import sys

# Tambahkan current directory ke path agar import core/utils lancar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.engine import run_engine

if __name__ == "__main__":
    try:
        run_engine()
    except KeyboardInterrupt:
        print("\n[!] Engine Stopped.")
