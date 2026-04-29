import 'dart:convert';
import 'package:http/http.dart' as http;

/// Service class for communicating with the Smart Wheelchair backend API.
class ApiService {
  final String baseUrl;
  final Duration timeout;

  ApiService({
    required this.baseUrl,
    this.timeout = const Duration(seconds: 5),
  });

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  // ── GET /status ──
  Future<Map<String, dynamic>> getStatus() async {
    try {
      final r = await http.get(_uri('/status'), headers: _headers).timeout(timeout);
      if (r.statusCode == 200) return jsonDecode(r.body);
      throw ApiException('Status ${r.statusCode}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('$e');
    }
  }

  // ── GET /scan ──
  Future<Map<String, dynamic>> getScan() async {
    try {
      final r = await http.get(_uri('/scan'), headers: _headers).timeout(timeout);
      if (r.statusCode == 200) return jsonDecode(r.body);
      throw ApiException('Scan ${r.statusCode}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('$e');
    }
  }

  // ── GET /imu ──
  Future<Map<String, dynamic>> getIMU() async {
    try {
      final r = await http.get(_uri('/imu'), headers: _headers).timeout(timeout);
      if (r.statusCode == 200) return jsonDecode(r.body);
      throw ApiException('IMU ${r.statusCode}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('$e');
    }
  }

  // ── POST /command ──
  Future<Map<String, dynamic>> sendCommand(String text) async {
    try {
      final r = await http
          .post(_uri('/command'), headers: _headers, body: jsonEncode({'text': text}))
          .timeout(timeout);
      if (r.statusCode == 200) return jsonDecode(r.body);
      throw ApiException('Command ${r.statusCode}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('$e');
    }
  }

  // ── POST /stop ──
  Future<Map<String, dynamic>> sendStop() async {
    try {
      final r = await http.post(_uri('/stop'), headers: _headers).timeout(timeout);
      if (r.statusCode == 200) return jsonDecode(r.body);
      throw ApiException('Stop ${r.statusCode}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('$e');
    }
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => 'ApiException: $message';
}
