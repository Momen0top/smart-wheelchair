import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def deploy_with_venv():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Creating virtual environment...")
        stdin, stdout, stderr = ssh.exec_command('python3 -m venv /home/momen/smartchair_test/venv')
        stdout.read()
        
        print("Installing dependencies in venv...")
        stdin, stdout, stderr = ssh.exec_command('/home/momen/smartchair_test/venv/bin/pip install fastapi uvicorn')
        stdout.read()
        
        print("Starting Virtual Test Server using venv python...")
        ssh.exec_command('pkill -f test_virtual_server.py')
        cmd = 'cd /home/momen/smartchair_test && nohup /home/momen/smartchair_test/venv/bin/python test_virtual_server.py > test.log 2>&1 &'
        ssh.exec_command(cmd)
        
        import time
        time.sleep(3)
        
        print("Verifying...")
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep test_virtual_server.py | grep -v grep')
        res = stdout.read().decode()
        if res:
            print(f"SUCCESS: {res}")
            print(f"Server is running at http://{host}:8000")
        else:
            print("FAILED again. Checking logs...")
            stdin, stdout, stderr = ssh.exec_command('cat /home/momen/smartchair_test/test.log')
            print(stdout.read().decode())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    deploy_with_venv()
