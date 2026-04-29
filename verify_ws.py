import paramiko

host = '192.168.1.13'
user = 'momen'
password = '123456789'

def verify_ws_output():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=10)
        
        print("Grabbing a sample of the WebSocket output...")
        # We can use a python one-liner on the Pi to connect to the WS and print one frame
        cmd = """python3 -c "
import websocket
import json
try:
    ws = websocket.create_connection('ws://localhost:8000/ws/map')
    # Receive one frame
    msg = ws.recv()
    data = json.loads(msg)
    print(f'Type: {data.get(\\"type\\")}')
    print(f'Size: {data.get(\\"width\\")}x{data.get(\\"height\\")}')
    print(f'Cells[0] type: {type(data[\\"cells\\"])}')
    print(f'Cells[0][0] type: {type(data[\\"cells\\"][0][0])}')
    ws.close()
except Exception as e:
    print(f'Error: {e}')
" """
        # Need websocket-client installed on Pi
        ssh.exec_command('/home/momen/smartchair_test/venv/bin/pip install websocket-client')
        
        stdin, stdout, stderr = ssh.exec_command(f'/home/momen/smartchair_test/venv/bin/python3 -c "import websocket; ws=websocket.create_connection(\'ws://localhost:8000/ws/map\'); msg=ws.recv(); print(msg[:500]); ws.close()"')
        print("Sample JSON (first 500 chars):")
        print(stdout.read().decode())
        print(stderr.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    verify_ws_output()
