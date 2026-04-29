import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def fix_and_run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Installing dependencies...")
        # Use pip3 and --user to avoid permission issues, or just sudo
        stdin, stdout, stderr = ssh.exec_command('sudo -S pip3 install fastapi uvicorn')
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read() # Wait for install
        
        print("Starting Virtual Test Server...")
        ssh.exec_command('pkill -f test_virtual_server.py')
        ssh.exec_command('nohup python3 /home/momen/smartchair_test/test_virtual_server.py > /home/momen/smartchair_test/test.log 2>&1 &')
        
        print("Verifying...")
        import time
        time.sleep(2)
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep test_virtual_server.py | grep -v grep')
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    fix_and_run()
