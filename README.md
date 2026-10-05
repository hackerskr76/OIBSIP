Python Applications Portfolio

A collection of five production-ready Python applications focused on automation, data visualization, cybersecurity, real-time communication, and API integration.

Projects
1. 🎙️ Real-Time Voice Assistant

A non-blocking voice assistant that understands natural-language commands and executes system and web actions without freezing the main application.

Highlights

Custom natural-language command parsing
Asynchronous background voice listening
Local audio processing
Weather integration through OpenWeatherMap API
Audio data is not stored on disk

Tech Stack: Python, SpeechRecognition, pyttsx3, Threading, OpenWeatherMap API

Run

pip install SpeechRecognition pyttsx3 PyAudio requests
python assistant.py
2. 📊 BMI Calculator & Health Tracker

An offline desktop application for tracking BMI data over time with persistent storage and visual analytics.

Highlights

Multi-user health tracking
SQLite-based persistent data storage
Metric validation
Dynamic BMI categorization
Interactive Matplotlib trend charts

Tech Stack: Python, Tkinter, SQLite3, Matplotlib

Run

pip install matplotlib
python main.py
3. 🔐 Cryptographically Secure Password Generator

A desktop cybersecurity utility designed to generate strong passwords using Python's cryptographically secure secrets module.

Highlights

Cryptographically secure password generation
Character diversity guarantees
Ambiguous-character filtering
Dynamic password-strength indicator
Temporary session history automatically cleared on exit

Tech Stack: Python, secrets, Tkinter, Pyperclip

Run

pip install pyperclip
python main.py
4. 🌦️ Graphical Weather Dashboard

A desktop weather dashboard providing automatic location detection and multi-day weather forecasting through a graphical interface.

Highlights

Automatic city detection using IP
Real-time weather information
Dynamic weather condition icons
5-day forecast
6-hour hourly forecast panels

Tech Stack: Python, Tkinter, Requests, Pillow, OpenWeatherMap API

Run

pip install requests Pillow
python main.py
5. 💬 Multi-Device Real-Time Chat Application

A WhatsApp Web-inspired messaging platform supporting multiple concurrent devices connected through a local network.

Highlights

Real-time messaging
Multi-device LAN connectivity
Persistent chat rooms
SQLite message history
Secure password hashing with Werkzeug
Emoji shortcode conversion
Server accessible across the local network using 0.0.0.0

Tech Stack: Python, Flask, Flask-SocketIO, SQLite3, Werkzeug

Run

pip install flask flask-socketio werkzeug
python app.py
🛠️ Technology Overview
Area	Technologies
Language	Python
Desktop GUI	Tkinter
Web	Flask, Flask-SocketIO
Database	SQLite3
Data Visualization	Matplotlib
APIs	OpenWeatherMap
Security	Python secrets, Werkzeug
Networking	Sockets, LAN, WebSockets
Automation	Speech Recognition, Text-to-Speech
🎯 Key Focus Areas
Real-time communication
Desktop application development
API integration
Data visualization
Cybersecurity
Database management
Networking
Automation
📁 Repository Structure
python-applications-portfolio/
│
├── voice-assistant/
├── bmi-health-tracker/
├── password-generator/
├── weather-dashboard/
├── realtime-chat/
└── README.md
🚀 Getting Started

Clone the repository and navigate into the application you want to run:

git clone <your-repository-url>
cd python-applications-portfolio

Each project contains its own dependencies and execution instructions.

👨‍💻 Author

Sahil Raut

Computer Science & Engineering Student | AI/ML | Full-Stack Development | Cybersecurity

Note: Each application is independently runnable and focuses on solving a specific real-world problem using Python.
