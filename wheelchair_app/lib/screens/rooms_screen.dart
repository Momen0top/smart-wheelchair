import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';

/// Room list screen — shows all saved rooms with "Go" buttons.
class RoomsScreen extends StatefulWidget {
  final ApiService api;
  const RoomsScreen({super.key, required this.api});

  @override
  State<RoomsScreen> createState() => _RoomsScreenState();
}

class _RoomsScreenState extends State<RoomsScreen> {
  List<Room> _rooms = [];
  String _status = '';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final r = await widget.api.getRooms();
      if (mounted) setState(() => _rooms = r);
    } catch (_) {}
  }

  Future<void> _navigate(Room room) async {
    setState(() => _status = 'Navigating to ${room.name}…');
    try {
      await widget.api.navigate(room.name);
      setState(() => _status = '→ ${room.name}');
    } catch (e) {
      setState(() => _status = 'Error: $e');
    }
  }

  Future<void> _delete(Room room) async {
    try {
      await widget.api.deleteRoom(room.name);
      _load();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF06080F),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // Header
            Row(children: [
              const Icon(Icons.room, color: Color(0xFFFFB347), size: 22),
              const SizedBox(width: 8),
              const Text('Rooms', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Color(0xFFE8ECF4))),
              const Spacer(),
              if (_status.isNotEmpty) _statusChip(),
            ]),
            const SizedBox(height: 16),

            // Room list
            Expanded(
              child: _rooms.isEmpty
                  ? const Center(child: Text('No rooms saved.\nTap on the map to create one.',
                      textAlign: TextAlign.center, style: TextStyle(color: Color(0xFF3A4255), fontSize: 14)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        itemCount: _rooms.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _roomCard(_rooms[i]),
                      ),
                    ),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _statusChip() => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(
      color: const Color(0xFF00E5A0).withOpacity(0.1),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: const Color(0xFF00E5A0).withOpacity(0.3)),
    ),
    child: Text(_status, style: const TextStyle(fontSize: 10, color: Color(0xFF00E5A0), fontWeight: FontWeight.w600)),
  );

  Widget _roomCard(Room room) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1117),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1B2232)),
      ),
      child: Row(children: [
        Container(
          width: 40, height: 40,
          decoration: BoxDecoration(
            color: const Color(0xFFFFB347).withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.location_on, color: Color(0xFFFFB347), size: 20),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(room.name[0].toUpperCase() + room.name.substring(1),
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFFE8ECF4))),
          Text('(${room.x.toStringAsFixed(0)}, ${room.y.toStringAsFixed(0)})',
            style: const TextStyle(fontSize: 11, color: Color(0xFF6B7688))),
        ])),
        // Navigate
        GestureDetector(
          onTap: () => _navigate(room),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF7B6EF6), Color(0xFF5548D9)]),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Text('Go', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
          ),
        ),
        const SizedBox(width: 8),
        // Delete
        GestureDetector(
          onTap: () => _delete(room),
          child: Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFFFF4757).withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.delete_outline, color: Color(0xFFFF4757), size: 18),
          ),
        ),
      ]),
    );
  }
}
