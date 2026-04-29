import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../models/models.dart';

/// Pairing screen — scan QR code or NFC to connect to SmartChair.
class PairingScreen extends StatefulWidget {
  final Function(PairingInfo info) onPaired;
  const PairingScreen({super.key, required this.onPaired});

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  bool _scanning = false;
  String _status = 'Scan QR code on wheelchair';
  final _ipCtrl = TextEditingController(text: '192.168.1.100');
  final _portCtrl = TextEditingController(text: '8000');

  @override
  void dispose() { _ipCtrl.dispose(); _portCtrl.dispose(); super.dispose(); }

  void _onQrDetected(BarcodeCapture capture) {
    final barcode = capture.barcodes.firstOrNull;
    if (barcode == null || barcode.rawValue == null) return;
    try {
      final data = jsonDecode(barcode.rawValue!);
      final info = PairingInfo.fromJson(data);
      setState(() { _scanning = false; _status = 'Connected to ${info.robotId}'; });
      widget.onPaired(info);
    } catch (_) {
      setState(() => _status = 'Invalid QR code');
    }
  }

  void _manualConnect() {
    final ip = _ipCtrl.text.trim();
    final port = int.tryParse(_portCtrl.text.trim()) ?? 8000;
    if (ip.isEmpty) return;
    final info = PairingInfo(robotId: 'manual', ip: ip, port: port);
    setState(() => _status = 'Connected to $ip:$port');
    widget.onPaired(info);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF06080F),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(children: [
            // Header
            Row(children: [
              const Icon(Icons.link, color: Color(0xFF7B6EF6), size: 22),
              const SizedBox(width: 8),
              const Text('Connect', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Color(0xFFE8ECF4))),
            ]),
            const SizedBox(height: 20),

            // Status
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF0D1117),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF1B2232)),
              ),
              child: Row(children: [
                Icon(Icons.info_outline, size: 16, color: const Color(0xFF7B6EF6)),
                const SizedBox(width: 8),
                Expanded(child: Text(_status, style: const TextStyle(fontSize: 13, color: Color(0xFFE8ECF4)))),
              ]),
            ),
            const SizedBox(height: 20),

            // QR Scanner
            if (_scanning)
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: MobileScanner(onDetect: _onQrDetected),
                ),
              )
            else ...[
              GestureDetector(
                onTap: () => setState(() => _scanning = true),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFF7B6EF6), Color(0xFF5548D9)]),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [BoxShadow(color: const Color(0xFF7B6EF6).withOpacity(0.3), blurRadius: 16, offset: const Offset(0, 6))],
                  ),
                  child: const Column(children: [
                    Icon(Icons.qr_code_scanner, color: Colors.white, size: 48),
                    SizedBox(height: 8),
                    Text('Scan QR Code', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                    Text('Point camera at wheelchair QR', style: TextStyle(color: Colors.white70, fontSize: 12)),
                  ]),
                ),
              ),
              const SizedBox(height: 24),

              // Divider
              Row(children: [
                Expanded(child: Container(height: 1, color: const Color(0xFF1B2232))),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12),
                  child: Text('OR', style: TextStyle(color: Color(0xFF3A4255), fontSize: 11)),
                ),
                Expanded(child: Container(height: 1, color: const Color(0xFF1B2232))),
              ]),
              const SizedBox(height: 20),

              // Manual connect
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1117),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF1B2232)),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Manual Connection', style: TextStyle(color: Color(0xFFE8ECF4), fontSize: 14, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  _field('IP Address', _ipCtrl),
                  const SizedBox(height: 8),
                  _field('Port', _portCtrl),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _manualConnect,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00E5A0),
                        foregroundColor: const Color(0xFF06080F),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: const Text('Connect', style: TextStyle(fontWeight: FontWeight.w600)),
                    ),
                  ),
                ]),
              ),
            ],
          ]),
        ),
      ),
    );
  }

  Widget _field(String label, TextEditingController ctrl) => TextField(
    controller: ctrl,
    style: const TextStyle(color: Color(0xFFE8ECF4), fontSize: 14),
    decoration: InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Color(0xFF6B7688), fontSize: 12),
      filled: true,
      fillColor: const Color(0xFF06080F),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    ),
  );
}
