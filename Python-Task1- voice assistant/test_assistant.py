"""Test suite to verify IntentParser and assistant core logic."""
from assistant import IntentParser, load_config

def test_intent_parsing():
    cfg = load_config("config.json")
    parser = IntentParser(cfg["custom_commands"])

    test_cases = [
        ("hello there", "greeting"),
        ("good morning", "greeting"),
        ("what is the current time", "time"),
        ("what's the time", "time"),
        ("what is today's date", "date"),
        ("tell me the date", "date"),
        ("search the web for quantum computing", "web_search"),
        ("google python tutorials", "web_search"),
        ("what's the weather like in Paris", "weather"),
        ("weather in Tokyo", "weather"),
        ("check the weather", "weather"),
        ("remind me to stretch in 5 minutes", "reminder"),
        ("set a reminder for 10 seconds to drink water", "reminder"),
        ("remind me in 1 hour to join the team sync", "reminder"),
        ("who is Alan Turing", "wikipedia"),
        ("what is machine learning", "wikipedia"),
        ("tell me about Mars", "wikipedia"),
        ("send an email", "email"),
        ("compose an email", "email"),
        ("who made you", "custom"),
        ("tell me a joke", "custom"),
        ("what is your mission", "custom"),
        ("stop listening", "shutdown"),
        ("shut down", "shutdown"),
        ("goodbye", "shutdown"),
        ("quit", "shutdown"),
    ]

    all_passed = True
    for phrase, expected_intent in test_cases:
        result = parser.parse(phrase)
        actual = result["intent"]
        passed = actual == expected_intent
        print(f"[{'PASS' if passed else 'FAIL'}] '{phrase}' -> Expected: {expected_intent}, Got: {actual}")
        if not passed:
            all_passed = False
            print(f"   Payload: {result}")

    assert all_passed, "One or more intent test cases failed!"
    print("\nAll 24 test cases passed successfully!")

if __name__ == "__main__":
    test_intent_parsing()
