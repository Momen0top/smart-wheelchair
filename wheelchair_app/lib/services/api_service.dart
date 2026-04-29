import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

/// REST client for the SmartChair backend.
class ApiService {
  String baseUrl;
  final Duration timeout;

  ApiService({required this.baseUrl, this.timeout = const Duration(seconds: 5)});

  Uri _u(String p) => Uri.parse('$baseUrl$p');
  Map<String, String> get _h => {'Content-Type': 'application/json', 'Accept': 'application/json'};

  // ── Status ──
  Future<Map<String, dynamic>> getStatus() async {
    final r = await http.get(_u('/status'), headers: _h).timeout(timeout);
    if (r.statusCode == 200) return jsonDecode(r.body);
    throw Exception('Status ${r.statusCode}');
  }

  // ── Map ──
  Future<MapData> getMap() async {
    final r = await http.get(_u('/map'), headers: _h).timeout(timeout);
    if (r.statusCode == 200) return MapData.fromJson(jsonDecode(r.body));
    throw Exception('Map ${r.statusCode}');
  }

  // ── Scan ──
  Future<List<ScanPoint>> getScan() async {
    final r = await http.get(_u('/scan'), headers: _h).timeout(timeout);
    if (r.statusCode == 200) {
      final data = jsonDecode(r.body)['data'] as List;
      return data.map((e) => ScanPoint.fromJson(e)).toList();
    }
    throw Exception('Scan ${r.statusCode}');
  }

  // ── Rooms ──
  Future<List<Room>> getRooms() async {
    final r = await http.get(_u('/rooms'), headers: _h).timeout(timeout);
    if (r.statusCode == 200) {
      return (jsonDecode(r.body) as List).map((e) => Room.fromJson(e)).toList();
    }
    throw Exception('Rooms ${r.statusCode}');
  }

  Future<Room> createRoom(String name, double x, double y) async {
    final r = await http.post(_u('/rooms'), headers: _h,
        body: jsonEncode({'name': name, 'x': x, 'y': y})).timeout(timeout);
    if (r.statusCode == 200) return Room.fromJson(jsonDecode(r.body));
    throw Exception('Create room ${r.statusCode}');
  }

  Future<void> deleteRoom(String name) async {
    await http.delete(_u('/rooms/$name'), headers: _h).timeout(timeout);
  }

  // ── Navigate ──
  Future<Map<String, dynamic>> navigate(String roomName) async {
    final r = await http.post(_u('/navigate'), headers: _h,
        body: jsonEncode({'room_name': roomName})).timeout(timeout);
    if (r.statusCode == 200) return jsonDecode(r.body);
    throw Exception('Navigate ${r.statusCode}');
  }

  // ── Command ──
  Future<Map<String, dynamic>> sendCommand(String text) async {
    final r = await http.post(_u('/command'), headers: _h,
        body: jsonEncode({'text': text})).timeout(timeout);
    if (r.statusCode == 200) return jsonDecode(r.body);
    throw Exception('Command ${r.statusCode}');
  }

  // ── Stop ──
  Future<void> sendStop() async {
    await http.post(_u('/stop'), headers: _h).timeout(timeout);
  }

  // ── Pairing ──
  Future<PairingInfo> getPairingInfo() async {
    final r = await http.get(_u('/pairing/info'), headers: _h).timeout(timeout);
    if (r.statusCode == 200) return PairingInfo.fromJson(jsonDecode(r.body));
    throw Exception('Pairing ${r.statusCode}');
  }
}
