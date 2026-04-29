import paramiko
import time

def test_motor():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('192.168.1.13', username='momen', password='123456789')
    
    # Stop the service
    client.exec_command('echo 123456789 | sudo -S systemctl stop smartchair.service')
    
    # Send FORWARD and read response
    cmd = "/home/momen/smartchair_backend/venv/bin/python -c \"import serial; import time; ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2); time.sleep(2); ser.write(b'CMD:FORWARD\\n'); ser.flush(); time.sleep(1); print(ser.read_all().decode())\""
    stdin, stdout, stderr = client.exec_command(cmd)
    print("RESPONSE:", stdout.read().decode())
    
    # Start it back
    client.exec_command('echo 123456789 | sudo -S systemctl start smartchair.service')
    client.close()

if __name__ == "__main__":
    test_motor()
