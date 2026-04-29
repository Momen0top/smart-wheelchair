import paramiko

def trigger_forward():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('192.168.1.13', username='momen', password='123456789')
    
    # Trigger move forward via local API
    cmd = 'curl -X POST http://localhost:8000/command -H "Content-Type: application/json" -d "{\\\"text\\\": \\\"move forward\\\"}"'
    stdin, stdout, stderr = client.exec_command(cmd)
    print("API RESPONSE:", stdout.read().decode())
    
    # Wait 2 seconds and check logs
    import time
    time.sleep(2)
    stdin, stdout, stderr = client.exec_command('journalctl -u smartchair.service -n 20 --no-pager')
    print("LOGS:", stdout.read().decode())
    
    client.close()

if __name__ == "__main__":
    trigger_forward()
