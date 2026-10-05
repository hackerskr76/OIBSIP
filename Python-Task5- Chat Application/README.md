# Chatty Real-Time Chat Application (Web Edition)

A production-ready, full-stack real-time chat application inspired by modern web messaging design, built with **Python**, **Flask**, **Flask-SocketIO (WebSockets)**, and **SQLite3**. Supports seamless multi-device communication across desktops, laptops, and smartphones on the same local Wi-Fi network.

---

## 🌟 Key Features

### 1. Chatty Web Interface & Experience
- **Signature Aesthetics**: Polished teal header (`#008069`), soft textured wallpaper background (`#efeae2`), and clean typography.
- **Message Bubbles**:
  - **Outgoing (Self)**: Light green (`#d9fdd3`), right-aligned, with embedded small timestamps and double checkmarks (`✓✓`).
  - **Incoming (Others)**: Pure white (`#ffffff`), left-aligned, with colored sender badges and timestamps.
  - **System Notifications**: Centered pill notifications for user arrivals, departures, and disconnects.
- **Desktop Two-Column Layout**: Left sidebar for user profile, search, and room discovery; right pane for active conversation.
- **Mobile Responsive Layout**: On screens `< 768px`, switches to a single-column view. Tapping a room enters a full-screen conversation pane with a prominent **"← Back" button** to return to the room list.
- **Auto-Scroll**: Messages feed smoothly and automatically scrolls to the newest message upon sending, receiving, or loading room history.

### 2. Local Network Multi-Device Support
- **`0.0.0.0` Host Binding**: Bound across all network interfaces so any device on your Wi-Fi can participate.
- **Automatic LAN IP Detection**: On startup, automatically discovers and prints the machine's local IPv4 address (e.g., `http://192.168.X.X:5000`) for quick entry on mobile phones.

### 3. Core Networking & WebSocket Engine
- **Real-Time Bidirectional WebSockets**: Powered by `Flask-SocketIO` and `simple-websocket`.
- **Graceful Disconnection Handling**: When a user leaves or closes their tab, the server automatically cleans up the session and broadcasts:
  ```text
  [14:36] System: Alice has disconnected.
  ```
- **Live User Tracking & Typing Indicators**: Real-time room participant rosters and "Alice is typing..." indicators.

### 4. Authentication, Rooms & History
- **Cryptographic Password Hashing**: Backed by `werkzeug.security` and SQLite (`users` table).
- **Session Persistence**: Signed, HTTP-only session cookies maintain login state across refreshes.
- **Persistent Message History**: Messages are stored in SQLite and automatically queried and streamed into the chat view when a user joins any room.
- **Emoji Shortcode Engine**: Converts shortcodes (e.g., `:smile:`, `:heart:`, `:fire:`, `:rocket:`, `:thumbsup:`, `:100:`) into native Unicode emojis with a visual emoji picker popover.
- **Desktop Notifications**: Browser Web Notification API alerts users when a message is received while the window is unfocused or backgrounded.

---

## 🏗️ Architecture & Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Backend Framework** | `Flask 3.x` | Routing, REST APIs, session management |
| **Real-Time Layer** | `Flask-SocketIO 5.x` | Bi-directional WebSocket communication |
| **WebSocket Engine** | `simple-websocket` | Modern WebSocket protocol transport |
| **Database** | `SQLite3` | Relational database with foreign key support |
| **Security** | `Werkzeug` | Salted password hashing (`generate_password_hash`) |
| **Frontend** | Vanilla JS (ES6+), HTML5, CSS3 | Chatty Web responsive layout with Web Audio API |
| **Client Socket** | `Socket.IO 4.7.5` | Client-side WebSocket connection and event handling |

---

## 📁 Project Structure

```text
Chat_application/
├── app.py                  # Flask server: Routing, SocketIO events, SQLite logic, LAN IP detection
├── chat.db                 # SQLite database (auto-created on initial run)
├── templates/
│   └── index.html          # Chatty Web GUI (HTML, responsive CSS, Socket.IO client JS)
├── requirements.txt        # Pinned Python dependencies
├── test_app.py             # Test suite (Unit tests + WebSocket integration tests)
└── README.md               # Documentation and Security Transparency
```

---

## 🚀 Getting Started & Localhost Access

### Prerequisites
- **Python 3.9+** (Tested on Python 3.11)
- **pip** package manager

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python app.py
```

You will see the startup banner displaying your exact local network access URLs:
```text
=================================================================
 🚀 CHATTY REAL-TIME APPLICATION (WEB EDITION)
 💻 Localhost Access:       http://127.0.0.1:5000
 📱 Mobile / Wi-Fi Access:  http://192.168.29.59:5000
 📡 WebSocket transport enabled (Flask-SocketIO)
 💾 Database: SQLite3 (chat.db)
 🌐 Bound to host=0.0.0.0 (all local network interfaces)
=================================================================
```

### 3. Open on Your Computer
Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000) in your desktop browser.

---

## 📱 Connecting a Mobile Device (Same Wi-Fi Network)

To use the application across multiple devices (e.g., your smartphone and your laptop):

1. **Connect to the Same Wi-Fi Network**: Ensure your mobile phone and host computer are connected to the same local Wi-Fi router / network.
2. **Note the Mobile Access URL**: Check the terminal output when running `python app.py`. Look for the line:
   ```text
   📱 Mobile / Wi-Fi Access:  http://<YOUR_LAN_IP>:5000
   ```
   *(For example: `http://192.168.29.59:5000`)*
3. **Open Mobile Browser**: On your phone, open Chrome, Safari, or Firefox and enter that URL.
4. **Create an Account or Log In**: Register a username (e.g. `MobileUser`).
5. **Real-Time Cross-Device Chatting**:
   - On desktop, log in as `DesktopUser`.
   - On mobile, join `# General`.
   - Send messages back and forth in real-time. Messages will immediately pop up with light-green outgoing bubbles and white incoming bubbles!

### 💡 Windows Firewall Note
If your phone is unable to load the page, Windows Defender Firewall may be blocking incoming connections on port `5000`. You can allow it via PowerShell (run as Administrator):
```powershell
New-NetFirewallRule -DisplayName "Chatty Flask Server" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```
Or temporarily click **Allow Access** when Windows prompts you upon launching `python app.py`.

---

## 🧪 Testing & Verification

Run the automated test suite covering database operations, authentication, emoji parsing, and WebSocket real-time event broadcasting:

```bash
python -m pytest test_app.py -v
```

All 8 tests verify:
- Automatic SQLite database creation & table indexing.
- Password hashing and duplicate username prevention.
- User authentication and session verification.
- Emoji shortcode conversions (`:smile:` ➔ 😄).
- WebSocket connection, room history loading, bidirectional broadcasting, and disconnect notices.

---

## 🔒 Security Transparency & Data Storage

> [!IMPORTANT]
> This section documents the security posture, authentication handling, and data privacy considerations of this application.

### 1. Password Storage & Cryptographic Hashing
- **Hashing Function:** Passwords are never stored in plaintext. They are processed using `werkzeug.security.generate_password_hash` using salted **PBKDF2 with SHA-256** (or **scrypt**).
- **Salts:** Each user's password hash incorporates a unique, cryptographically secure random salt, protecting against rainbow table attacks.
- **Verification:** Credential validation during authentication uses constant-time string comparison (`check_password_hash`) to protect against timing attacks.

### 2. Message Storage: NOT Encrypted at Rest (Warning)
- **Storage Location:** All chat messages, user IDs, room IDs, and timestamps are stored in the `messages` table within the local SQLite database file (`chat.db`).
- **Encryption Status:** **Message contents are stored as unencrypted PLAINTEXT and are NOT encrypted at rest.**
- **Threat Implication:** Anyone with filesystem read access to the server or the `chat.db` file can view the entire message history across all rooms.
- **Usage Warning:**
  > [!CAUTION]
  > **DO NOT USE THIS APPLICATION FOR SENSITIVE, CONFIDENTIAL, REGULATED, OR FINANCIAL DATA.**
  > This application is intended for local network collaboration, demonstrations, and development. Without adding an encryption layer, it should not be exposed to the public Internet or used for private personal data.

### 3. Recommendations for Production Hardening
If deploying this application to a public or production environment:
1. **At-Rest Encryption:** Integrate **SQLCipher** (e.g. `pysqlcipher3`) to encrypt the SQLite database file with 256-bit AES encryption.
2. **End-to-End Encryption (E2EE):** Utilize the browser's Web Crypto API to exchange public keys (ECDH) and encrypt message payloads with AES-GCM on the sender's device before sending them over WebSockets.
3. **Transport Security (TLS / WSS):** Place the Flask application behind a reverse proxy (such as Nginx, Caddy, or Cloudflare) configured with valid SSL/TLS certificates to enforce **HTTPS** and **WSS (WebSocket Secure)**.
4. **Cookie Security:** When serving over HTTPS, enable `SESSION_COOKIE_SECURE = True` in `app.py`.
