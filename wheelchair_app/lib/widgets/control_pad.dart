import 'package:flutter/material.dart';

/// D-pad manual control widget.
class ControlPad extends StatelessWidget {
  final VoidCallback onForward;
  final VoidCallback onBackward;
  final VoidCallback onLeft;
  final VoidCallback onRight;
  final VoidCallback onStop;

  const ControlPad({
    super.key,
    required this.onForward,
    required this.onBackward,
    required this.onLeft,
    required this.onRight,
    required this.onStop,
  });

  @override
  Widget build(BuildContext context) {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      _btn(Icons.keyboard_arrow_up, onForward, const Color(0xFF7B6EF6)),
      const SizedBox(height: 4),
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        _btn(Icons.keyboard_arrow_left, onLeft, const Color(0xFF7B6EF6)),
        const SizedBox(width: 4),
        _btn(Icons.stop_rounded, onStop, const Color(0xFFFF4757)),
        const SizedBox(width: 4),
        _btn(Icons.keyboard_arrow_right, onRight, const Color(0xFF7B6EF6)),
      ]),
      const SizedBox(height: 4),
      _btn(Icons.keyboard_arrow_down, onBackward, const Color(0xFF7B6EF6)),
    ]);
  }

  Widget _btn(IconData icon, VoidCallback onTap, Color color) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56, height: 48,
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.25)),
        ),
        child: Icon(icon, color: color, size: 26),
      ),
    );
  }
}
