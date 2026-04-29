import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def check_log():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        # Read the last 20 lines of the test.log
        stdin, stdout, stderr = ssh.exec_command('tail -n 20 /home/momen/smartchair_test/test.log')
        print("Server Logs:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_log()
