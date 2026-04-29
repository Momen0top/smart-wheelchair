import 'dart:async';
import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../services/speech_service.dart';
import '../widgets/map_painter.dart';
import '../widgets/room_dialog.dart';
import '../widgets/control_pad.dart';

/// Main map screen — live occupancy grid, controls, voice input.
class MapScreen extends StatefulWidget {
  final ApiService api;
  final WebSocketService ws;
  const MapScreen({super.key, required this.api, required this.ws});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> with TickerProviderStateMixin {
  final SpeechService _speech = SpeechService();
  final TransformationController _transformCtrl = TransformationController();

  MapData? _map;
  List<Room> _rooms = [];
  String _motorState = 'stopped';
  bool _scanning = false;
  bool _navigating = false;
  String _targetRoom = '';
  bool _isListening = false;
  String _recognized = '';
  String _cmdResult = '';

  StreamSubscription? _mapSub;
  Timer? _pollTimer;

  late AnimationController _pulseCtrl;
  late Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000));
    _pulse = Tween(begin: 1.0, end: 1.12).animate(CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut));
    _speech.init();
    _mapSub = widget.ws.mapStream.listen((m) { if (mounted) setState(() => _map = m); });
    _startPolling();
    _loadRooms();
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _mapSub?.cancel();
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      try {
        final s = await widget.api.getStatus();
        if (!mounted) return;
        setState(() {
          _motorState = s['motors'] ?? 'stopped';
          _scanning = s['scanning'] ?? false;
          _navigating = s['navigating'] ?? false;
          _targetRoom = s['target_room'] ?? '';
        });
      } catch (_) {}
    });
  }

  Future<void> _loadRooms() async {
    try {
      final r = await widget.api.getRooms();
      if (mounted) setState(() => _rooms = r);
    } catch (_) {}
  }

  // ── Voice ──
  void _listen() {
    setState(() { _isListening = true; _recognized = ''; _cmdResult = 'Listening…'; });
    _pulseCtrl.repeat(reverse: true);
    _speech.listen(onResult: (text, isFinal) {
      setState(() => _recognized = text);
      if (isFinal) _sendCmd(text);
    });
  }

  void _stopListen() {
    _speech.stop();
    setState(() => _isListening = false);
    _pulseCtrl.stop(); _pulseCtrl.reset();
  }

  Future<void> _sendCmd(String text) async {
    _pulseCtrl.stop(); _pulseCtrl.reset();
    setState(() { _isListening = false; _cmdResult = 'Sending…'; });
    try {
      final r = await widget.api.sendCommand(text);
      setState(() => _cmdResult = '${r['intent']} · ${r['status']}');
      _loadRooms();
    } catch (e) {
      setState(() => _cmdResult = 'Error');
    }
  }

  Future<void> _quick(String cmd) async {
    try { await widget.api.sendCommand(cmd); } catch (_) {}
  }

  Future<void> _stop() async {
    try { await widget.api.sendStop(); } catch (_) {}
    setState(() => _cmdResult = 'STOPPED');
  }

  // ── Map tap → create room ──
  void _onMapTap(TapUpDetails details, BoxConstraints constraints) {
    if (_map == null) return;
    final pos = _transformCtrl.toScene(details.localPosition);
    final cellW = constraints.maxWidth / _map!.width;
    final cellH = constraints.maxHeight / _map!.height;
    final cell = cellW < cellH ? cellW : cellH;
    final gx = pos.dx / cell;
    final gy = pos.dy / cell;
    final wx = (gx - _map!.width / 2) * _map!.resolution;
    final wy = (gy - _map!.height / 2) * _map!.resolution;

    showDialog<String>(
      context: context,
      builder: (_) => RoomDialog(x: wx, y: wy),
    ).then((name) {
      if (name != null && name.isNotEmpty) {
        widget.api.createRoom(name, wx, wy).then((_) => _loadRooms());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF06080F),
      body: SafeArea(
        child: Column(children: [
          _header(),
          Expanded(child: _mapView()),
          _bottomBar(),
        ]),
      ),
    );
  }

  // ── Header ──
  Widget _header() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Row(children: [
        Container(
          width: 36, height: 36,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF7B6EF6), Color(0xFF5B4FD6)]),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.accessible, color: Colors.white, size: 18),
        ),
        const SizedBox(width: 10),
        const Expanded(child: Text('SmartChair', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: Color(0xFFE8ECF4)))),
        // Status chips
        _chip(_scanning ? 'SCANNING' : 'IDLE', _scanning ? const Color(0xFF00D4FF) : const Color(0xFF3A4255)),
        const SizedBox(width: 6),
        _chip(_motorState.toUpperCase(), _motorState == 'stopped' ? const Color(0xFF3A4255) : const Color(0xFF00E5A0)),
        if (_navigating) ...[const SizedBox(width: 6), _chip('NAV: $_targetRoom', const Color(0xFFFFB347))],
        const SizedBox(width: 10),
        GestureDetector(
          onTap: _stop,
          child: Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFFF4757), Color(0xFFCC2233)]),
              borderRadius: BorderRadius.circular(10),
              boxShadow: [BoxShadow(color: const Color(0xFFFF4757).withOpacity(0.3), blurRadius: 10, offset: const Offset(0, 3))],
            ),
            child: const Icon(Icons.power_settings_new, color: Colors.white, size: 18),
          ),
        ),
      ]),
    );
  }

  Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(6), border: Border.all(color: color.withOpacity(0.3))),
    child: Text(text, style: TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: color)),
  );

  // ── Map view ──
  Widget _mapView() {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0D1117),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF1B2232)),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: LayoutBuilder(builder: (ctx, constraints) {
            return GestureDetector(
              onTapUp: (d) => _onMapTap(d, constraints),
              child: InteractiveViewer(
                transformationController: _transformCtrl,
                minScale: 0.5,
                maxScale: 5.0,
                child: _map == null
                    ? const Center(child: Text('Waiting for map data…', style: TextStyle(color: Color(0xFF3A4255))))
                    : CustomPaint(
                        size: Size(constraints.maxWidth, constraints.maxHeight),
                        painter: MapPainter(map: _map!, rooms: _rooms),
                      ),
              ),
            );
          }),
        ),
      ),
    );
  }

  // ── Bottom bar ──
  Widget _bottomBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: const BoxDecoration(
        color: Color(0xFF0D1117),
        border: Border(top: BorderSide(color: Color(0xFF1B2232))),
      ),
      child: Row(children: [
        // Mic
        GestureDetector(
          onTap: _isListening ? _stopListen : _listen,
          child: AnimatedBuilder(
            animation: _pulse,
            builder: (_, __) => Transform.scale(
              scale: _isListening ? _pulse.value : 1.0,
              child: Container(
                width: 48, height: 48,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: _isListening ? [const Color(0xFFFF4757), const Color(0xFFFFB347)] : [const Color(0xFF7B6EF6), const Color(0xFF5548D9)],
                  ),
                  boxShadow: [BoxShadow(color: (_isListening ? const Color(0xFFFF4757) : const Color(0xFF7B6EF6)).withOpacity(0.35), blurRadius: 14)],
                ),
                child: Icon(_isListening ? Icons.mic : Icons.mic_none, color: Colors.white, size: 22),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        // Recognized text / result
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(_recognized.isEmpty ? 'Voice command…' : _recognized,
              style: TextStyle(fontSize: 12, color: _recognized.isEmpty ? const Color(0xFF3A4255) : const Color(0xFFE8ECF4)),
              maxLines: 1, overflow: TextOverflow.ellipsis),
            if (_cmdResult.isNotEmpty)
              Text(_cmdResult, style: const TextStyle(fontSize: 10, color: Color(0xFF00E5A0)), maxLines: 1),
          ]),
        ),
        const SizedBox(width: 8),
        // D-pad
        ControlPad(
          onForward: () => _quick('move forward'),
          onBackward: () => _quick('move backward'),
          onLeft: () => _quick('turn left'),
          onRight: () => _quick('turn right'),
          onStop: _stop,
        ),
      ]),
    );
  }
}
