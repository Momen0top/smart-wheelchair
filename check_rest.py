import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def check_map_rest():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8000/map | head -c 1000')
        print("REST /map Sample:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_map_rest()
