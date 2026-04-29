import paramiko

def run_ssh_commands(host, user, password, commands):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password)
        for cmd in commands:
            print(f"--- Executing: {cmd} ---")
            stdin, stdout, stderr = client.exec_command(f"echo {password} | sudo -S {cmd}")
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            if out: print(out)
            if err: print(err)
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    commands = [
        "ip a show wlan0",
        "systemctl status smartchair.service --no-pager",
        "journalctl -u smartchair.service -n 20 --no-pager",
        "ss -tunlp | grep python"
    ]
    run_ssh_commands('192.168.1.13', 'momen', '123456789', commands)
