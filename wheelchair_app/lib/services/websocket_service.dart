import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/models.dart';

/// Live map stream via WebSocket.
class WebSocketService {
  WebSocketChannel? _channel;
  final _mapController = StreamController<MapData>.broadcast();
  Timer? _reconnectTimer;
  String _wsUrl = '';

  Stream<MapData> get mapStream => _mapController.stream;

  void connect(String baseUrl) {
    final host = Uri.parse(baseUrl).host;
    final port = Uri.parse(baseUrl).port;
    _wsUrl = 'ws://$host:$port/ws/map';
    _doConnect();
  }

  void _doConnect() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(_wsUrl));
      _channel!.stream.listen(
        (data) {
          try {
            final json = jsonDecode(data as String);
            if (json['type'] == 'map') {
              _mapController.add(MapData.fromJson(json));
            }
          } catch (_) {}
        },
        onDone: _onDisconnect,
        onError: (_) => _onDisconnect(),
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _onDisconnect() {
    _channel = null;
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), _doConnect);
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    disconnect();
    _mapController.close();
  }
}
