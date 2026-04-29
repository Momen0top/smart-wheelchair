import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def fix_websocket_lib():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Installing 'websockets' library in the venv...")
        # FastAPI/Uvicorn needs 'websockets' to accept WS connections
        stdin, stdout, stderr = ssh.exec_command('/home/momen/smartchair_test/venv/bin/pip install websockets')
        print(stdout.read().decode())
        
        print("Restarting server...")
        ssh.exec_command('sudo -S fuser -k 8000/tcp || true')
        stdin, stdout, stderr = ssh.exec_command('sudo -S fuser -k 8000/tcp || true')
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        
        cmd = 'cd /home/momen/smartchair_test && nohup /home/momen/smartchair_test/venv/bin/python test_virtual_server.py > test.log 2>&1 &'
        ssh.exec_command(cmd)
        
        print("Done! The server should now be able to upgrade to WebSocket connections.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    fix_websocket_lib()
