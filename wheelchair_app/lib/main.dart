import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'models/models.dart';
import 'services/api_service.dart';
import 'services/websocket_service.dart';
import 'screens/map_screen.dart';
import 'screens/rooms_screen.dart';
import 'screens/pairing_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));
  runApp(const SmartChairApp());
}

class SmartChairApp extends StatelessWidget {
  const SmartChairApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartChair',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF06080F),
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF7B6EF6),
          secondary: const Color(0xFF00E5A0),
          surface: const Color(0xFF0D1117),
          error: const Color(0xFFFF4757),
        ),
      ),
      home: const AppShell(),
    );
  }
}

/// App shell — bottom navigation between Map, Rooms, Connect.
class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _tab = 0;

  // Default URL — updated by pairing screen
  String _baseUrl = 'http://192.168.1.100:8000';
  late ApiService _api;
  late WebSocketService _ws;

  @override
  void initState() {
    super.initState();
    _api = ApiService(baseUrl: _baseUrl);
    _ws = WebSocketService();
    _ws.connect(_baseUrl);
  }

  @override
  void dispose() {
    _ws.dispose();
    super.dispose();
  }

  void _onPaired(PairingInfo info) {
    setState(() {
      _baseUrl = info.baseUrl;
      _api = ApiService(baseUrl: _baseUrl);
      _ws.disconnect();
      _ws.connect(_baseUrl);
      _tab = 0; // switch to map
    });
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      MapScreen(api: _api, ws: _ws),
      RoomsScreen(api: _api),
      PairingScreen(onPaired: _onPaired),
    ];

    return Scaffold(
      body: IndexedStack(index: _tab, children: screens),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Color(0xFF0D1117),
          border: Border(top: BorderSide(color: Color(0xFF1B2232))),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
              _navItem(0, Icons.map, 'Map'),
              _navItem(1, Icons.room, 'Rooms'),
              _navItem(2, Icons.link, 'Connect'),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _navItem(int index, IconData icon, String label) {
    final active = _tab == index;
    final color = active ? const Color(0xFF7B6EF6) : const Color(0xFF3A4255);
    return GestureDetector(
      onTap: () => setState(() => _tab = index),
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 2),
          Text(label, style: TextStyle(fontSize: 10, color: color, fontWeight: active ? FontWeight.w600 : FontWeight.w400)),
        ]),
      ),
    );
  }
}
