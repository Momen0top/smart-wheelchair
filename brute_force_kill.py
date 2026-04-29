import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def brute_force_kill():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Finding process on port 8000...")
        stdin, stdout, stderr = ssh.exec_command('sudo -S lsof -t -i:8000')
        stdin.write(password + '\n')
        stdin.flush()
        pids = stdout.read().decode().strip().split('\n')
        
        if pids and pids[0]:
            print(f"Killing PIDs: {pids}")
            for pid in pids:
                ssh.exec_command(f'sudo -S kill -9 {pid}')
                stdin, stdout, stderr = ssh.exec_command(f'sudo -S kill -9 {pid}')
                stdin.write(password + '\n')
                stdin.flush()
        else:
            print("No process found on port 8000 via lsof.")

        print("Checking with fuser...")
        stdin, stdout, stderr = ssh.exec_command('sudo -S fuser -k 8000/tcp')
        stdin.write(password + '\n')
        stdin.flush()
        stdout.read()
        
        print("Waiting for port to clear...")
        import time
        time.sleep(2)
        
        print("Starting Virtual Test Server...")
        cmd = 'cd /home/momen/smartchair_test && nohup /home/momen/smartchair_test/venv/bin/python test_virtual_server.py > test.log 2>&1 &'
        ssh.exec_command(cmd)
        
        time.sleep(3)
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep test_virtual_server.py | grep -v grep')
        res = stdout.read().decode()
        if res:
            print(f"SUCCESS: {res}")
        else:
            print("FAILED. Log:")
            stdin, stdout, stderr = ssh.exec_command('cat /home/momen/smartchair_test/test.log')
            print(stdout.read().decode())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    brute_force_kill()
