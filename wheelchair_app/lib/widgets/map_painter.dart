import 'dart:math';
import 'package:flutter/material.dart';
import '../models/models.dart';

/// Paints the occupancy grid map with robot position and room labels.
class MapPainter extends CustomPainter {
  final MapData map;
  final List<Room> rooms;

  MapPainter({required this.map, required this.rooms});

  @override
  void paint(Canvas canvas, Size size) {
    if (map.cells.isEmpty) return;

    final rows = map.cells.length;
    final cols = map.cells[0].length;
    final cellW = size.width / cols;
    final cellH = size.height / rows;
    final cellSize = min(cellW, cellH);

    // ── Draw grid cells ──
    for (int y = 0; y < rows; y++) {
      for (int x = 0; x < cols; x++) {
        final v = map.cells[y][x];
        Color color;
        if (v == 1) {
          color = const Color(0xFFFF4757); // occupied → red
        } else if (v == 0) {
          color = const Color(0xFF1A2038); // free → dark
        } else {
          color = const Color(0xFF0D1117); // unknown → background
        }
        canvas.drawRect(
          Rect.fromLTWH(x * cellSize, y * cellSize, cellSize, cellSize),
          Paint()..color = color,
        );
      }
    }

    // ── Draw room labels ──
    for (final room in rooms) {
      final gx = room.x / map.resolution + cols / 2;
      final gy = room.y / map.resolution + rows / 2;
      final px = gx * cellSize;
      final py = gy * cellSize;

      // Pin dot
      canvas.drawCircle(Offset(px, py), 5, Paint()..color = const Color(0xFFFFB347));
      canvas.drawCircle(Offset(px, py), 8, Paint()..color = const Color(0xFFFFB347).withOpacity(0.3));

      // Label
      final tp = TextPainter(
        text: TextSpan(
          text: room.name,
          style: const TextStyle(color: Color(0xFFFFB347), fontSize: 10, fontWeight: FontWeight.w600),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(px + 10, py - 6));
    }

    // ── Robot position ──
    final rx = (map.robotX / map.resolution + cols / 2) * cellSize;
    final ry = (map.robotY / map.resolution + rows / 2) * cellSize;

    // Robot body
    canvas.drawCircle(Offset(rx, ry), 6, Paint()..color = const Color(0xFF7B6EF6));
    canvas.drawCircle(Offset(rx, ry), 10, Paint()..color = const Color(0xFF7B6EF6).withOpacity(0.25));

    // Direction arrow
    const arrowLen = 14.0;
    final ax = rx + arrowLen * cos(map.robotYaw);
    final ay = ry + arrowLen * sin(map.robotYaw);
    canvas.drawLine(
      Offset(rx, ry),
      Offset(ax, ay),
      Paint()
        ..color = const Color(0xFF7B6EF6)
        ..strokeWidth = 2
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant MapPainter old) => true;
}
