import paramiko

def run_ssh_commands(host, user, password, commands):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password)
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            # We use a channel to get live output if possible, but for simplicity:
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            if out: print("OUT:", out)
            if err: print("ERR:", err)
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    commands = [
        "cd /home/momen/smartchair_backend && python3 -m venv venv",
        "cd /home/momen/smartchair_backend && ./venv/bin/python -m pip install --upgrade pip",
        "cd /home/momen/smartchair_backend && ./venv/bin/pip install -r requirements.txt"
    ]
    run_ssh_commands('192.168.1.13', 'momen', '123456789', commands)
