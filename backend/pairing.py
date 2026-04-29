"""
Device Pairing — QR code generation & NFC payload.
"""
import io
import json
import socket

import qrcode

from config import ROBOT_ID, SERVER_PORT
from utils import logger


def get_local_ip() -> str:
    """Detect the Pi's local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))   # doesn't actually send data
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.1.1"


def get_pairing_payload() -> dict:
    """Return the pairing data dict."""
    return {
        "robot_id": ROBOT_ID,
        "ip": get_local_ip(),
        "port": SERVER_PORT,
    }


def generate_qr_bytes() -> bytes:
    """Generate a QR code PNG as bytes."""
    data = json.dumps(get_pairing_payload())
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    logger.info("QR code generated for %s", data)
    return buf.getvalue()


def get_nfc_payload() -> str:
    """Return JSON string suitable for NFC NDEF text record."""
    return json.dumps(get_pairing_payload())
