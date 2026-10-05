"""Automated validation of ContinuousVoiceAssistant and action handlers."""
import time
from assistant import ContinuousVoiceAssistant

def test_assistant_actions():
    print("Initializing ContinuousVoiceAssistant in text mode...")
    app = ContinuousVoiceAssistant(config_file="config.json", text_mode=True)
    app.start()
    
    # 1. Test direct time and date
    print("\n--- Testing Direct Time & Date ---")
    app.action_handler.handle_time()
    app.action_handler.handle_date()

    # 2. Test custom response
    print("\n--- Testing Custom Commands ---")
    app.action_handler.handle_custom("This is a custom response test.")

    # 3. Test non-blocking reminder
    print("\n--- Testing Non-Blocking Reminder Timer ---")
    app.action_handler.handle_reminder(task="Drink a glass of water", seconds=2, duration_text="2 seconds")
    print("Waiting 3 seconds for reminder thread to fire...")
    time.sleep(3)

    # 4. Test Wikipedia lookup
    print("\n--- Testing Wikipedia Summary ---")
    app.action_handler.handle_wikipedia("Python (programming language)")

    # 5. Test Weather API placeholder handling
    print("\n--- Testing Weather API Placeholder Notice ---")
    app.action_handler.handle_weather(city="Paris")

    # 6. Test Email credentials placeholder notice
    print("\n--- Testing Email Credentials Placeholder Notice ---")
    app.action_handler.handle_email(recipient="alice@example.com", subject="Meeting", message="Hello")

    # 7. Test Asynchronous Command Queue & Multi-Turn Email State Machine
    print("\n--- Testing Asynchronous Command Queue & Email State Machine ---")
    app.command_queue.put("send an email")
    time.sleep(0.5)
    app.command_queue.put("test.user@example.com")
    time.sleep(0.5)
    app.command_queue.put("Weekly update")
    time.sleep(0.5)
    app.command_queue.put("Everything is running smoothly.")
    time.sleep(1.0)

    # 8. Clean shutdown
    print("\n--- Testing Clean Shutdown via Dispatcher ---")
    app.command_queue.put("stop listening")
    time.sleep(1.0)
    app.stop()
    print("All action handler and continuous background tests completed successfully!")

if __name__ == "__main__":
    test_assistant_actions()
