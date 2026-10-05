# Python Voice Assistant (Real-Time Background Listening Agent)

A production-ready Voice Assistant built in Python designed as a **continuous, non-blocking real-time background listening agent**. 

Unlike standard voice assistants that freeze your application in a blocking `while True: listen()` loop, this assistant utilizes `SpeechRecognition`'s asynchronous `listen_in_background()` daemon thread, coupled with a thread-safe text-to-speech output pipeline, an event-driven command dispatcher, and a conversational state machine.

---

## Table of Contents
1. [Features Checklist](#features-checklist)
   - [Beginner Tier](#beginner-tier)
   - [Advanced Tier](#advanced-tier)
   - [Modern Background Agent Architecture](#modern-background-agent-architecture)
2. [Agent Architecture & Concurrency Model](#agent-architecture--concurrency-model)
   - [Non-Blocking Audio Capture (`listen_in_background`)](#1-non-blocking-audio-capture-listen_in_background)
   - [Acoustic Feedback & Self-Echo Suppression](#2-acoustic-feedback--self-echo-suppression)
   - [Multi-Turn Dialogue State Machine (Voice Email)](#3-multi-turn-dialogue-state-machine-voice-email)
   - [Thread-Safe TTS Worker](#4-thread-safe-tts-worker)
3. [Prerequisites & Installation](#prerequisites--installation)
   - [PyAudio Platform Installation Guide](#pyaudio-platform-installation-guide)
4. [Configuration Guide (`config.json`)](#configuration-guide-configjson)
5. [Usage & Voice Commands](#usage--voice-commands)
   - [Background Voice Mode](#1-background-voice-mode-microphone)
   - [Interactive Console Mode](#2-interactive-console-mode-text-mode)
6. [Testing & Verification](#testing--verification)
7. [Privacy & Data Processing Disclosure](#privacy--data-processing-disclosure)
   - [Local (On-Device) Processing](#local-on-device-processing)
   - [Third-Party & Cloud Services](#third-party--cloud-services)
   - [Data Minimization & Security Recommendations](#data-minimization--security-recommendations)

---

## Features Checklist

### Beginner Tier
- [x] **Microphone Voice Capture**: Captures microphone input using `SpeechRecognition` with ambient noise calibration.
- [x] **Conversational Greetings**: Welcomes the user with a time-of-day greeting (Morning, Afternoon, Evening).
- [x] **Live Time & Date**: Accurate time and date announcements powered by Python's `datetime` module.
- [x] **Web Search Integration**: Extracts search topics from natural speech and launches Google search in the default web browser using `webbrowser`.
- [x] **Graceful Error Handling**: Detects uninterpretable speech (`UnknownValueError`) or network drops (`RequestError`) and prompts the user to repeat without crashing.
- [x] **Universal Text-to-Speech Feedback**: Employs `pyttsx3` for vocal feedback before and after every external action.

### Advanced Tier
- [x] **Natural Language Understanding (NLU)**: Regex-based intent classification and entity slot extraction that understands natural, free-form phrasing.
- [x] **Voice-Directed Email Dispatch**: Multi-turn voice dialogue to specify recipient, subject, and message via `smtplib` over TLS.
- [x] **Non-Blocking Timed Reminders**: Background thread timers (`threading.Timer`) trigger audible TTS alerts upon expiration without freezing the assistant.
- [x] **Live Weather Forecasts**: Real-time atmospheric conditions, temperature, and humidity fetched via OpenWeatherMap REST API.
- [x] **Wikipedia Knowledge Summaries**: Provides concise 1-2 sentence summaries from Wikipedia, with compliant User-Agent headers and disambiguation handling.
- [x] **Configurable Custom Commands**: User-defined trigger phrases and responses loaded dynamically from `config.json`.
- [x] **Privacy Transparency**: Detailed disclosure of data processed locally vs. sent to third parties.

### Modern Background Agent Architecture
- [x] **Non-Blocking Continuous Listening**: Uses `recognizer.listen_in_background(microphone, callback)` daemon thread instead of a blocking `while True: listen()` loop.
- [x] **Producer-Consumer Dispatch Queue**: Speech chunks are recognized in the background and placed onto an event-driven `command_queue` processed by a dedicated worker.
- [x] **Echo Cancellation / Self-Listening Prevention**: The audio callback automatically suppresses microphone input while the assistant is speaking (`is_speaking`), preventing feedback loops.

---

## Agent Architecture & Concurrency Model

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                      ContinuousVoiceAssistant Agent                         │
 │                                                                             │
 │  ┌─────────────────────────┐           ┌─────────────────────────────────┐  │
 │  │      Microphone         │           │        Main Application         │  │
 │  └───────────┬─────────────┘           │       (Non-blocking Thread)     │  │
 │              │ (Live Audio Stream)     └────────────────┬────────────────┘  │
 │              ▼                                          │                   │
 │  ┌───────────────────────────────┐                      │                   │
 │  │ listen_in_background (Daemon) │                      │ Keep-Alive / Wait │
 │  │  - adjust_for_ambient_noise   │                      ▼                   │
 │  │  - Energy Threshold Checking  │             ┌─────────────────┐          │
 │  └───────────┬───────────────────┘             │  stop_event     │          │
 │              │ audio chunk                     └─────────────────┘          │
 │              ▼                                                              │
 │  ┌───────────────────────────────┐     Dropped if                           │
 │  │    _audio_callback (STT)      │◄─── is_speaking()                        │
 │  │  - Google Speech Recognition  │    (Echo Suppression)                    │
 │  └───────────┬───────────────────┘                                          │
 │              │ text utterance                                               │
 │              ▼                                                              │
 │  ┌───────────────────────────────┐                                          │
 │  │    command_queue (FIFO)       │                                          │
 │  └───────────┬───────────────────┘                                          │
 │              │                                                              │
 │              ▼                                                              │
 │  ┌───────────────────────────────┐     ┌─────────────────────────────────┐  │
 │  │   _command_dispatcher         │────►│ State Machine (Multi-turn Email)│  │
 │  │   (Dedicated Consumer Thread) │     └────────────────┬────────────────┘  │
 │  └───────────┬───────────────────┘                      │                   │
 │              │                                          ▼                   │
 │              ▼                               ┌─────────────────────┐        │
 │  ┌───────────────────────────────┐           │   ActionHandler     │        │
 │  │   IntentParser (NLU Engine)   │           │ - Web Search        │        │
 │  │ - Regular Expression Patterns │           │ - OpenWeatherMap    │        │
 │  │ - Slot & Parameter Extraction │           │ - Wikipedia QA      │        │
 │  └───────────────────────────────┘           │ - Background Timer  │        │
 │                                              │ - SMTP Mailer       │        │
 │                                              └──────────┬──────────┘        │
 │                                                         │ speech string     │
 │                                                         ▼                   │
 │                                              ┌─────────────────────┐        │
 │                                              │ TextToSpeechManager │        │
 │                                              │ - Dedicated Worker  │        │
 │                                              │ - is_speaking Flag  │        │
 │                                              │ - pyttsx3 Engine    │        │
 │                                              └─────────────────────┘        │
 └─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Non-Blocking Audio Capture (`listen_in_background`)
The assistant initializes a microphone stream and delegates listening to a background daemon thread spawned by `SpeechRecognition`. The main thread is never blocked, allowing other application logic, UI loops, or worker tasks to run simultaneously.

### 2. Acoustic Feedback & Self-Echo Suppression
A common defect in voice agents is self-triggering: when the assistant speaks through the speakers, the microphone records the assistant's own voice and transcribes it as a user command.
- `TextToSpeechManager` maintains a thread-safe `_speaking_event`.
- When audio playback begins, `is_speaking()` returns `True`.
- The background `_audio_callback` discards any audio frames captured during speech synthesis plus an acoustic decay buffer (0.3s).

### 3. Multi-Turn Dialogue State Machine (Voice Email)
Interactive tasks (such as dictating an email) cannot use blocking `input()` or blocking audio calls in an asynchronous architecture. The assistant implements a lightweight dialogue state machine:
- `STATE_NORMAL`: Utterances are parsed as new intents.
- `STATE_EMAIL_RECIPIENT`: Next utterance is sanitized into an email address.
- `STATE_EMAIL_SUBJECT`: Next utterance is saved as the subject line.
- `STATE_EMAIL_BODY`: Next utterance is captured as the message body, dispatched over TLS SMTP, and returned to `STATE_NORMAL`.
- Saying *"cancel"* at any step aborts the draft.

### 4. Thread-Safe TTS Worker
`pyttsx3` is not thread-safe and crashes with `RuntimeError: run loop already started` when invoked simultaneously across multiple threads (e.g. when a background reminder timer triggers while another action is speaking). All vocal prompts are serialized through a thread-safe FIFO queue consumed by a dedicated speech worker.

---

## Prerequisites & Installation

### 1. Clone & Setup Virtual Environment
```bash
# Navigate to project
cd voice_assistant

# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### PyAudio Platform Installation Guide
`PyAudio` interfaces with the PortAudio library to provide microphone streaming:

- **Windows**: Pre-compiled binary wheels install automatically via `pip install PyAudio>=0.2.14`. If you encounter build errors:
  ```bash
  pip install pipwin
  pipwin install pyaudio
  ```
- **macOS**:
  ```bash
  brew install portaudio
  pip install pyaudio
  ```
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt-get update
  sudo apt-get install python3-pyaudio portaudio19-dev libespeak1
  pip install pyaudio
  ```

---

## Configuration Guide (`config.json`)

Settings are stored in [`config.json`](file:///f:/OASIS/voice_assistant/config.json):

```json
{
  "assistant_name": "Aura",
  "voice_gender": "female",
  "speech_rate": 185,
  "volume": 1.0,
  "phrase_time_limit": 8,
  "non_speaking_duration": 0.5,
  "energy_threshold": 300,
  "dynamic_energy_threshold": true,
  "openweathermap": {
    "api_key": "YOUR_OPENWEATHERMAP_API_KEY",
    "default_city": "London",
    "units": "metric"
  },
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "sender_password": "your_app_password"
  },
  "custom_commands": {
    "who made you": "I was designed and coded by an expert Python engineer.",
    "what is your mission": "My mission is to assist you with your daily computing tasks.",
    "tell me a joke": "Why do programmers prefer dark mode? Because light attracts bugs!",
    "how are you": "I am functioning at full capacity in background listening mode!"
  }
}
```

- **OpenWeatherMap**: Obtain a free API key at [openweathermap.org](https://openweathermap.org/api) and paste it into `"api_key"`.
- **Email (SMTP)**: For Gmail accounts, generate a 16-character **App Password** under Google Account Security settings and paste it into `"sender_password"`.
- **Custom Commands**: Add any custom phrase as a key and the desired response as the value.

---

## Usage & Voice Commands

### 1. Background Voice Mode (Microphone)
```bash
python assistant.py
```
The agent calibrates microphone noise, announces that real-time background listening is active, and listens continuously.

### 2. Interactive Console Mode (`--text-mode`)
```bash
python assistant.py --text-mode
```
Allows testing all background queues, state machines, and action handlers by typing commands directly.

### Spoken Phrasing Examples

| Category | Example Spoken Phrases | Assistant Action |
| :--- | :--- | :--- |
| **Greeting** | *"Hello"*, *"Good morning"*, *"Hi there"* | Responds with time-sensitive greeting |
| **Time** | *"What time is it?"*, *"Tell me the current time"* | Speaks the current local time |
| **Date** | *"What is today's date?"*, *"Tell me what day it is"* | Speaks today's date and day of the week |
| **Web Search** | *"Search the web for quantum mechanics"*, *"Google artificial intelligence"* | Speaks confirmation and opens default browser |
| **Live Weather** | *"What's the weather in Tokyo?"*, *"How is the weather?"* | Speaks temperature, conditions, and humidity |
| **Timed Reminder** | *"Remind me to stretch in 5 minutes"*, *"Set a timer for 10 seconds to drink water"* | Schedules non-blocking background alert; triggers audible TTS alert |
| **Wikipedia Q&A** | *"Who was Alan Turing?"*, *"What is machine learning?"*, *"Tell me about Mars"* | Fetches and reads a concise 2-sentence summary |
| **Voice Email** | *"Send an email"*, *"Compose an email"* | Initiates multi-turn voice dialogue for recipient, subject, and body |
| **Custom Commands** | *"Tell me a joke"*, *"Who made you?"* | Speaks custom response configured in `config.json` |
| **Shutdown** | *"Stop listening"*, *"Shut down"*, *"Exit"*, *"Quit"* | Speaks goodbye and cleanly terminates all background daemons |

---

## Testing & Verification

Automated test suites are included to verify functionality:

### 1. Test NLU Intent Parsing (26 Scenarios)
```bash
python test_assistant.py
```
Validates greetings, time/date, search extraction, weather, reminder durations, Wikipedia lookups, emails, custom triggers, and shutdown phrases.

### 2. Test Actions, Background Timers, and Queue Dispatching
```bash
python test_actions.py
```
Validates the action handler, non-blocking reminder thread timers, Wikipedia summaries, API placeholder detection, and the multi-turn email state machine through the asynchronous command queue.

---

## Privacy & Data Processing Disclosure

```
                     ┌──────────────────────────────────────────────┐
                     │               USER'S COMPUTER                │
                     │                                              │
 [Microphone Audio] ─┼──► [listen_in_background]                    │
                     │             │                                │
                     │             ▼ (Raw Audio Stream)             │
                     │    Google Web Speech API ────────► [Cloud]   │
                     │             │                                │
                     │             ▼ (Transcribed Text)             │
                     │       [assistant.py]                         │
                     │       ├── Intent Parsing (Local Regex)       │
                     │       ├── Dialogue State (Local Memory)      │
                     │       ├── Time / Date (Local OS)             │
                     │       ├── Custom Commands (Local Config)     │
                     │       ├── Timed Reminders (Local Threads)    │
                     │       ├── TTS Output (Local pyttsx3 Engine)  │
                     │       │                                      │
                     │       ├── OpenWeatherMap API ────► [Cloud]   │
                     │       ├── Wikipedia API ─────────► [Cloud]   │
                     │       └── SMTP Server (TLS) ─────► [Mail Host]
                     └──────────────────────────────────────────────┘
```

### Local (On-Device) Processing
- **Intent Parsing & NLU**: All intent matching, entity extraction, and conversational state transitions are executed locally using pre-compiled regular expressions. No spoken transcripts are sent to third-party NLP providers.
- **Speech Synthesis (TTS)**: Text-to-speech generation via `pyttsx3` uses your operating system's native speech synthesis engine (Microsoft SAPI5 on Windows, NSSpeechSynthesizer on macOS, eSpeak on Linux). No audio is synthesized via cloud services.
- **Clock & Calendar**: Handled locally via Python's standard `datetime` library.
- **Background Timers**: Reminders run locally in memory via `threading.Timer` daemon threads.
- **Custom Commands**: Resolved locally from `config.json`.

### Third-Party & Cloud Services
- **Speech-to-Text (`SpeechRecognition`)**:
  - **Provider**: Google Web Speech API (via `recognize_google`).
  - **Data Transmitted**: Short audio samples captured when speech exceeds the background energy threshold.
  - **Data Retention**: Audio samples are processed ephemerally by Google to return text strings. No user credentials or persistent identifiers are attached.
- **Weather Forecasts (`requests`)**:
  - **Provider**: OpenWeatherMap REST API (`api.openweathermap.org`).
  - **Data Transmitted**: User-specified city name and your configured OpenWeatherMap API Key.
- **Wikipedia Knowledge Base (`wikipedia`)**:
  - **Provider**: Wikimedia Foundation (`en.wikipedia.org`).
  - **Data Transmitted**: Query search terms sent with a compliant identification header.
- **Email Sending (`smtplib`)**:
  - **Provider**: Your configured SMTP mail host (e.g. `smtp.gmail.com`).
  - **Data Transmitted**: Sender credentials, recipient address, subject, and message content over an encrypted TLS connection.

### Data Minimization & Security Recommendations
- **Microphone Isolation**: Audio is sampled only when voice levels cross the calibrated ambient energy threshold; no audio recordings are saved to disk.
- **Credentials Protection**: `config.json` is listed in `.gitignore` to prevent committing sensitive passwords or keys to version control.
- **App-Specific Passwords**: Always use dedicated, revocable App Passwords for SMTP instead of primary account passwords.
