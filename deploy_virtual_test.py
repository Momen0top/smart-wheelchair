import paramiko
import os

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def deploy_test():
    print(f"Connecting to {host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        # Create directory
        ssh.exec_command('mkdir -p /home/momen/smartchair_test')
        
        print("Uploading backend/test_virtual_server.py...")
        sftp = ssh.open_sftp()
        sftp.put('backend/test_virtual_server.py', '/home/momen/smartchair_test/test_virtual_server.py')
        sftp.close()
        
        print("Stopping any existing instances...")
        ssh.exec_command('pkill -f test_virtual_server.py')
        
        print("Starting Virtual Test Server...")
        # Run using nohup to keep it running after we disconnect
        # We also need to make sure fastapi/uvicorn are installed
        ssh.exec_command('pip install fastapi uvicorn')
        
        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.exec_command('nohup python3 /home/momen/smartchair_test/test_virtual_server.py > /home/momen/smartchair_test/test.log 2>&1 &')
        
        print("Done!")
        print(f"Virtual map is now running at http://{host}:8000")
        print(f"WebSocket URL: ws://{host}:8000/ws/map")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    deploy_test()
