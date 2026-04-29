import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def check_log():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        # Check if the process is running
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep test_virtual_server.py | grep -v grep')
        res = stdout.read().decode()
        if res:
            print(f"Process is RUNNING:\n{res}")
        else:
            print("Process is NOT running.")
            
        # Read the log
        stdin, stdout, stderr = ssh.exec_command('tail -n 10 /home/momen/smartchair_test/test.log')
        log = stdout.read().decode()
        print(f"Last 10 lines of log:\n{log}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_log()
