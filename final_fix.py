import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def final_fix():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Installing dependencies for user 'momen'...")
        ssh.exec_command('pip3 install fastapi uvicorn')
        
        print("Starting Virtual Test Server using python3 -m uvicorn...")
        ssh.exec_command('pkill -f test_virtual_server.py')
        # We need the full path to test_virtual_server.py or change dir
        cmd = 'cd /home/momen/smartchair_test && nohup python3 test_virtual_server.py > test.log 2>&1 &'
        ssh.exec_command(cmd)
        
        import time
        time.sleep(3)
        
        print("Checking again...")
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep test_virtual_server.py | grep -v grep')
        res = stdout.read().decode()
        if res:
            print(f"SUCCESS: {res}")
        else:
            print("STILL FAILED. Checking logs...")
            stdin, stdout, stderr = ssh.exec_command('cat /home/momen/smartchair_test/test.log')
            print(stdout.read().decode())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    final_fix()
