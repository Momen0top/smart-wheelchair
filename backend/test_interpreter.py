"""
Command Interpreter tests — runs without hardware.
"""
from command_interpreter import CommandInterpreter


def main():
    ci = CommandInterpreter()
    tests = [
        # Navigation
        ("go to kitchen", "navigate", "kitchen"),
        ("go to the bedroom", "navigate", "bedroom"),
        ("navigate to bathroom", "navigate", "bathroom"),
        ("take me to the living room", "navigate", "living room"),
        ("drive to garage", "navigate", "garage"),
        # Movement
        ("move forward", "move", "forward"),
        ("go ahead", "move", "forward"),
        ("go back", "move", "backward"),
        ("reverse", "move", "backward"),
        ("turn left", "move", "left"),
        ("turn right", "move", "right"),
        # Stop
        ("stop now", "stop", ""),
        ("halt", "stop", ""),
        ("emergency stop", "stop", ""),
        # Scan
        ("scan area", "scan", ""),
        ("look around", "scan", ""),
        # Status
        ("status", "status", ""),
        # Unknown
        ("hello world", "unknown", ""),
        ("do a dance", "unknown", ""),
        ("", "unknown", ""),
    ]

    passed = failed = 0
    for text, exp_intent, exp_param in tests:
        r = ci.interpret(text)
        ok = r["intent"] == exp_intent and r["parameter"] == exp_param
        icon = "✅" if ok else "❌"
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  {icon} \"{text}\" → {r['intent']}:{r['parameter']}  (expected {exp_intent}:{exp_param})")
            continue
        print(f"  {icon} \"{text}\" → {r['intent']}:{r['parameter']}")

    print(f"\nResults: {passed} passed, {failed} failed, {passed+failed} total")


if __name__ == "__main__":
    main()
