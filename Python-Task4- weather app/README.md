# ⛅ Atmosphere — Modern Desktop Weather Application

Atmosphere is a complete, production-ready desktop weather application built with Python, Tkinter, Pillow, and the OpenWeatherMap & IPinfo.io APIs. It features a modern dark-slate interface, live weather metrics, hourly & 5-day daily forecasts, dynamic official weather icons, instant unit switching (°C / °F), and one-click automatic IP-based location detection.

---

## 🌟 Key Features

### 🟢 Core API Logic & Validation (Beginner Baseline)
- **Current Weather Endpoint**: Connects to OpenWeatherMap's Current Weather Data API and parses real-time metrics.
- **Essential Weather Metrics**: Displays temperature, weather condition description (e.g., *"Partly Cloudy"*, *"Moderate Rain"*), humidity percentage, and wind speed.
- **Extended Conditions**: Includes "Feels Like" temperature, atmospheric pressure (hPa), visibility, and local time.
- **Input Validation**: Validates user queries and prevents empty or whitespace-only submissions.
- **Graceful Error Handling**: Non-crashing error handling displaying informative GUI pop-up dialogs (`messagebox`) for:
  - City not found (HTTP 404)
  - Invalid or unactivated API key (HTTP 401)
  - Rate limiting (HTTP 429)
  - Network timeouts and disconnection issues

### 🚀 GUI, Forecasts & Auto-Location (Advanced Tier)
- **Modern Dark Interface**: Clean, polished desktop UI utilizing high-contrast slate cards, clear visual hierarchy, and smooth mouse wheel scrolling.
- **⚡ Quick Cities Bar**: One-click preset pills for major world cities (`🇬🇧 London`, `🇺🇸 New York`, `🇯🇵 Tokyo`, `🇫🇷 Paris`, `🇦🇪 Dubai`, `🇮🇳 Mumbai`, `🇦🇺 Sydney`, `🇸🇬 Singapore`).
- **🌍 30+ World Cities Dropdown**: Fast explore menu covering iconic cities across the Americas, Europe, Asia, Africa, and Oceania.
- **⭐ Saved / Favorite Cities**: Bookmark any searched city with the **"☆ Save City"** button to pin it to your quick-access favorites row.
- **Dynamic Weather Icons**: Downloads and caches official OpenWeatherMap weather icons using Pillow (`PIL`), complete with offline fallbacks.
- **Hourly Forecast Panel**: Parses the next 6–12 hours into distinct forecast cards showing timestamp, weather condition icon, and temperature.
- **5-Day Daily Forecast Panel**: Aggregates the 5-day forecast into daily cards with day names, dates, midday condition descriptions, and High / Low temperature ranges.
- **Instant Unit Toggle (°C / °F)**: Switch between Celsius and Fahrenheit at any time. When toggled, all active hero and forecast numbers re-render immediately without re-fetching.
- **Automatic IP Geolocation**: One-click **"📍 Auto Location"** button calls `https://ipinfo.io/json` to automatically detect your local city, populate the input box, and pull the forecast.
- **Non-Blocking Multithreading**: All network requests run asynchronously in background worker threads so the GUI never stutters, hangs, or shows *"Not Responding"*.

---

## 📋 Prerequisites

- **Python 3.8+** (Python 3.11+ recommended)
- **Tkinter** (included by default in standard Python distributions for Windows and macOS)
  - *On Linux (Ubuntu/Debian)*, install via: `sudo apt-get install python3-tk`
- An active internet connection

---

## 📦 Installation & Setup

### 1. Clone or Open the Project
Navigate to the project root directory:
```bash
cd "F:\OASIS\Weather APP"
```

### 2. Set Up a Python Virtual Environment (Recommended)
If you haven't already created a virtual environment:
```bash
# On Windows:
python -m venv .venv
.\.venv\Scripts\activate

# On macOS/Linux:
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install all required libraries from `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 🔑 Getting Your Free API Keys

### OpenWeatherMap API Key (Required for Weather Data)
1. Go to [OpenWeatherMap Sign Up](https://home.openweathermap.org/users/sign_up) and register for a free account.
2. Verify your email address.
3. Visit the [API Keys Tab](https://home.openweathermap.org/api_keys).
4. Copy your default 32-character API key.
5. Provide your key using either of two methods:
   - **Method A (Direct in `main.py`)**: Open `main.py` and replace line 37:
     ```python
     OPENWEATHER_API_KEY: str = "YOUR_ACTUAL_API_KEY_HERE"
     ```
   - **Method B (Environment Variable)**:
     ```powershell
     # In Windows PowerShell:
     $env:OPENWEATHER_API_KEY="YOUR_ACTUAL_API_KEY_HERE"

     # In Linux/macOS Bash:
     export OPENWEATHER_API_KEY="YOUR_ACTUAL_API_KEY_HERE"
     ```

> [!NOTE]
> Newly created OpenWeatherMap API keys typically take between **30 to 120 minutes** to propagate through their global CDN. If you receive an "Invalid API Key" response immediately after signing up, please allow a short time for OpenWeatherMap to activate your new key.

### IPinfo.io Token (Optional)
The automatic IP location detector uses IPinfo's free public endpoint (`https://ipinfo.io/json`) out of the box without requiring any token. If you have an account or token, you can optionally set `IPINFO_API_TOKEN` in `main.py` or as an environment variable.

---

## 🚀 Running the Application

Run the application with Python:
```bash
python main.py
```

### Usage Guide
1. **Search Any City**: Enter any city name (e.g., `Tokyo`, `New York`, `London`, `Paris`) in the search field and press <kbd>Enter</kbd> or click **"Get Weather"**.
2. **⚡ Quick Pick Popular Cities**: Click any top global city pill (`🇬🇧 London`, `🇺🇸 New York`, `🇯🇵 Tokyo`, `🇫🇷 Paris`, `🇦🇪 Dubai`, `🇮🇳 Mumbai`, `🇦🇺 Sydney`, `🇸🇬 Singapore`) to check its weather with one click.
3. **🌍 Explore 30+ World Cities**: Use the dropdown menu to select from major metropolitan hubs across all 6 continents.
4. **⭐ Bookmark Favorite Cities**: Click **"☆ Save City"** on any weather card to pin it into your personal **Saved Cities** row for quick 1-click checking.
5. **Auto-Detect**: Click **"📍 Auto Location"** to automatically discover your city via IP and fetch its forecast.
6. **Change Units**: Click the **°C** or **°F** radio toggle in the top-right corner to toggle all temperature metrics instantly.
7. **Key Instructions**: Click **"🔑 API Setup"** in the top bar to review key setup instructions at any time.

---

## 📂 Project Structure

```
Weather APP/
├── main.py              # Main desktop application (OOP Tkinter, API client, threading, UI)
├── requirements.txt     # Python dependencies (requests, Pillow)
└── README.md            # Comprehensive documentation & setup guide
```

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Missing API Key" popup** | The placeholder key `YOUR_API_KEY_HERE` is still in `main.py`. | Paste your valid OpenWeatherMap key in `main.py` or set the `OPENWEATHER_API_KEY` environment variable. |
| **"Invalid API Key (HTTP 401)"** | The API key is brand new or mistyped. | Ensure the key matches your OpenWeather dashboard. New keys may take up to 2 hours to activate. |
| **"City not found (HTTP 404)"** | Typo or unrecognized location query. | Check spelling or specify country code (e.g., `Paris, US` vs `Paris, FR`). |
| **"Network request timed out"** | Slow or blocked internet connection. | Check your local network or firewall settings. |
| **Blank or placeholder icon** | Weather icon download temporarily blocked or offline. | The app automatically displays an offline fallback condition icon. |

---

## 📜 License
This project is open-source and free for personal and educational use.
