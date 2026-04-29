import paramiko

def check_raw_serial():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('192.168.1.13', username='momen', password='123456789')
    # Stop the service first so it doesn't hold the port
    client.exec_command('echo 123456789 | sudo -S systemctl stop smartchair.service')
    
    cmd = "/home/momen/smartchair_backend/venv/bin/python -c \"import serial; ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2); print(ser.read(200))\""
    stdin, stdout, stderr = client.exec_command(cmd)
    print("RAW BYTES:", stdout.read())
    
    # Start it back
    client.exec_command('echo 123456789 | sudo -S systemctl start smartchair.service')
    client.close()

if __name__ == "__main__":
    check_raw_serial()
