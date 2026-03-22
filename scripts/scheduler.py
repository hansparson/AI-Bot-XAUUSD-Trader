import time
import subprocess
from datetime import datetime, os
import sys

# Tambahkan project root ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_scheduler():
    print("========================================")
    print("⏰ [SCHEDULER] AUTO-LEARNING AKTIF")
    print("Target: Setiap jam 00:00 (Tengah Malam)")
    print("========================================")

    last_run_date = None

    try:
        while True:
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_hour = now.hour
            
            # Monitoring Heartbeat (setiap jam)
            if now.minute == 0:
                print(f"🕒 [{now.strftime('%H:%M:%S')}] Scheduler standby...")

            # Trigger jam 12 malam
            if current_hour == 0 and last_run_date != current_date:
                print(f"\n🚀 [{now.strftime('%H:%M:%S')}] MEMULAI EVALUASI HARIAN...")
                try:
                    # Jalankan evaluator sebagai modul
                    result = subprocess.run([sys.executable, "-m", "scripts.evaluator"], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"✅ EVALUASI BERHASIL: {current_date}")
                        last_run_date = current_date
                    else:
                        print(f"❌ EVALUASI GAGAL: {result.stderr}")
                except Exception as e:
                    print(f"❌ Error eksekusi: {e}")
                
                print("💤 Kembali Standby untuk 24 jam kedepan...\n")
            
            # Check setiap 30 detik
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n🛑 Scheduler Dimatikan.")

if __name__ == "__main__":
    run_scheduler()
