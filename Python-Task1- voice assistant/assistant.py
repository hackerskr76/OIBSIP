import datetime
import json
import os
import queue
import re
import smtplib
import sys
import threading
import time
import urllib.parse
import webbrowser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pyttsx3
import requests
import speech_recognition as sr
import wikipedia


def load_config(config_path="config.json"):
    default_config = {
        "assistant_name": "Aura",
        "voice_gender": "female",
        "speech_rate": 185,
        "volume": 1.0,
        "phrase_time_limit": 8,
        "energy_threshold": 300,
        "dynamic_energy_threshold": True,
        "openweathermap": {
            "api_key": "YOUR_OPENWEATHERMAP_API_KEY",
            "default_city": "London",
            "units": "metric",
        },
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "your_email@gmail.com",
            "sender_password": "your_app_password",
        },
        "custom_commands": {
            "who made you": "I was designed and coded by an expert Python engineer.",
            "what is your mission": "My mission is to assist you with your daily computing tasks.",
            "tell me a joke": "Why do programmers prefer dark mode? Because light attracts bugs!",
            "how are you": "I am functioning at full capacity in background listening mode!",
            "what can you do": "I run as a background agent and can check the weather, look up Wikipedia, search the web, tell the time and date, set reminders, send emails, and answer your custom questions.",
        },
    }

    if not os.path.exists(config_path):
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
        except OSError:
            pass
        return default_config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            default_config.update(user_config)
            return default_config
    except (json.JSONDecodeError, OSError):
        return default_config


class TextToSpeechManager:
    def __init__(self, voice_gender="female", rate=185, volume=1.0):
        self.rate = rate
        self.volume = volume
        self.voice_gender = voice_gender.lower()
        self._speech_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._speaking_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _init_engine(self):
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            voices = engine.getProperty("voices")
            if voices:
                selected_voice = voices[0].id
                for voice in voices:
                    name_lower = voice.name.lower()
                    if self.voice_gender in name_lower or (
                        "zira" in name_lower and self.voice_gender == "female"
                    ) or (
                        "david" in name_lower and self.voice_gender == "male"
                    ):
                        selected_voice = voice.id
                        break
                engine.setProperty("voice", selected_voice)
            return engine
        except Exception:
            return None

    def _speech_worker(self):
        engine = self._init_engine()
        while not self._stop_event.is_set():
            try:
                task = self._speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            text, done_event = task
            if text is None:
                self._speech_queue.task_done()
                break

            print(f"\n[Assistant]: {text}")
            self._speaking_event.set()
            if engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    engine = self._init_engine()

            time.sleep(0.3)
            self._speaking_event.clear()

            if done_event:
                done_event.set()
            self._speech_queue.task_done()

    def is_speaking(self):
        return self._speaking_event.is_set()

    def speak(self, text, block=True):
        if not text or not str(text).strip():
            return
        text = str(text).strip()
        done_event = threading.Event() if block else None
        self._speech_queue.put((text, done_event))
        if block and done_event:
            done_event.wait()

    def stop(self):
        self._stop_event.set()
        self._speech_queue.put((None, None))


class IntentParser:
    INTENT_GREETING = "greeting"
    INTENT_TIME = "time"
    INTENT_DATE = "date"
    INTENT_WEB_SEARCH = "web_search"
    INTENT_WEATHER = "weather"
    INTENT_REMINDER = "reminder"
    INTENT_WIKIPEDIA = "wikipedia"
    INTENT_EMAIL = "email"
    INTENT_CUSTOM = "custom"
    INTENT_SHUTDOWN = "shutdown"
    INTENT_UNKNOWN = "unknown"

    def __init__(self, custom_commands=None):
        self.custom_commands = custom_commands or {}
        self.re_shutdown = re.compile(
            r"\b(stop listening|shut down|shutdown|turn off|terminate|quit|exit|goodbye|bye|go to sleep)\b",
            re.IGNORECASE,
        )
        self.re_greeting = re.compile(
            r"\b(hello|hi|hey|good morning|good afternoon|good evening|howdy|greetings|welcome)\b",
            re.IGNORECASE,
        )
        self.re_time = re.compile(
            r"\b(what(?:'s| is)? the time|tell me the time|current time|what time is it|time please)\b",
            re.IGNORECASE,
        )
        self.re_date = re.compile(
            r"\b(what(?:'s| is)? (?:today'?s )?date|tell me the date|current date|what day is (?:it )?today|today'?s date)\b",
            re.IGNORECASE,
        )
        self.re_search = re.compile(
            r"^(?:please\s+)?(?:search(?: the web| google)? for|look up|google|find online|search)\s+(.+)$",
            re.IGNORECASE,
        )
        self.re_weather_city = re.compile(
            r"\b(?:weather in|weather of|weather for|weather at|weather like in|forecast for)\s+([a-zA-Z\s]+)",
            re.IGNORECASE,
        )
        self.re_weather_general = re.compile(
            r"\b(weather|forecast|temperature|how is the weather|what's the weather|is it raining)\b",
            re.IGNORECASE,
        )
        self.re_reminder_type_1 = re.compile(
            r"remind me to\s+(.+?)\s+in\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(seconds?|secs?|minutes?|mins?|hours?|hrs?)",
            re.IGNORECASE,
        )
        self.re_reminder_type_2 = re.compile(
            r"(?:set|create)(?:\s+a)?\s+(?:reminder|timer)\s+(?:for|in)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(seconds?|secs?|minutes?|mins?|hours?|hrs?)(?:\s+to\s+(.+))?",
            re.IGNORECASE,
        )
        self.re_reminder_type_3 = re.compile(
            r"remind me in\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(seconds?|secs?|minutes?|mins?|hours?|hrs?)\s+to\s+(.+)",
            re.IGNORECASE,
        )
        self.re_wiki = re.compile(
            r"^(?:who is|who was|what is|what was|tell me about|explain|define|wikipedia|info on|information about)\s+(.+)$",
            re.IGNORECASE,
        )
        self.re_email = re.compile(
            r"\b(send(?: an)? email|compose(?: an)? email|send mail|write an email)\b",
            re.IGNORECASE,
        )

    @staticmethod
    def _parse_duration(number_str, unit_str):
        word_map = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        val = word_map.get(number_str.lower(), None)
        if val is None:
            try:
                val = int(number_str)
            except ValueError:
                val = 10

        unit = unit_str.lower()
        if "sec" in unit:
            seconds = val
            duration_text = f"{val} second{'s' if val != 1 else ''}"
        elif "min" in unit:
            seconds = val * 60
            duration_text = f"{val} minute{'s' if val != 1 else ''}"
        elif "hour" in unit or "hr" in unit:
            seconds = val * 3600
            duration_text = f"{val} hour{'s' if val != 1 else ''}"
        else:
            seconds = val
            duration_text = f"{val} seconds"

        return seconds, duration_text

    def parse(self, text):
        clean_text = text.strip()

        if self.re_shutdown.search(clean_text):
            return {"intent": self.INTENT_SHUTDOWN, "raw": clean_text}

        lower_text = clean_text.lower()
        for trigger, response in self.custom_commands.items():
            if trigger.lower() in lower_text or lower_text in trigger.lower():
                return {"intent": self.INTENT_CUSTOM, "response": response, "raw": clean_text}

        m = self.re_reminder_type_1.search(clean_text)
        if m:
            task, num, unit = m.group(1).strip(), m.group(2), m.group(3)
            seconds, duration_text = self._parse_duration(num, unit)
            return {
                "intent": self.INTENT_REMINDER,
                "task": task,
                "seconds": seconds,
                "duration_text": duration_text,
                "raw": clean_text,
            }

        m = self.re_reminder_type_2.search(clean_text)
        if m:
            num, unit, task = m.group(1), m.group(2), m.group(3)
            task = task.strip() if task else "Timer finished"
            seconds, duration_text = self._parse_duration(num, unit)
            return {
                "intent": self.INTENT_REMINDER,
                "task": task,
                "seconds": seconds,
                "duration_text": duration_text,
                "raw": clean_text,
            }

        m = self.re_reminder_type_3.search(clean_text)
        if m:
            num, unit, task = m.group(1), m.group(2), m.group(3).strip()
            seconds, duration_text = self._parse_duration(num, unit)
            return {
                "intent": self.INTENT_REMINDER,
                "task": task,
                "seconds": seconds,
                "duration_text": duration_text,
                "raw": clean_text,
            }

        m = self.re_weather_city.search(clean_text)
        if m:
            return {"intent": self.INTENT_WEATHER, "city": m.group(1).strip(), "raw": clean_text}

        if self.re_weather_general.search(clean_text):
            return {"intent": self.INTENT_WEATHER, "city": None, "raw": clean_text}

        if self.re_time.search(clean_text):
            return {"intent": self.INTENT_TIME, "raw": clean_text}

        if self.re_date.search(clean_text):
            return {"intent": self.INTENT_DATE, "raw": clean_text}

        m = self.re_search.match(clean_text)
        if m:
            return {"intent": self.INTENT_WEB_SEARCH, "query": m.group(1).strip(), "raw": clean_text}

        m = self.re_wiki.match(clean_text)
        if m:
            return {"intent": self.INTENT_WIKIPEDIA, "topic": m.group(1).strip(), "raw": clean_text}

        if self.re_email.search(clean_text):
            return {"intent": self.INTENT_EMAIL, "raw": clean_text}

        if self.re_greeting.search(clean_text):
            return {"intent": self.INTENT_GREETING, "raw": clean_text}

        return {"intent": self.INTENT_UNKNOWN, "raw": clean_text}


class ActionHandler:
    def __init__(self, config, tts):
        self.config = config
        self.tts = tts
        self._active_timers = []
        try:
            wikipedia.set_user_agent("VoiceAssistant/2.0 (ContinuousBackgroundAgent)")
        except Exception:
            pass

    def handle_greeting(self):
        hour = datetime.datetime.now().hour
        period = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
        name = self.config.get("assistant_name", "Aura")
        self.tts.speak(f"{period}! I am {name}. I am listening in the background. How can I help?")

    def handle_time(self):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        self.tts.speak(f"The current time is {current_time}.")

    def handle_date(self):
        current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
        self.tts.speak(f"Today is {current_date}.")

    def handle_web_search(self, query):
        self.tts.speak(f"Searching the web for {query}.")
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        try:
            webbrowser.open(search_url)
            time.sleep(0.5)
            self.tts.speak("I have opened the search results in your default browser.")
        except Exception:
            self.tts.speak("I encountered an error trying to open your web browser.")

    def handle_weather(self, city=None):
        weather_cfg = self.config.get("openweathermap", {})
        api_key = weather_cfg.get("api_key", "").strip()
        target_city = city or weather_cfg.get("default_city", "London")
        units = weather_cfg.get("units", "metric")
        unit_label = "Celsius" if units == "metric" else "Fahrenheit"

        if not api_key or api_key == "YOUR_OPENWEATHERMAP_API_KEY":
            self.tts.speak(
                "OpenWeatherMap API key is not configured. "
                "Please add your free API key to config.json to check live weather."
            )
            return

        self.tts.speak(f"Checking live weather for {target_city}...")
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": target_city, "appid": api_key, "units": units}

        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            if response.status_code == 200:
                desc = data["weather"][0]["description"]
                temp = round(data["main"]["temp"])
                feels_like = round(data["main"]["feels_like"])
                humidity = data["main"]["humidity"]
                self.tts.speak(
                    f"The weather in {target_city} is currently {desc} "
                    f"with a temperature of {temp} degrees {unit_label}, "
                    f"feeling like {feels_like} degrees. Humidity is at {humidity} percent."
                )
            elif response.status_code == 404:
                self.tts.speak(f"Sorry, I could not find weather data for the city {target_city}.")
            elif response.status_code == 401:
                self.tts.speak("Authentication failed. Your OpenWeatherMap API key appears to be invalid.")
            else:
                self.tts.speak("Unable to retrieve weather data at this moment.")
        except requests.RequestException:
            self.tts.speak("I could not reach the weather service. Please check your internet connection.")

    def handle_reminder(self, task, seconds, duration_text):
        def trigger_alarm():
            self.tts.speak(f"Alert! This is your reminder to: {task}.", block=False)

        timer = threading.Timer(seconds, trigger_alarm)
        timer.daemon = True
        timer.start()
        self._active_timers.append(timer)
        self.tts.speak(f"Reminder set. I will alert you to '{task}' in {duration_text}.")

    def handle_wikipedia(self, topic):
        self.tts.speak(f"Searching Wikipedia for {topic}...")
        try:
            summary = wikipedia.summary(topic, sentences=2, auto_suggest=True)
            self.tts.speak(summary)
        except wikipedia.exceptions.DisambiguationError as de:
            options = de.options[:3]
            self.tts.speak(
                f"There are multiple topics matching {topic}, including {', '.join(options)}. "
                "Please specify which one you would like to know about."
            )
        except wikipedia.exceptions.PageError:
            self.tts.speak(f"I couldn't find any Wikipedia article matching '{topic}'.")
        except Exception:
            self.tts.speak("I encountered an issue fetching information from Wikipedia.")

    def send_email_smtp(self, recipient, subject, message_body):
        email_cfg = self.config.get("email", {})
        smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
        smtp_port = email_cfg.get("smtp_port", 587)
        sender_email = email_cfg.get("sender_email", "")
        sender_password = email_cfg.get("sender_password", "")

        if not sender_email or sender_email == "your_email@gmail.com":
            self.tts.speak(
                "Email credentials are not configured. "
                "Please configure your email and app password in config.json to send emails."
            )
            return False

        self.tts.speak(f"Sending email to {recipient} now.")
        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(message_body, "plain"))

            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            self.tts.speak("Your email has been sent successfully.")
            return True
        except smtplib.SMTPAuthenticationError:
            self.tts.speak("Authentication failed. Please verify your email and app password in config.json.")
            return False
        except Exception:
            self.tts.speak("Failed to send the email due to a connection or server error.")
            return False

    def handle_email(self, recipient="test@example.com", subject="Test Subject", message="Test message"):
        return self.send_email_smtp(recipient, subject, message)

    def handle_custom(self, response):
        self.tts.speak(response)

    def handle_unknown(self, raw_text):
        self.tts.speak(
            f"I didn't recognize a command for '{raw_text}'. "
            "You can ask me for the time, weather, Wikipedia search, or to set a reminder."
        )


class ContinuousVoiceAssistant:
    STATE_NORMAL = "NORMAL"
    STATE_EMAIL_RECIPIENT = "EMAIL_RECIPIENT"
    STATE_EMAIL_SUBJECT = "EMAIL_SUBJECT"
    STATE_EMAIL_BODY = "EMAIL_BODY"

    def __init__(self, config_file="config.json", text_mode=False):
        self.config = load_config(config_file)
        self.name = self.config.get("assistant_name", "Aura")
        self.text_mode = text_mode
        self.phrase_time_limit = self.config.get("phrase_time_limit", 8)
        self.energy_threshold = self.config.get("energy_threshold", 300)

        self.tts = TextToSpeechManager(
            voice_gender=self.config.get("voice_gender", "female"),
            rate=self.config.get("speech_rate", 185),
            volume=self.config.get("volume", 1.0),
        )
        self.parser = IntentParser(custom_commands=self.config.get("custom_commands", {}))
        self.action_handler = ActionHandler(config=self.config, tts=self.tts)

        self.dialogue_state = self.STATE_NORMAL
        self.email_context = {"recipient": "", "subject": "", "body": ""}
        self.command_queue = queue.Queue()
        self.is_running = threading.Event()
        self.stop_listening_fn = None

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.energy_threshold
        self.recognizer.dynamic_energy_threshold = self.config.get("dynamic_energy_threshold", True)
        self.recognizer.pause_threshold = 0.8
        self.microphone = None

        self.dispatcher_thread = threading.Thread(
            target=self._command_dispatcher, daemon=True, name="CommandDispatcher"
        )

    def _init_audio(self):
        if self.text_mode:
            return False
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            return True
        except Exception:
            self.text_mode = True
            return False

    def _audio_callback(self, recognizer, audio):
        if self.tts.is_speaking():
            return
        try:
            transcribed = recognizer.recognize_google(audio).strip().lower()
            print(f"[You (Voice)]: {transcribed}")
            self.command_queue.put(transcribed)
        except sr.UnknownValueError:
            if not self.tts.is_speaking():
                self.tts.speak("Sorry, I didn't catch that. Could you please repeat?")
        except sr.RequestError:
            if not self.tts.is_speaking():
                self.tts.speak("Speech recognition service is currently unavailable. Please check your internet connection.")
        except Exception:
            pass

    def _handle_email_state(self, utterance):
        if utterance in ["cancel", "stop", "abort", "nevermind", "cancel email"]:
            self.dialogue_state = self.STATE_NORMAL
            self.email_context = {"recipient": "", "subject": "", "body": ""}
            self.tts.speak("Email cancelled.")
            return

        if self.dialogue_state == self.STATE_EMAIL_RECIPIENT:
            recipient = (
                utterance.replace(" at the rate ", "@")
                .replace(" at ", "@")
                .replace(" dot ", ".")
                .replace(" ", "")
                .strip()
            )
            if "@" not in recipient or "." not in recipient:
                self.tts.speak(f"'{recipient}' does not appear to be a valid email. Please say the recipient email again, or say 'cancel'.")
                return
            self.email_context["recipient"] = recipient
            self.dialogue_state = self.STATE_EMAIL_SUBJECT
            self.tts.speak(f"Recipient set to {recipient}. What is the subject of the email?")

        elif self.dialogue_state == self.STATE_EMAIL_SUBJECT:
            self.email_context["subject"] = utterance
            self.dialogue_state = self.STATE_EMAIL_BODY
            self.tts.speak("Subject recorded. What message would you like to send?")

        elif self.dialogue_state == self.STATE_EMAIL_BODY:
            self.email_context["body"] = utterance
            self.dialogue_state = self.STATE_NORMAL
            self.action_handler.send_email_smtp(
                recipient=self.email_context["recipient"],
                subject=self.email_context["subject"],
                message_body=self.email_context["body"],
            )
            self.email_context = {"recipient": "", "subject": "", "body": ""}

    def _command_dispatcher(self):
        while self.is_running.is_set():
            try:
                utterance = self.command_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if utterance is None:
                self.command_queue.task_done()
                break

            if self.dialogue_state != self.STATE_NORMAL:
                self._handle_email_state(utterance)
                self.command_queue.task_done()
                continue

            parsed = self.parser.parse(utterance)
            intent = parsed.get("intent")

            if intent == IntentParser.INTENT_SHUTDOWN:
                self.tts.speak("Shutting down background listening. Goodbye!")
                self.stop()
            elif intent == IntentParser.INTENT_GREETING:
                self.action_handler.handle_greeting()
            elif intent == IntentParser.INTENT_TIME:
                self.action_handler.handle_time()
            elif intent == IntentParser.INTENT_DATE:
                self.action_handler.handle_date()
            elif intent == IntentParser.INTENT_WEB_SEARCH:
                self.action_handler.handle_web_search(parsed["query"])
            elif intent == IntentParser.INTENT_WEATHER:
                self.action_handler.handle_weather(parsed.get("city"))
            elif intent == IntentParser.INTENT_REMINDER:
                self.action_handler.handle_reminder(
                    task=parsed["task"],
                    seconds=parsed["seconds"],
                    duration_text=parsed["duration_text"],
                )
            elif intent == IntentParser.INTENT_WIKIPEDIA:
                self.action_handler.handle_wikipedia(parsed["topic"])
            elif intent == IntentParser.INTENT_EMAIL:
                self.dialogue_state = self.STATE_EMAIL_RECIPIENT
                self.email_context = {"recipient": "", "subject": "", "body": ""}
                self.tts.speak("Who would you like to send this email to?")
            elif intent == IntentParser.INTENT_CUSTOM:
                self.action_handler.handle_custom(parsed["response"])
            else:
                self.action_handler.handle_unknown(parsed.get("raw", utterance))

            self.command_queue.task_done()

    def start(self):
        self.is_running.set()
        self.dispatcher_thread.start()
        has_mic = self._init_audio()
        self.tts.speak(f"Hello! I am {self.name}, your voice assistant. Real-time background listening is active.")

        if has_mic and self.microphone:
            self.stop_listening_fn = self.recognizer.listen_in_background(
                source=self.microphone,
                callback=self._audio_callback,
                phrase_time_limit=self.phrase_time_limit,
            )
            print(f"[{self.name} is listening in the background]")
        else:
            print(f"[{self.name} running in Interactive Console Mode]")

    def run_console_loop(self):
        try:
            while self.is_running.is_set():
                user_input = input("[You]: ").strip()
                if user_input:
                    self.command_queue.put(user_input.lower())
                time.sleep(0.1)
        except (KeyboardInterrupt, EOFError):
            self.stop()

    def wait(self):
        try:
            while self.is_running.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        if not self.is_running.is_set():
            return
        self.is_running.clear()
        if self.stop_listening_fn:
            try:
                self.stop_listening_fn(wait_for_stop=False)
            except Exception:
                pass
        self.command_queue.put(None)
        self.tts.stop()

    def shutdown(self):
        self.stop()


VoiceAssistant = ContinuousVoiceAssistant

if __name__ == "__main__":
    use_text_mode = "--text-mode" in sys.argv
    app = ContinuousVoiceAssistant(config_file="config.json", text_mode=use_text_mode)
    app.start()
    if use_text_mode:
        app.run_console_loop()
    else:
        app.wait()
