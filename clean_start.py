import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def clean_and_run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Stopping all potential server instances...")
        # Kill both python and uvicorn processes, using sudo to be sure
        stdin, stdout, stderr = ssh.exec_command('sudo -S pkill -f test_virtual_server.py || true')
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        
        stdin, stdout, stderr = ssh.exec_command('sudo -S pkill -f uvicorn || true')
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        
        print("Starting Virtual Test Server...")
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
            print("Still failed. Log:")
            stdin, stdout, stderr = ssh.exec_command('cat /home/momen/smartchair_test/test.log')
            print(stdout.read().decode())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    clean_and_run()
