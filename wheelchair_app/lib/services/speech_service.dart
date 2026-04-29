import 'package:speech_to_text/speech_to_text.dart' as stt;

/// Wrapper around speech_to_text for voice commands.
class SpeechService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _available = false;

  bool get isAvailable => _available;

  Future<void> init() async {
    _available = await _speech.initialize();
  }

  void listen({
    required Function(String text, bool isFinal) onResult,
    Function(String)? onError,
  }) {
    if (!_available) return;
    _speech.listen(
      onResult: (r) => onResult(r.recognizedWords, r.finalResult),
      listenFor: const Duration(seconds: 10),
      pauseFor: const Duration(seconds: 3),
    );
  }

  void stop() => _speech.stop();
  bool get isListening => _speech.isListening;
}
