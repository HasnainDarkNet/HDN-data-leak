import socket
import os
import time
import threading
from datetime import datetime

LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 9998
SAVE_FOLDER = "received_folders"
BUFFER_SIZE = 65536

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

print("="*60)
print("📥 KALI RECEIVER - FINAL")
print("="*60)
print(f"🎯 Listening: {LISTEN_IP}:{LISTEN_PORT}")
print(f"📁 Saving to: {SAVE_FOLDER}")
print("="*60)

# Kill existing port
def kill_port():
    try:
        os.system(f"sudo fuser -k {LISTEN_PORT}/tcp")
        time.sleep(2)
    except:
        pass

kill_port()

# Server
def create_server():
    while True:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            server.bind((LISTEN_IP, LISTEN_PORT))
            server.listen(5)
            print("[*] ✅ Server started!")
            return server
        except Exception as e:
            print(f"[-] Error: {e}")
            time.sleep(3)

server = create_server()
print("[*] Waiting for connections...\n")

# Handle client
def handle_client(client, addr):
    try:
        print(f"\n[+] Connection from: {addr}")
        client.settimeout(300)  # 5 minute timeout
        
        # Folder name
        data = b""
        while b'\n' not in data:
            chunk = client.recv(1)
            if not chunk:
                break
            data += chunk
        
        if not data:
            client.close()
            return
        
        folder_name = data.decode().strip().replace("FOLDER:", "")
        print(f"[*] 📁 Folder: {folder_name}")
        
        # Count
        data = b""
        while b'\n' not in data:
            chunk = client.recv(1)
            if not chunk:
                break
            data += chunk
        
        if not data:
            client.close()
            return
        
        file_count = int(data.decode().strip().replace("COUNT:", ""))
        print(f"[*] 📊 Files: {file_count}")
        
        # Save folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(SAVE_FOLDER, f"{folder_name}_{timestamp}")
        os.makedirs(save_path, exist_ok=True)
        print(f"[*] 💾 Saving to: {save_path}")
        
        received = 0
        
        # Receive files
        for i in range(file_count):
            try:
                # Header
                data = b""
                while b'\n' not in data:
                    chunk = client.recv(1)
                    if not chunk:
                        break
                    data += chunk
                
                if not data:
                    break
                
                header = data.decode().strip()
                parts = header.replace("FILE:", "").split(":")
                filename = parts[0]
                file_size = int(parts[1])
                
                filepath = os.path.join(save_path, filename)
                
                print(f"\n[*] Receiving: {filename} ({file_size/1024:.1f}KB)")
                
                # Data
                received_size = 0
                with open(filepath, 'wb', buffering=BUFFER_SIZE) as f:
                    while received_size < file_size:
                        chunk = client.recv(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        received_size += len(chunk)
                        
                        if file_size > 1024*1024:
                            if received_size % (1024*1024) == 0 or received_size == file_size:
                                progress = (received_size / file_size) * 100
                                print(f"\r   Progress: {received_size/1024:.1f}KB/{file_size/1024:.1f}KB ({progress:.1f}%)", end='', flush=True)
                
                if received_size == file_size:
                    print(f"\n[+] ✅ Saved: {filename}")
                    received += 1
                else:
                    print(f"\n[-] ⚠️ Incomplete")
                    
            except Exception as e:
                print(f"[-] Error: {e}")
                break
        
        # Complete
        try:
            client.recv(1024)
        except:
            pass
        
        print(f"\n[+] ✅ Received {received}/{file_count} files")
        print(f"[+] 📁 Location: {save_path}")
        print("-"*60)
        client.close()
        
    except Exception as e:
        print(f"[-] Error: {e}")
        try:
            client.close()
        except:
            pass

# Main loop
while True:
    try:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()
    except Exception as e:
        print(f"[-] Server error: {e}")
        server = create_server()
