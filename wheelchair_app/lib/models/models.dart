/// Data models shared across the Flutter app.
library;

class ScanPoint {
  final double angle;
  final double distance;
  ScanPoint({required this.angle, required this.distance});

  factory ScanPoint.fromJson(Map<String, dynamic> j) =>
      ScanPoint(angle: (j['angle'] as num).toDouble(), distance: (j['distance'] as num).toDouble());
}

class Room {
  final String name;
  final double x;
  final double y;
  Room({required this.name, required this.x, required this.y});

  factory Room.fromJson(Map<String, dynamic> j) =>
      Room(name: j['name'] as String, x: (j['x'] as num).toDouble(), y: (j['y'] as num).toDouble());
}

class MapData {
  final int width;
  final int height;
  final double resolution;
  final double robotX;
  final double robotY;
  final double robotYaw;
  final List<List<int>> cells;

  MapData({
    required this.width,
    required this.height,
    required this.resolution,
    required this.robotX,
    required this.robotY,
    required this.robotYaw,
    required this.cells,
  });

  factory MapData.fromJson(Map<String, dynamic> j) => MapData(
        width: j['width'] as int,
        height: j['height'] as int,
        resolution: (j['resolution'] as num).toDouble(),
        robotX: (j['robot_x'] as num? ?? 0).toDouble(),
        robotY: (j['robot_y'] as num? ?? 0).toDouble(),
        robotYaw: (j['robot_yaw'] as num? ?? 0).toDouble(),
        cells: (j['cells'] as List).map((row) => (row as List).map((c) => c as int).toList()).toList(),
      );
}

class PairingInfo {
  final String robotId;
  final String ip;
  final int port;
  PairingInfo({required this.robotId, required this.ip, required this.port});

  factory PairingInfo.fromJson(Map<String, dynamic> j) => PairingInfo(
        robotId: j['robot_id'] as String,
        ip: j['ip'] as String,
        port: j['port'] as int,
      );

  String get baseUrl => 'http://$ip:$port';
}
