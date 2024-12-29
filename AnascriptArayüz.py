import time
from multiprocessing import shared_memory
import subprocess
import threading

# Ortak hafıza adı ve boyutu
SHARED_MEMORY_NAME = "SystemMode"
SHARED_MEMORY_SIZE = 10  # En fazla 10 karakterlik veri

SCRIPTS = {
    "2": r"C:\Users\skyks\Desktop\yolov7-main\tamoto-sistemde-kullanılacak.py",
    "1": r"C:\Users\skyks\Desktop\yolov7-main\manuel.py",
    "3": r"C:\Users\skyks\Desktop\yolov7-main\yarıoto-sistemde-kullanılacak.py"
}

# Global değişkenler
current_mode = None
current_process = None

def cleanup_shared_memory(name):
    """Belirtilen paylaşımlı belleği temizler."""
    try:
        shm = shared_memory.SharedMemory(name=name)
        shm.close()
        shm.unlink()
        print(f"Paylaşımlı bellek '{name}' temizlendi.", flush=True)
    except FileNotFoundError:
        print(f"Paylaşımlı bellek '{name}' bulunamadı.", flush=True)
    except Exception as e:
        print(f"Paylaşımlı bellek temizleme hatası: {e}", flush=True)

def write_to_shared_memory(value):
    """Shared memory'ye veri yaz."""
    try:
        shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME)
        data = value.ljust(SHARED_MEMORY_SIZE)  # Veriyi shared memory boyutuna uygun hale getir
        shm.buf[:len(data)] = bytes(data, "utf-8")
    except Exception as e:
        print(f"Shared memory'ye yazma hatası: {e}", flush=True)

def read_from_shared_memory():
    """Shared memory'den veri oku."""
    try:
        shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME)
        data = bytes(shm.buf[:SHARED_MEMORY_SIZE]).decode("utf-8").strip()
        return data
    except Exception as e:
        print(f"Shared memory'den okuma hatası: {e}", flush=True)
        return None

def stop_current_process():
    """Çalışan scripti durdur."""
    global current_process
    if current_process and current_process.poll() is None:  # Process çalışıyorsa
        current_process.terminate()
        print("Mevcut script durduruldu.", flush=True)
        current_process = None
        # Paylaşımlı bellekleri temizle
        cleanup_shared_memory("raw_frame")
        cleanup_shared_memory("processed_frame")

def start_new_process(mode):
    """Yeni scripti başlat."""
    global current_process
    script_path = SCRIPTS.get(mode)
    if script_path:
        print(f"Yeni script çalıştırılıyor: {script_path}", flush=True)
        current_process = subprocess.Popen(
            ["python", script_path],
            stdout=subprocess.PIPE,  # Çıktıyı yakala
            stderr=subprocess.PIPE,  # Hataları yakala
            text=True  # Çıktıları metin olarak al
        )

        def read_output(pipe, pipe_type):
            """Alt scriptin çıktısını oku ve terminale yaz."""
            for line in pipe:
                print(f"[{pipe_type}] {line.strip()}", flush=True)

        # Çıktıları ve hataları ayrı thread'lerde okuyarak yazdır
        threading.Thread(target=read_output, args=(current_process.stdout, "Mod Çıktısı :"), daemon=True).start()
        threading.Thread(target=read_output, args=(current_process.stderr, "MOD ERROR :"), daemon=True).start()
    else:
        print(f"Bilinmeyen mod: {mode}", flush=True)

def main():
    global current_mode, current_process

    # Ortak hafızayı aç veya oluştur
    try:
        shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME, create=True, size=SHARED_MEMORY_SIZE)
        write_to_shared_memory("Bekleniyor")  # Varsayılan değer
        print("Ortak hafıza oluşturuldu ve varsayılan değer yazıldı.", flush=True)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME, create=False)
        print("Ortak hafıza zaten mevcut.", flush=True)

    print("Sistem başlatıldı, veri bekleniyor...", flush=True)

    try:
        # Shared memory'den veri gelene kadar bekle
        while True:
            # Shared memory'den veri al
            shared_memory_data = read_from_shared_memory()
            if shared_memory_data and shared_memory_data in SCRIPTS:
                print(f"Shared memory'den gelen veri: {shared_memory_data}", flush=True)
                current_mode = shared_memory_data
                break

            time.sleep(1)  # Döngü gecikmesi

        # İlgili scripti çalıştır
        start_new_process(current_mode)

        # Shared memory'yi izlemeye devam et
        while True:
            shared_memory_data = read_from_shared_memory()
            if shared_memory_data and shared_memory_data != current_mode and shared_memory_data in SCRIPTS:
                print(f"Shared memory'den gelen yeni mod: {shared_memory_data}", flush=True)

                # Mevcut scripti durdur
                stop_current_process()

                # Yeni modu güncelle
                current_mode = shared_memory_data

                # Yeni scripti çalıştır
                start_new_process(current_mode)

            time.sleep(1)  # Döngü gecikmesi
    except KeyboardInterrupt:
        print("Program sonlandırılıyor...", flush=True)
    finally:
        stop_current_process()
        shm.close()
        shm.unlink()  # Ortak hafızayı temizle

if __name__ == "__main__":
    main()
