import paramiko
import sys

def run_ssh_command(host, user, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password)
        stdin, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        print("STDOUT:\n", out)
        print("STDERR:\n", err)
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    run_ssh_command('192.168.1.13', 'momen', '123456789', 'cat /etc/os-release && ip a && which nmcli')
