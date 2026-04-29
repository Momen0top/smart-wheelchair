import paramiko
import os

def sftp_upload_dir(sftp, local_dir, remote_dir):
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = remote_dir + '/' + item
        if os.path.isfile(local_path):
            print(f"Uploading {local_path} to {remote_path}")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            sftp_upload_dir(sftp, local_path, remote_path)

def deploy():
    host = '192.168.1.13'
    user = 'momen'
    password = '123456789'
    local_backend = r'c:\Users\Toppa\Desktop\chair\backend'
    remote_backend = '/home/momen/smartchair_backend'

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password)
        sftp = client.open_sftp()
        
        # Create remote dir if not exists
        try:
            client.exec_command(f"mkdir -p {remote_backend}")
        except:
            pass
            
        sftp_upload_dir(sftp, local_backend, remote_backend)
        sftp.close()
        print("Upload complete!")
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    deploy()
