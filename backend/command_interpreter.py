"""
AI Command Interpreter — rule-based NLP for wheelchair commands.

Parses natural language into structured intents:
  navigate:<room>    — go to a named room
  move:<direction>   — manual movement
  stop               — stop motors
  scan               — start scanning
  status             — get status
  unknown            — unrecognised
"""
from utils import logger


# ── Intent patterns ──────────────────────────
# Ordered longest-first within each category for greedy matching.

NAVIGATE_PREFIXES = [
    "go to the ", "go to ", "navigate to the ", "navigate to ",
    "drive to the ", "drive to ", "take me to the ", "take me to ",
    "move to the ", "move to ", "head to the ", "head to ",
    "bring me to the ", "bring me to ",
]

MOVE_PATTERNS: dict[str, list[str]] = {
    "forward": [
        "move forward", "go forward", "go ahead", "go straight",
        "drive forward", "forward", "advance", "keep going",
    ],
    "backward": [
        "move backward", "move back", "go backward", "go back",
        "reverse", "backward", "back up",
    ],
    "left": [
        "turn left", "go left", "rotate left", "steer left", "left",
    ],
    "right": [
        "turn right", "go right", "rotate right", "steer right", "right",
    ],
}

STOP_PHRASES = [
    "stop now", "stop moving", "stop", "halt", "freeze", "brake",
    "emergency stop", "don't move", "stay", "hold", "pause",
]

SCAN_PHRASES = [
    "start scan", "scan area", "scan now", "scan",
    "look around", "check surroundings",
]

STATUS_PHRASES = [
    "status", "how are you", "what's happening", "state",
]


class CommandInterpreter:

    def __init__(self):
        # Pre-build flat move lookup (longest first)
        self._move_lookup: list[tuple[str, str]] = []
        for direction, phrases in MOVE_PATTERNS.items():
            for p in phrases:
                self._move_lookup.append((p.lower(), direction))
        self._move_lookup.sort(key=lambda x: len(x[0]), reverse=True)
        logger.info("CommandInterpreter ready")

    def interpret(self, text: str) -> dict:
        """
        Parse natural language → {intent, parameter, status}.

        Returns dict with:
          intent:    navigate | move | stop | scan | status | unknown
          parameter: room name or direction
          status:    ok
        """
        t = text.strip().lower()
        if not t:
            return {"intent": "unknown", "parameter": "", "status": "empty"}

        # 1. Navigation — "go to kitchen"
        for prefix in NAVIGATE_PREFIXES:
            if t.startswith(prefix):
                room = t[len(prefix):].strip().rstrip(".")
                if room:
                    logger.info("'%s' → navigate:%s", text, room)
                    return {"intent": "navigate", "parameter": room, "status": "ok"}

        # 2. Stop
        for p in STOP_PHRASES:
            if p in t:
                logger.info("'%s' → stop", text)
                return {"intent": "stop", "parameter": "", "status": "ok"}

        # 3. Movement
        for phrase, direction in self._move_lookup:
            if phrase in t:
                logger.info("'%s' → move:%s", text, direction)
                return {"intent": "move", "parameter": direction, "status": "ok"}

        # 4. Scan
        for p in SCAN_PHRASES:
            if p in t:
                logger.info("'%s' → scan", text)
                return {"intent": "scan", "parameter": "", "status": "ok"}

        # 5. Status
        for p in STATUS_PHRASES:
            if p in t:
                return {"intent": "status", "parameter": "", "status": "ok"}

        logger.info("'%s' → unknown", text)
        return {"intent": "unknown", "parameter": "", "status": "unrecognised"}
