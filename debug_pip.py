import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def debug_pip():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Checking python and pip paths...")
        stdin, stdout, stderr = ssh.exec_command('which python3 && which pip3')
        print(stdout.read().decode())
        
        print("Installing using python3 -m pip...")
        stdin, stdout, stderr = ssh.exec_command('python3 -m pip install fastapi uvicorn')
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        print("Trying to run python3 -c 'import uvicorn; print(uvicorn.__version__)'")
        stdin, stdout, stderr = ssh.exec_command("python3 -c 'import uvicorn; print(\"Import success\")'")
        print(stdout.read().decode())
        print(stderr.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    debug_pip()
