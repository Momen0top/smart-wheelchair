import 'package:flutter/material.dart';

/// Dialog for naming a tapped map location.
class RoomDialog extends StatefulWidget {
  final double x;
  final double y;
  const RoomDialog({super.key, required this.x, required this.y});

  @override
  State<RoomDialog> createState() => _RoomDialogState();
}

class _RoomDialogState extends State<RoomDialog> {
  final _ctrl = TextEditingController();

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF121829),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: const Text('Name This Location', style: TextStyle(color: Colors.white, fontSize: 18)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        Text('Coordinates: (${widget.x.toStringAsFixed(0)}, ${widget.y.toStringAsFixed(0)})',
          style: const TextStyle(color: Color(0xFF6B7688), fontSize: 12)),
        const SizedBox(height: 14),
        TextField(
          controller: _ctrl,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: 'e.g. Kitchen, Bedroom',
            hintStyle: const TextStyle(color: Color(0xFF3A4255)),
            filled: true,
            fillColor: const Color(0xFF0D1117),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          ),
        ),
      ]),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel', style: TextStyle(color: Color(0xFF6B7688))),
        ),
        ElevatedButton(
          onPressed: () {
            final name = _ctrl.text.trim();
            if (name.isNotEmpty) Navigator.pop(context, name);
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF7B6EF6),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: const Text('Save', style: TextStyle(color: Colors.white)),
        ),
      ],
    );
  }
}
