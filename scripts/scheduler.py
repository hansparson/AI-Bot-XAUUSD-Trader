import subprocess
import os
import sys
from datetime import datetime

# Tambahkan project root ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_scheduler():
    print("========================================")
    print("🚀 [SCHEDULER] MANUAL RUN AKTIF")
    print("Target: Menjalankan Evaluator Sekarang")
    print("========================================")

    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    print(f"\n🚀 [{now.strftime('%H:%M:%S')}] MEMULAI EVALUASI HARIAN...")
    try:
        # Jalankan evaluator sebagai modul
        result = subprocess.run([sys.executable, "-m", "scripts.evaluator"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ EVALUASI BERHASIL: {current_date}")
            print(result.stdout)
        else:
            print(f"❌ EVALUASI GAGAL: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
    except Exception as e:
        print(f"❌ Error eksekusi: {e}")
    
    print("🏁 Proses selesai.\n")

if __name__ == "__main__":
    run_scheduler()
