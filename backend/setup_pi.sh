#!/bin/bash
set -e

echo "====================================="
echo " SmartChair Raspberry Pi Setup "
echo "====================================="

# Update package list and install system dependencies
echo "1. Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv i2c-tools libgpiod2

# Create a virtual environment and install python packages
echo "2. Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Enable I2C (needed for VL53L0X)
echo "3. Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Set up the systemd service to auto-start on boot
echo "4. Configuring auto-boot service..."
# Update the service file with the current user and directory path
CURRENT_DIR=$(pwd)
CURRENT_USER=$USER

sed -i "s|User=pi|User=$CURRENT_USER|g" smartchair.service
sed -i "s|WorkingDirectory=/home/pi/smartchair_backend|WorkingDirectory=$CURRENT_DIR|g" smartchair.service
sed -i "s|ExecStart=/home/pi/smartchair_backend/venv/bin/python main.py|ExecStart=$CURRENT_DIR/venv/bin/python main.py|g" smartchair.service

sudo cp smartchair.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartchair.service
sudo systemctl restart smartchair.service

echo "====================================="
echo " Setup complete! "
echo " The SmartChair backend will now auto-start on boot."
echo " To check the status, use: sudo systemctl status smartchair.service"
echo " To view logs, use: journalctl -u smartchair.service -f"
echo "====================================="
