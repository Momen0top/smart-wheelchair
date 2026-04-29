import paramiko
import sys

def run_ssh_commands(host, user, password, commands):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password)
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(f"echo {password} | sudo -S {cmd}")
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
        "nmcli con delete SmartChair_AP || true",
        "nmcli con add type wifi ifname wlan0 mode ap con-name SmartChair_AP ssid SmartChair_AP autoconnect yes",
        "nmcli con modify SmartChair_AP 802-11-wireless.band bg",
        "nmcli con modify SmartChair_AP 802-11-wireless-security.key-mgmt wpa-psk",
        "nmcli con modify SmartChair_AP 802-11-wireless-security.psk smartchair123",
        "nmcli con modify SmartChair_AP ipv4.method shared",
        "nmcli con up SmartChair_AP"
    ]
    run_ssh_commands('192.168.1.13', 'momen', '123456789', commands)
