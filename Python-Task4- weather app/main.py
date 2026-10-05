"""
Atmosphere Weather App - Production-Ready Desktop Application
------------------------------------------------------------
A modern, feature-packed Tkinter weather desktop application built with Python.
Supports current conditions, 5-day daily forecast, hourly forecast,
dynamic weather icons, metric/imperial unit toggle, and automatic IP location.
"""

import io
import os
import sys
import json
import math
import queue
import logging
import threading
from datetime import datetime, timezone, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List

import requests
from PIL import Image, ImageTk

# ==============================================================================
# CONFIGURATION & API KEYS
# ==============================================================================
# Paste your free OpenWeatherMap API key below or set the OPENWEATHER_API_KEY env var.
# Get a free API key at: https://home.openweathermap.org/users/sign_up
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "e2ef4c399105041b1c1066f729c8209c")

# Optional IPinfo API token if you have one. Otherwise, the free tier endpoint is used.
IPINFO_API_TOKEN: str = os.getenv("IPINFO_API_TOKEN", "")

# Endpoints
CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
ICON_URL_TEMPLATE = "https://openweathermap.org/img/wn/{icon_code}@2x.png"
IPINFO_URL = "https://ipinfo.io/json"

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WeatherApp")


# ==============================================================================
# COLOR PALETTE & STYLES (Modern Deep Slate Dark Theme)
# ==============================================================================
THEME = {
    "bg_app": "#0f172a",         # Slate 900
    "bg_card": "#1e293b",        # Slate 800
    "bg_card_alt": "#334155",    # Slate 700
    "bg_input": "#1e293b",       # Input background
    "border": "#475569",         # Slate 600
    "accent": "#38bdf8",         # Sky 400 (Cyan/Blue)
    "accent_hover": "#0284c7",   # Sky 600
    "accent_green": "#34d399",   # Emerald 400
    "text_primary": "#f8fafc",   # Slate 50
    "text_secondary": "#94a3b8", # Slate 400
    "text_muted": "#64748b",     # Slate 500
    "highlight": "#fbbf24",      # Amber 400
}

FONT_HEADING = ("Segoe UI", 18, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_SUBTITLE = ("Segoe UI", 11, "bold")
FONT_TEMP_HERO = ("Segoe UI", 48, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_BODY_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_STATUS = ("Segoe UI", 9, "italic")

# ==============================================================================
# PRESET WORLD LOCATIONS FOR QUICK CHECKING
# ==============================================================================
POPULAR_CITIES = [
    ("🇬🇧 London", "London"),
    ("🇺🇸 New York", "New York"),
    ("🇯🇵 Tokyo", "Tokyo"),
    ("🇫🇷 Paris", "Paris"),
    ("🇦🇪 Dubai", "Dubai"),
    ("🇮🇳 Mumbai", "Mumbai"),
    ("🇦🇺 Sydney", "Sydney"),
    ("🇸🇬 Singapore", "Singapore"),
]

MORE_WORLD_CITIES = [
    # Americas
    "Chicago, US",
    "Los Angeles, US",
    "Miami, US",
    "San Francisco, US",
    "Toronto, CA",
    "Vancouver, CA",
    "Mexico City, MX",
    "São Paulo, BR",
    "Buenos Aires, AR",
    # Europe
    "Amsterdam, NL",
    "Barcelona, ES",
    "Berlin, DE",
    "Dublin, IE",
    "Madrid, ES",
    "Rome, IT",
    "Vienna, AT",
    "Zurich, CH",
    # Asia & Middle East
    "Bangkok, TH",
    "Beijing, CN",
    "Delhi, IN",
    "Hong Kong, HK",
    "Istanbul, TR",
    "Kuala Lumpur, MY",
    "Seoul, KR",
    # Africa & Oceania
    "Auckland, NZ",
    "Cairo, EG",
    "Cape Town, ZA",
    "Melbourne, AU",
    "Nairobi, KE",
]

# ==============================================================================
# WEATHER DATA MODELS & CONVERSION HELPERS
# ==============================================================================
def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9.0 / 5.0) + 32.0


def f_to_c(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32.0) * 5.0 / 9.0


def mps_to_mph(mps: float) -> float:
    """Convert meters per second to miles per hour."""
    return mps * 2.23694


def mps_to_kmh(mps: float) -> float:
    """Convert meters per second to kilometers per hour."""
    return mps * 3.6


def format_temp(temp_celsius: float, unit: str) -> str:
    """Format temperature string with degree symbol based on unit preference."""
    if unit == "imperial":
        f = c_to_f(temp_celsius)
        return f"{round(f)}°F"
    return f"{round(temp_celsius)}°C"


def format_wind(speed_mps: float, unit: str) -> str:
    """Format wind speed based on unit preference."""
    if unit == "imperial":
        return f"{round(mps_to_mph(speed_mps), 1)} mph"
    return f"{round(mps_to_kmh(speed_mps), 1)} km/h"


# ==============================================================================
# WEATHER API CLIENT
# ==============================================================================
class WeatherAPIClient:
    """Handles network requests for weather data and IP geolocation."""

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AtmosphereWeatherApp/1.0"
        })

    def validate_api_key(self) -> bool:
        """Check if the user has provided a real key instead of the placeholder."""
        placeholder = "YOUR_API_KEY_HERE"
        return bool(self.api_key and self.api_key != placeholder and len(self.api_key) >= 16)

    def fetch_current_weather(self, city: str) -> Dict[str, Any]:
        """Fetch current weather data in standard metric units."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",  # Always fetch metric internally, convert for display
        }
        response = self.session.get(CURRENT_WEATHER_URL, params=params, timeout=10)
        return self._handle_response(response, city)

    def fetch_forecast(self, city: str) -> Dict[str, Any]:
        """Fetch 5-day / 3-hour forecast data in standard metric units."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
        }
        response = self.session.get(FORECAST_URL, params=params, timeout=10)
        return self._handle_response(response, city)

    def detect_ip_location(self) -> str:
        """Detect the user's city via IP address using ipinfo.io with ip-api.com fallback."""
        # 1. Primary: ipinfo.io
        headers = {}
        if IPINFO_API_TOKEN:
            headers["Authorization"] = f"Bearer {IPINFO_API_TOKEN}"

        try:
            response = self.session.get(IPINFO_URL, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                city = data.get("city") or data.get("region")
                if city:
                    return city
        except Exception as exc:
            logger.warning(f"Primary IP location service (ipinfo.io) error: {exc}. Trying fallback service...")

        # 2. Fallback: ip-api.com
        try:
            response = self.session.get("http://ip-api.com/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                city = data.get("city") or data.get("regionName")
                if city:
                    return city
        except Exception as exc:
            logger.warning(f"Fallback IP location service (ip-api.com) error: {exc}.")

        raise ConnectionError(
            "Could not determine your city via IP location services. "
            "Please check your internet connection or enter your city manually in the search bar."
        )

    def _handle_response(self, response: requests.Response, city: str) -> Dict[str, Any]:
        """Handle standard HTTP response codes and parse JSON with helpful errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
            error_msg = error_data.get("message", "Unknown error")
        except Exception:
            error_msg = response.text or "Unknown response"

        if response.status_code == 404:
            raise ValueError(f"City '{city}' not found. Please check spelling and try again.")
        elif response.status_code == 401:
            raise PermissionError(
                "Invalid API Key. Please verify your OpenWeatherMap API key.\n"
                "Note: New keys can take up to 1-2 hours after sign-up to activate."
            )
        elif response.status_code == 429:
            raise RuntimeError("OpenWeatherMap API rate limit exceeded. Please wait a moment.")
        else:
            raise RuntimeError(f"OpenWeatherMap API error (HTTP {response.status_code}): {error_msg.capitalize()}")


# ==============================================================================
# ICON MANAGER (PIL + Caching + Offline Fallbacks)
# ==============================================================================
class IconManager:
    """Downloads, caches, resizes, and provides PhotoImage objects for weather icons."""

    def __init__(self):
        self._cache: Dict[str, ImageTk.PhotoImage] = {}
        self._raw_cache: Dict[str, Image.Image] = {}
        self._session = requests.Session()

    def get_icon(self, icon_code: str, size: tuple = (80, 80)) -> ImageTk.PhotoImage:
        """Get cached PhotoImage of the requested weather icon, downloading if necessary."""
        cache_key = f"{icon_code}_{size[0]}x{size[1]}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check raw image cache
        if icon_code not in self._raw_cache:
            img = self._download_icon(icon_code)
            self._raw_cache[icon_code] = img
        else:
            img = self._raw_cache[icon_code]

        # Resize and create PhotoImage
        resized = img.resize(size, Image.Resampling.LANCZOS)
        photo_img = ImageTk.PhotoImage(resized)
        self._cache[cache_key] = photo_img
        return photo_img

    def _download_icon(self, icon_code: str) -> Image.Image:
        """Fetch icon from OpenWeatherMap CDN or return fallback if offline."""
        url = ICON_URL_TEMPLATE.format(icon_code=icon_code)
        try:
            resp = self._session.get(url, timeout=5)
            if resp.status_code == 200:
                return Image.open(io.BytesIO(resp.content)).convert("RGBA")
        except Exception as e:
            logger.warning(f"Could not download icon '{icon_code}': {e}. Using fallback icon.")

        return self._generate_fallback_icon(icon_code)

    def _generate_fallback_icon(self, icon_code: str) -> Image.Image:
        """Generate a clean colored fallback circle when offline or icon is missing."""
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        # Choose color by icon condition
        color = (250, 204, 21, 220) if "d" in icon_code else (148, 163, 184, 220)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.ellipse([15, 15, 85, 85], fill=color, outline=(255, 255, 255, 180), width=3)
        return img


# ==============================================================================
# MAIN APPLICATION CLASS
# ==============================================================================
class WeatherApp(tk.Tk):
    """Production-grade Graphical Weather Application."""

    def __init__(self):
        super().__init__()
        self.title("Atmosphere — Weather & Forecast")
        self.geometry("980x820")
        self.minsize(860, 720)
        self.configure(bg=THEME["bg_app"])

        # Try to set modern taskbar/window icon
        self._configure_window_icon()

        # State management
        self.api_client = WeatherAPIClient(OPENWEATHER_API_KEY)
        self.icon_manager = IconManager()
        self.unit_var = tk.StringVar(value="metric")  # 'metric' (°C) or 'imperial' (°F)
        self.is_loading = False

        # Current loaded dataset cache (metric values stored internally for instant unit switching)
        self.current_data: Optional[Dict[str, Any]] = None
        self.forecast_data: Optional[Dict[str, Any]] = None

        # Favorite locations & active city tracking
        self.favorite_cities: List[str] = ["London", "New York", "Tokyo", "Paris", "Mumbai"]
        self.active_city_name: str = "London"

        # Thread-safe queue for background worker communication
        self.queue: queue.Queue = queue.Queue()
        self._poll_queue()

        # Build GUI layout
        self._setup_styles()
        self._build_ui()

        # Bind Return key to search
        self.city_entry.bind("<Return>", lambda event: self.start_weather_fetch())

        # Check API key status on launch (non-blocking status indicator)
        if not self.api_client.validate_api_key():
            self.lbl_status.config(
                text="⚠️ Note: API key is not configured. Set OPENWEATHER_API_KEY in main.py to fetch live weather.",
                fg=THEME["highlight"]
            )

    def run_on_main_thread(self, func, *args):
        """Thread-safe dispatch of callbacks to the main Tkinter thread."""
        self.queue.put((func, args))

    def _poll_queue(self):
        """Process dispatched callbacks on the main GUI thread."""
        try:
            while True:
                callback, args = self.queue.get_nowait()
                try:
                    callback(*args)
                except Exception as exc:
                    logger.error(f"Error executing callback {callback}: {exc}")
                finally:
                    self.queue.task_done()
        except queue.Empty:
            pass
        # Reschedule check every 50ms
        self.after(50, self._poll_queue)

    def _configure_window_icon(self):
        """Set a window icon if supported."""
        try:
            # Create a simple 32x32 weather sun icon in memory
            icon_img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(icon_img)
            draw.ellipse([4, 4, 28, 28], fill=(56, 189, 248, 255))
            self._app_icon_photo = ImageTk.PhotoImage(icon_img)
            self.iconphoto(False, self._app_icon_photo)
        except Exception:
            pass

    def _setup_styles(self):
        """Configure ttk styles for a unified dark theme."""
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Frame styles
        self.style.configure("App.TFrame", background=THEME["bg_app"])
        self.style.configure("Card.TFrame", background=THEME["bg_card"], relief="flat")
        self.style.configure("CardAlt.TFrame", background=THEME["bg_card_alt"], relief="flat")

        # Label styles
        self.style.configure("App.TLabel", background=THEME["bg_app"], foreground=THEME["text_primary"], font=FONT_BODY)
        self.style.configure("Card.TLabel", background=THEME["bg_card"], foreground=THEME["text_primary"], font=FONT_BODY)
        self.style.configure("CardMuted.TLabel", background=THEME["bg_card"], foreground=THEME["text_secondary"], font=FONT_SMALL)
        self.style.configure("CardBold.TLabel", background=THEME["bg_card"], foreground=THEME["text_primary"], font=FONT_BODY_BOLD)

        # Radio button style for units
        self.style.configure(
            "Unit.TRadiobutton",
            background=THEME["bg_card"],
            foreground=THEME["text_primary"],
            font=FONT_BODY_BOLD,
            focuscolor=THEME["bg_card"],
        )
        self.style.map(
            "Unit.TRadiobutton",
            background=[("active", THEME["bg_card"])],
            foreground=[("active", THEME["accent"])]
        )

        # Combobox style
        self.style.configure(
            "City.TCombobox",
            fieldbackground=THEME["bg_card_alt"],
            background=THEME["bg_card_alt"],
            foreground=THEME["text_primary"],
            arrowcolor=THEME["accent"],
            bordercolor=THEME["border"],
        )

    def _build_ui(self):
        """Build the complete application layout using modular frames."""
        # Top Header & Search Bar
        self._build_search_header()

        # Quick Locations / Popular & Saved Cities Bar
        self._build_quick_locations_bar()

        # Scrollable Canvas container for responsive layout
        self.container_canvas = tk.Canvas(self, bg=THEME["bg_app"], bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.container_canvas.yview)
        self.scrollable_content = tk.Frame(self.container_canvas, bg=THEME["bg_app"])

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.container_canvas.configure(scrollregion=self.container_canvas.bbox("all"))
        )

        self.canvas_window_id = self.container_canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.container_canvas.configure(yscrollcommand=self.scrollbar.set)

        # Ensure content frame stretches horizontally
        self.container_canvas.bind(
            "<Configure>",
            lambda e: self.container_canvas.itemconfig(self.canvas_window_id, width=e.width)
        )

        # Pack scroll container
        self.scrollbar.pack(side="right", fill="y")
        self.container_canvas.pack(side="top", fill="both", expand=True, padx=16, pady=4)

        # Bind mouse wheel for smooth scrolling
        self._bind_mouse_wheel(self.container_canvas)

        # Hero Current Weather Section
        self._build_current_weather_hero()

        # Hourly Forecast Section
        self._build_hourly_forecast_section()

        # 5-Day Daily Forecast Section
        self._build_daily_forecast_section()

        # Bottom Status Bar
        self._build_status_bar()

    def _bind_mouse_wheel(self, widget):
        """Enable mouse wheel scrolling on Windows and other platforms."""
        def _on_mousewheel(event):
            self.container_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind_all("<MouseWheel>", _on_mousewheel)

    # --------------------------------------------------------------------------
    # HEADER & SEARCH BAR
    # --------------------------------------------------------------------------
    def _build_search_header(self):
        """Top section containing title, search bar, auto-detect, and unit toggle."""
        header_frame = tk.Frame(self, bg=THEME["bg_card"], padx=18, pady=14)
        header_frame.pack(side="top", fill="x", padx=16, pady=(14, 8))

        # Brand / Title
        brand_frame = tk.Frame(header_frame, bg=THEME["bg_card"])
        brand_frame.pack(side="left", padx=(0, 16))

        brand_icon = tk.Label(brand_frame, text="⛅", font=("Segoe UI Emoji", 20), bg=THEME["bg_card"], fg=THEME["accent"])
        brand_icon.pack(side="left", padx=(0, 6))

        title_lbl = tk.Label(brand_frame, text="Atmosphere", font=FONT_TITLE, bg=THEME["bg_card"], fg=THEME["text_primary"])
        title_lbl.pack(side="left")

        # Search Controls Area
        search_box_frame = tk.Frame(header_frame, bg=THEME["bg_card"])
        search_box_frame.pack(side="left", fill="x", expand=True, padx=(8, 12))

        # City Input Field
        input_container = tk.Frame(search_box_frame, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        input_container.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.city_entry = tk.Entry(
            input_container,
            font=("Segoe UI", 11),
            bg=THEME["bg_input"],
            fg=THEME["text_primary"],
            insertbackground=THEME["text_primary"],
            bd=0,
            relief="flat"
        )
        self.city_entry.pack(side="left", fill="x", expand=True, padx=10, pady=7)
        self.city_entry.insert(0, "London")  # Default friendly starter city

        # "Get Weather" Button
        self.btn_search = tk.Button(
            search_box_frame,
            text="Get Weather",
            font=FONT_BODY_BOLD,
            bg=THEME["accent"],
            fg="#090d16",
            activebackground=THEME["accent_hover"],
            activeforeground="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.start_weather_fetch
        )
        self.btn_search.pack(side="left", padx=(0, 8))

        # "Detect My Location" Button
        self.btn_detect = tk.Button(
            search_box_frame,
            text="📍 Auto Location",
            font=FONT_BODY_BOLD,
            bg=THEME["bg_card_alt"],
            fg=THEME["text_primary"],
            activebackground=THEME["border"],
            activeforeground=THEME["accent"],
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.start_auto_location
        )
        self.btn_detect.pack(side="left")

        # API Setup Help Button
        self.btn_api_help = tk.Button(
            header_frame,
            text="🔑 API Setup",
            font=FONT_SMALL,
            bg=THEME["bg_card_alt"],
            fg=THEME["text_secondary"],
            activebackground=THEME["border"],
            activeforeground=THEME["accent"],
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.show_api_key_help
        )
        self.btn_api_help.pack(side="right", padx=(8, 0))

        # Unit Toggle (Celsius / Fahrenheit)
        unit_frame = tk.Frame(header_frame, bg=THEME["bg_card_alt"], padx=6, pady=3, highlightbackground=THEME["border"], highlightthickness=1)
        unit_frame.pack(side="right")

        rb_c = ttk.Radiobutton(
            unit_frame,
            text="°C",
            variable=self.unit_var,
            value="metric",
            style="Unit.TRadiobutton",
            command=self._on_unit_toggled
        )
        rb_c.pack(side="left", padx=4)

        rb_f = ttk.Radiobutton(
            unit_frame,
            text="°F",
            variable=self.unit_var,
            value="imperial",
            style="Unit.TRadiobutton",
            command=self._on_unit_toggled
        )
        rb_f.pack(side="left", padx=4)

    # --------------------------------------------------------------------------
    # QUICK LOCATIONS & EXPLORE BAR
    # --------------------------------------------------------------------------
    def _build_quick_locations_bar(self):
        """Horizontal bar with quick-pick location chips, a 30+ world cities dropdown, and saved cities."""
        self.quick_frame = tk.Frame(self, bg=THEME["bg_card"], padx=18, pady=8)
        self.quick_frame.pack(side="top", fill="x", padx=16, pady=(0, 8))

        # Row 1: Popular cities + 30+ World cities dropdown
        row1 = tk.Frame(self.quick_frame, bg=THEME["bg_card"])
        row1.pack(fill="x", expand=True)

        lbl_quick = tk.Label(
            row1,
            text="⚡ Popular:",
            font=FONT_SMALL,
            bg=THEME["bg_card"],
            fg=THEME["accent"]
        )
        lbl_quick.pack(side="left", padx=(0, 6))

        # Popular chips
        popular_chips_frame = tk.Frame(row1, bg=THEME["bg_card"])
        popular_chips_frame.pack(side="left", fill="x", expand=True)

        for display_name, city_query in POPULAR_CITIES:
            btn = tk.Button(
                popular_chips_frame,
                text=display_name,
                font=FONT_SMALL,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_primary"],
                activebackground=THEME["border"],
                activeforeground=THEME["accent"],
                bd=0,
                padx=7,
                pady=2,
                cursor="hand2",
                command=lambda c=city_query: self.select_quick_location(c)
            )
            btn.pack(side="left", padx=2)

        # Explore 30+ World Cities Dropdown
        dropdown_frame = tk.Frame(row1, bg=THEME["bg_card"])
        dropdown_frame.pack(side="right")

        lbl_more = tk.Label(
            dropdown_frame,
            text="🌍 30+ Cities:",
            font=FONT_SMALL,
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"]
        )
        lbl_more.pack(side="left", padx=(0, 6))

        self.more_cities_cb = ttk.Combobox(
            dropdown_frame,
            values=MORE_WORLD_CITIES,
            state="readonly",
            width=18,
            font=FONT_SMALL,
            style="City.TCombobox"
        )
        self.more_cities_cb.set("Select a city...")
        self.more_cities_cb.pack(side="left")
        self.more_cities_cb.bind("<<ComboboxSelected>>", self._on_more_city_selected)

        # Row 2: Saved / Favorite Cities
        self.fav_row = tk.Frame(self.quick_frame, bg=THEME["bg_card"])
        self.fav_row.pack(fill="x", expand=True, pady=(6, 0))

        lbl_fav = tk.Label(
            self.fav_row,
            text="⭐ Saved Cities:",
            font=FONT_SMALL,
            bg=THEME["bg_card"],
            fg=THEME["highlight"]
        )
        lbl_fav.pack(side="left", padx=(0, 6))

        self.fav_chips_frame = tk.Frame(self.fav_row, bg=THEME["bg_card"])
        self.fav_chips_frame.pack(side="left", fill="x", expand=True)

        self._refresh_favorite_chips()

    def _refresh_favorite_chips(self):
        """Re-render the saved cities chips in the quick locations bar."""
        for child in self.fav_chips_frame.winfo_children():
            child.destroy()

        if not self.favorite_cities:
            lbl_empty = tk.Label(
                self.fav_chips_frame,
                text="No saved cities yet. Click '☆ Save City' on any weather card to bookmark it here!",
                font=FONT_SMALL,
                bg=THEME["bg_card"],
                fg=THEME["text_muted"]
            )
            lbl_empty.pack(side="left")
            return

        for city in self.favorite_cities:
            btn = tk.Button(
                self.fav_chips_frame,
                text=city,
                font=FONT_SMALL,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_primary"],
                activebackground=THEME["border"],
                activeforeground=THEME["highlight"],
                bd=0,
                padx=7,
                pady=2,
                cursor="hand2",
                command=lambda c=city: self.select_quick_location(c)
            )
            btn.pack(side="left", padx=2)

    def select_quick_location(self, city: str):
        """Set city in entry box and immediately trigger weather fetch."""
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, city)
        self.start_weather_fetch()

    def _on_more_city_selected(self, event=None):
        """Handle selection from the 30+ world cities dropdown."""
        selected = self.more_cities_cb.get()
        if selected and selected != "Select a city...":
            self.select_quick_location(selected)
            self.more_cities_cb.set("Select a city...")

    def toggle_favorite_current(self):
        """Toggle saving the active city in favorites."""
        if not self.active_city_name:
            city_query = self.city_entry.get().strip()
            if not city_query:
                return
            self.active_city_name = city_query

        target = self.active_city_name
        existing = next((fav for fav in self.favorite_cities if fav.lower() == target.lower()), None)
        if existing:
            self.favorite_cities.remove(existing)
            self.btn_fav.config(text="☆ Save City", fg=THEME["text_secondary"])
            self.lbl_status.config(text=f"Removed '{target}' from saved cities.")
        else:
            self.favorite_cities.append(target)
            self.btn_fav.config(text="⭐ Saved", fg=THEME["highlight"])
            self.lbl_status.config(text=f"Added '{target}' to saved cities.")

        self._refresh_favorite_chips()

    # --------------------------------------------------------------------------
    # CURRENT WEATHER HERO SECTION
    # --------------------------------------------------------------------------
    def _build_current_weather_hero(self):
        """Build the main hero card showing current temperature, icon, and conditions."""
        self.hero_card = tk.Frame(self.scrollable_content, bg=THEME["bg_card"], padx=24, pady=20)
        self.hero_card.pack(fill="x", expand=True, pady=(6, 12))

        # Top row: Location & Time
        top_row = tk.Frame(self.hero_card, bg=THEME["bg_card"])
        top_row.pack(fill="x", expand=True)

        self.lbl_city_country = tk.Label(
            top_row,
            text="Atmosphere Weather",
            font=FONT_HEADING,
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        )
        self.lbl_city_country.pack(side="left")

        # Save / Favorite City Button
        self.btn_fav = tk.Button(
            top_row,
            text="⭐ Saved",
            font=FONT_SMALL,
            bg=THEME["bg_card_alt"],
            fg=THEME["highlight"],
            activebackground=THEME["border"],
            activeforeground=THEME["highlight"],
            bd=0,
            padx=9,
            pady=3,
            cursor="hand2",
            command=self.toggle_favorite_current
        )
        self.btn_fav.pack(side="left", padx=(12, 0))

        self.lbl_local_time = tk.Label(
            top_row,
            text="Enter a city or click Auto Location to begin",
            font=FONT_BODY,
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"]
        )
        self.lbl_local_time.pack(side="right")

        # Middle row: Large Icon + Big Temp + Condition
        mid_row = tk.Frame(self.hero_card, bg=THEME["bg_card"])
        mid_row.pack(fill="x", expand=True, pady=(12, 16))

        # Weather Icon display
        self.lbl_weather_icon = tk.Label(mid_row, bg=THEME["bg_card"])
        self.lbl_weather_icon.pack(side="left", padx=(0, 16))

        # Temp & Condition column
        temp_col = tk.Frame(mid_row, bg=THEME["bg_card"])
        temp_col.pack(side="left")

        self.lbl_temp = tk.Label(
            temp_col,
            text="--°",
            font=FONT_TEMP_HERO,
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        )
        self.lbl_temp.pack(anchor="w")

        self.lbl_condition = tk.Label(
            temp_col,
            text="Awaiting search...",
            font=FONT_TITLE,
            bg=THEME["bg_card"],
            fg=THEME["accent"]
        )
        self.lbl_condition.pack(anchor="w")

        # Metric Details Grid (Feels like, humidity, wind, pressure, visibility)
        self.metrics_frame = tk.Frame(self.hero_card, bg=THEME["bg_card_alt"], padx=16, pady=14)
        self.metrics_frame.pack(fill="x", expand=True)

        for col_idx in range(5):
            self.metrics_frame.columnconfigure(col_idx, weight=1)

        # Metric Card 1: Feels Like
        self.lbl_feels_like_val = self._create_metric_widget(
            self.metrics_frame, col=0, icon="🌡️", label="Feels Like", initial="--"
        )
        # Metric Card 2: Humidity
        self.lbl_humidity_val = self._create_metric_widget(
            self.metrics_frame, col=1, icon="💧", label="Humidity", initial="--"
        )
        # Metric Card 3: Wind Speed
        self.lbl_wind_val = self._create_metric_widget(
            self.metrics_frame, col=2, icon="💨", label="Wind Speed", initial="--"
        )
        # Metric Card 4: Pressure
        self.lbl_pressure_val = self._create_metric_widget(
            self.metrics_frame, col=3, icon="⏲️", label="Pressure", initial="--"
        )
        # Metric Card 5: Visibility
        self.lbl_visibility_val = self._create_metric_widget(
            self.metrics_frame, col=4, icon="👁️", label="Visibility", initial="--"
        )

    def _create_metric_widget(self, parent: tk.Frame, col: int, icon: str, label: str, initial: str) -> tk.Label:
        """Create a single metric cell inside the hero metrics grid."""
        frame = tk.Frame(parent, bg=THEME["bg_card_alt"])
        frame.grid(row=0, column=col, sticky="nsew", padx=6)

        title_lbl = tk.Label(
            frame,
            text=f"{icon} {label}",
            font=FONT_SMALL,
            bg=THEME["bg_card_alt"],
            fg=THEME["text_secondary"]
        )
        title_lbl.pack(anchor="center", pady=(0, 2))

        val_lbl = tk.Label(
            frame,
            text=initial,
            font=FONT_BODY_BOLD,
            bg=THEME["bg_card_alt"],
            fg=THEME["text_primary"]
        )
        val_lbl.pack(anchor="center")
        return val_lbl

    # --------------------------------------------------------------------------
    # HOURLY FORECAST SECTION
    # --------------------------------------------------------------------------
    def _build_hourly_forecast_section(self):
        """Build the next 6-12 hours forecast cards panel."""
        self.hourly_section = tk.Frame(self.scrollable_content, bg=THEME["bg_card"], padx=20, pady=16)
        self.hourly_section.pack(fill="x", expand=True, pady=(0, 12))

        header = tk.Label(
            self.hourly_section,
            text="Hourly Forecast (Next 6 - 12 Hours)",
            font=FONT_SUBTITLE,
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 10))

        # Cards container
        self.hourly_cards_container = tk.Frame(self.hourly_section, bg=THEME["bg_card"])
        self.hourly_cards_container.pack(fill="x", expand=True)

        self.hourly_placeholder = tk.Label(
            self.hourly_cards_container,
            text="Hourly weather predictions will appear here.",
            font=FONT_BODY,
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
            pady=20
        )
        self.hourly_placeholder.pack()

    # --------------------------------------------------------------------------
    # 5-DAY DAILY FORECAST SECTION
    # --------------------------------------------------------------------------
    def _build_daily_forecast_section(self):
        """Build the 5-day daily forecast cards panel."""
        self.daily_section = tk.Frame(self.scrollable_content, bg=THEME["bg_card"], padx=20, pady=16)
        self.daily_section.pack(fill="x", expand=True, pady=(0, 12))

        header = tk.Label(
            self.daily_section,
            text="5-Day Forecast",
            font=FONT_SUBTITLE,
            bg=THEME["bg_card"],
            fg=THEME["text_primary"]
        )
        header.pack(anchor="w", pady=(0, 10))

        # Daily cards container
        self.daily_cards_container = tk.Frame(self.daily_section, bg=THEME["bg_card"])
        self.daily_cards_container.pack(fill="x", expand=True)

        self.daily_placeholder = tk.Label(
            self.daily_cards_container,
            text="5-day upcoming conditions and temperature ranges will appear here.",
            font=FONT_BODY,
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
            pady=20
        )
        self.daily_placeholder.pack()

    # --------------------------------------------------------------------------
    # STATUS BAR
    # --------------------------------------------------------------------------
    def _build_status_bar(self):
        """Bottom status bar displaying loading status, timestamp, and tips."""
        self.status_frame = tk.Frame(self, bg=THEME["bg_card"], padx=14, pady=6)
        self.status_frame.pack(side="bottom", fill="x")

        self.lbl_status = tk.Label(
            self.status_frame,
            text="Ready. Powered by OpenWeatherMap.",
            font=FONT_STATUS,
            bg=THEME["bg_card"],
            fg=THEME["text_secondary"]
        )
        self.lbl_status.pack(side="left")

        self.lbl_update_time = tk.Label(
            self.status_frame,
            text="",
            font=FONT_STATUS,
            bg=THEME["bg_card"],
            fg=THEME["text_muted"]
        )
        self.lbl_update_time.pack(side="right")

    # --------------------------------------------------------------------------
    # API KEY SETUP & HELP
    # --------------------------------------------------------------------------
    def show_api_key_help(self):
        """Show clear instructions on obtaining and setting the OpenWeatherMap API key."""
        msg = (
            "OpenWeatherMap API Key Setup Instructions:\n\n"
            "1. Sign up for a free account at:\n"
            "   https://openweathermap.org/\n\n"
            "2. Navigate to 'My API Keys' in your account dashboard and copy your key.\n\n"
            "3. Paste your key in main.py at line 37:\n"
            "   OPENWEATHER_API_KEY = \"your_actual_key_here\"\n"
            "   (Or configure the OPENWEATHER_API_KEY environment variable)\n\n"
            "Note: Newly generated OpenWeatherMap keys typically require 30 to 120 minutes "
            "to activate on their global CDN servers."
        )
        messagebox.showinfo("API Key Setup", msg)

    # --------------------------------------------------------------------------
    # USER ACTIONS & CONTROLS
    # --------------------------------------------------------------------------
    def start_weather_fetch(self):
        """Initiate weather search for the city specified in the entry field."""
        if self.is_loading:
            return

        city = self.city_entry.get().strip()

        # Input validation: reject empty city input
        if not city:
            messagebox.showwarning("Input Required", "Please enter a city name before searching.")
            self.city_entry.focus_set()
            return

        # Check API key placeholder before network call
        if not self.api_client.validate_api_key():
            self.show_api_key_help()
            return

        self._set_loading(True, f"Fetching weather data for '{city}'...")

        # Run network requests in background thread to keep UI completely responsive
        threading.Thread(
            target=self._fetch_weather_worker,
            args=(city,),
            daemon=True
        ).start()

    def start_auto_location(self):
        """Initiate IP-based auto location detection."""
        if self.is_loading:
            return

        # Check API key before making requests
        if not self.api_client.validate_api_key():
            self.show_api_key_help()
            return

        self._set_loading(True, "Detecting your city via IP address...")

        threading.Thread(
            target=self._auto_location_worker,
            daemon=True
        ).start()

    def _auto_location_worker(self):
        """Worker thread for IP geolocation and subsequent weather fetch."""
        try:
            city = self.api_client.detect_ip_location()

            # Update city entry on main thread
            self.run_on_main_thread(self._on_location_detected, city)

            # Continue fetching weather for detected city in background thread
            current = self.api_client.fetch_current_weather(city)
            forecast = self.api_client.fetch_forecast(city)

            # Pass parsed results back to main GUI thread
            self.run_on_main_thread(self._handle_fetch_success, current, forecast)

        except (ValueError, PermissionError, RuntimeError, ConnectionError) as known_err:
            self.run_on_main_thread(self._handle_worker_error, str(known_err))
        except requests.exceptions.Timeout:
            self.run_on_main_thread(self._handle_worker_error, "Location or weather request timed out. Please check your connection.")
        except requests.exceptions.ConnectionError:
            self.run_on_main_thread(self._handle_worker_error, "Could not reach weather or location services. Check your connection.")
        except Exception as exc:
            self.run_on_main_thread(self._handle_worker_error, f"Auto Location Error: {exc}")

    def _on_location_detected(self, city: str):
        """Update city entry and status text when IP location is found."""
        self.city_entry.delete(0, tk.END)
        self.city_entry.insert(0, city)
        self.lbl_status.config(text=f"Detected location: {city}. Loading weather...", fg=THEME["highlight"])

    def _fetch_weather_worker(self, city: str):
        """Worker thread that executes Current Weather and Forecast API calls."""
        try:
            # 1. Fetch current weather
            current = self.api_client.fetch_current_weather(city)

            # 2. Fetch 5-day / 3-hour forecast
            forecast = self.api_client.fetch_forecast(city)

            # Pass parsed results back to main GUI thread
            self.run_on_main_thread(self._handle_fetch_success, current, forecast)

        except (ValueError, PermissionError, RuntimeError, ConnectionError) as known_err:
            self.run_on_main_thread(self._handle_worker_error, str(known_err))
        except requests.exceptions.Timeout:
            self.run_on_main_thread(self._handle_worker_error, "Network request timed out. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            self.run_on_main_thread(self._handle_worker_error, "Could not connect to OpenWeatherMap. Please check your network connection.")
        except Exception as exc:
            self.run_on_main_thread(self._handle_worker_error, f"An unexpected error occurred: {exc}")

    def _handle_fetch_success(self, current: Dict[str, Any], forecast: Dict[str, Any]):
        """Store fetched data and render GUI components."""
        self.current_data = current
        self.forecast_data = forecast
        self._set_loading(False, f"Weather updated successfully.")

        # Update last updated timestamp
        now_str = datetime.now().strftime("%I:%M %p")
        self.lbl_update_time.config(text=f"Last updated: {now_str}")

        # Render all sections
        self._render_current_weather()
        self._render_hourly_forecast()
        self._render_daily_forecast()

    def _handle_worker_error(self, error_message: str):
        """Show error dialog and reset loading state on main thread."""
        self._set_loading(False, "Error encountered.")
        messagebox.showerror("Weather App Error", error_message)

    def _set_loading(self, loading: bool, message: str = ""):
        """Toggle UI loading state, disable buttons, and update status label."""
        self.is_loading = loading
        if loading:
            self.btn_search.config(state="disabled", text="Loading...")
            self.btn_detect.config(state="disabled")
            self.lbl_status.config(text=message, fg=THEME["highlight"])
        else:
            self.btn_search.config(state="normal", text="Get Weather")
            self.btn_detect.config(state="normal")
            self.lbl_status.config(text=message, fg=THEME["text_secondary"])

    def _on_unit_toggled(self):
        """Instantly re-render currently displayed weather data when °C / °F is changed."""
        if self.current_data and self.forecast_data:
            self._render_current_weather()
            self._render_hourly_forecast()
            self._render_daily_forecast()
            unit_name = "Fahrenheit (°F)" if self.unit_var.get() == "imperial" else "Celsius (°C)"
            self.lbl_status.config(text=f"Switched unit to {unit_name}.")

    # --------------------------------------------------------------------------
    # RENDERING METHODS
    # --------------------------------------------------------------------------
    def _render_current_weather(self):
        """Render the hero section using self.current_data."""
        if not self.current_data:
            return

        data = self.current_data
        unit = self.unit_var.get()

        # City & Country
        city_name = data.get("name", "Unknown")
        sys_data = data.get("sys", {})
        country = sys_data.get("country", "")
        location_title = f"{city_name}, {country}" if country else city_name
        self.lbl_city_country.config(text=location_title)

        # Update active city and synchronize favorite button
        self.active_city_name = city_name
        if any(fav.lower() == city_name.lower() for fav in self.favorite_cities):
            self.btn_fav.config(text="⭐ Saved", fg=THEME["highlight"])
        else:
            self.btn_fav.config(text="☆ Save City", fg=THEME["text_secondary"])

        # Date & Local Time calculation from timezone offset
        tz_offset_sec = data.get("timezone", 0)
        local_dt = datetime.now(timezone.utc) + timedelta(seconds=tz_offset_sec)
        time_str = local_dt.strftime("%A, %B %d • %I:%M %p")
        self.lbl_local_time.config(text=time_str)

        # Main conditions
        main = data.get("main", {})
        temp_c = main.get("temp", 0.0)
        feels_like_c = main.get("feels_like", 0.0)
        humidity = main.get("humidity", 0)
        pressure = main.get("pressure", 0)

        weather_list = data.get("weather", [{}])
        weather_info = weather_list[0] if weather_list else {}
        condition_desc = weather_info.get("description", "Unknown").title()
        icon_code = weather_info.get("icon", "01d")

        wind_data = data.get("wind", {})
        wind_speed_mps = wind_data.get("speed", 0.0)

        visibility_m = data.get("visibility", 10000)
        visibility_km = round(visibility_m / 1000.0, 1)

        # Update labels
        self.lbl_temp.config(text=format_temp(temp_c, unit))
        self.lbl_condition.config(text=condition_desc)
        self.lbl_feels_like_val.config(text=format_temp(feels_like_c, unit))
        self.lbl_humidity_val.config(text=f"{humidity}%")
        self.lbl_wind_val.config(text=format_wind(wind_speed_mps, unit))
        self.lbl_pressure_val.config(text=f"{pressure} hPa")

        if unit == "imperial":
            vis_mi = round(visibility_km * 0.621371, 1)
            self.lbl_visibility_val.config(text=f"{vis_mi} mi")
        else:
            self.lbl_visibility_val.config(text=f"{visibility_km} km")

        # Dynamically load and update hero weather icon
        try:
            icon_img = self.icon_manager.get_icon(icon_code, size=(90, 90))
            self.lbl_weather_icon.config(image=icon_img)
            self.lbl_weather_icon.image = icon_img  # Keep reference
        except Exception as exc:
            logger.warning(f"Error displaying hero icon: {exc}")

    def _render_hourly_forecast(self):
        """Render the next 6-12 hours forecast cards."""
        if not self.forecast_data:
            return

        # Clear existing hourly items
        for child in self.hourly_cards_container.winfo_children():
            child.destroy()

        forecast_list = self.forecast_data.get("list", [])
        if not forecast_list:
            return

        unit = self.unit_var.get()
        tz_offset = self.forecast_data.get("city", {}).get("timezone", 0)

        # Take next 4 slots (3h intervals -> 3h, 6h, 9h, 12h)
        slots = forecast_list[:4]

        # Configure columns evenly
        for i in range(len(slots)):
            self.hourly_cards_container.columnconfigure(i, weight=1)

        for idx, item in enumerate(slots):
            dt_epoch = item.get("dt", 0)
            local_time = datetime.fromtimestamp(dt_epoch, timezone.utc) + timedelta(seconds=tz_offset)
            time_label_text = local_time.strftime("%I:%M %p")

            main_info = item.get("main", {})
            temp_c = main_info.get("temp", 0.0)

            weather_info = item.get("weather", [{}])[0]
            icon_code = weather_info.get("icon", "01d")
            condition = weather_info.get("main", "Clear")

            # Hourly Card Container
            card = tk.Frame(
                self.hourly_cards_container,
                bg=THEME["bg_card_alt"],
                padx=12,
                pady=10,
                highlightbackground=THEME["border"],
                highlightthickness=1
            )
            card.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")

            # Time
            lbl_time = tk.Label(card, text=time_label_text, font=FONT_SMALL, bg=THEME["bg_card_alt"], fg=THEME["text_secondary"])
            lbl_time.pack(anchor="center")

            # Icon
            lbl_icon = tk.Label(card, bg=THEME["bg_card_alt"])
            try:
                card_icon = self.icon_manager.get_icon(icon_code, size=(48, 48))
                lbl_icon.config(image=card_icon)
                lbl_icon.image = card_icon
            except Exception:
                pass
            lbl_icon.pack(anchor="center", pady=2)

            # Temp
            lbl_temp = tk.Label(card, text=format_temp(temp_c, unit), font=FONT_BODY_BOLD, bg=THEME["bg_card_alt"], fg=THEME["text_primary"])
            lbl_temp.pack(anchor="center")

            # Condition
            lbl_cond = tk.Label(card, text=condition, font=FONT_SMALL, bg=THEME["bg_card_alt"], fg=THEME["accent"])
            lbl_cond.pack(anchor="center")

    def _render_daily_forecast(self):
        """Aggregate the 5-day / 3-hour forecast into daily High/Low cards and render them."""
        if not self.forecast_data:
            return

        # Clear existing daily items
        for child in self.daily_cards_container.winfo_children():
            child.destroy()

        forecast_list = self.forecast_data.get("list", [])
        if not forecast_list:
            return

        unit = self.unit_var.get()
        tz_offset = self.forecast_data.get("city", {}).get("timezone", 0)

        # Aggregate data by local date
        daily_buckets: Dict[str, Dict[str, Any]] = {}

        for entry in forecast_list:
            dt_epoch = entry.get("dt", 0)
            local_dt = datetime.fromtimestamp(dt_epoch, timezone.utc) + timedelta(seconds=tz_offset)
            date_key = local_dt.strftime("%Y-%m-%d")

            main = entry.get("main", {})
            temp_min = main.get("temp_min", main.get("temp", 0.0))
            temp_max = main.get("temp_max", main.get("temp", 0.0))

            weather = entry.get("weather", [{}])[0]
            icon = weather.get("icon", "01d")
            desc = weather.get("description", "Clear").title()

            hour = local_dt.hour

            if date_key not in daily_buckets:
                daily_buckets[date_key] = {
                    "weekday": local_dt.strftime("%A"),
                    "date_short": local_dt.strftime("%b %d"),
                    "min_temp": temp_min,
                    "max_temp": temp_max,
                    "icons": [(hour, icon, desc)],
                }
            else:
                b = daily_buckets[date_key]
                b["min_temp"] = min(b["min_temp"], temp_min)
                b["max_temp"] = max(b["max_temp"], temp_max)
                b["icons"].append((hour, icon, desc))

        # Show next 5 days
        display_days = list(daily_buckets.values())[:5]

        # Render clean horizontal row cards for each day
        for idx, day in enumerate(display_days):
            # Select midday icon (closest to 12:00 / 15:00) or first
            icons_sorted = sorted(day["icons"], key=lambda item: abs(item[0] - 13))
            best_hour, best_icon, best_desc = icons_sorted[0]

            row_frame = tk.Frame(
                self.daily_cards_container,
                bg=THEME["bg_card_alt"],
                padx=16,
                pady=10,
                highlightbackground=THEME["border"],
                highlightthickness=1
            )
            row_frame.pack(fill="x", expand=True, pady=4)

            # Day Name & Date
            day_info = tk.Frame(row_frame, bg=THEME["bg_card_alt"], width=140)
            day_info.pack(side="left")
            day_info.pack_propagate(False)

            lbl_weekday = tk.Label(
                day_info,
                text="Today" if idx == 0 else day["weekday"],
                font=FONT_BODY_BOLD,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_primary"]
            )
            lbl_weekday.pack(anchor="w")

            lbl_date = tk.Label(
                day_info,
                text=day["date_short"],
                font=FONT_SMALL,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_secondary"]
            )
            lbl_date.pack(anchor="w")

            # Icon
            lbl_icon = tk.Label(row_frame, bg=THEME["bg_card_alt"])
            try:
                d_icon = self.icon_manager.get_icon(best_icon, size=(42, 42))
                lbl_icon.config(image=d_icon)
                lbl_icon.image = d_icon
            except Exception:
                pass
            lbl_icon.pack(side="left", padx=16)

            # Description
            lbl_desc = tk.Label(
                row_frame,
                text=best_desc,
                font=FONT_BODY,
                bg=THEME["bg_card_alt"],
                fg=THEME["accent"]
            )
            lbl_desc.pack(side="left", fill="x", expand=True)

            # High / Low Temp Display
            temp_range_frame = tk.Frame(row_frame, bg=THEME["bg_card_alt"])
            temp_range_frame.pack(side="right")

            lbl_max = tk.Label(
                temp_range_frame,
                text=format_temp(day["max_temp"], unit),
                font=FONT_BODY_BOLD,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_primary"]
            )
            lbl_max.pack(side="left", padx=4)

            lbl_sep = tk.Label(
                temp_range_frame,
                text="/",
                font=FONT_BODY,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_muted"]
            )
            lbl_sep.pack(side="left")

            lbl_min = tk.Label(
                temp_range_frame,
                text=format_temp(day["min_temp"], unit),
                font=FONT_BODY,
                bg=THEME["bg_card_alt"],
                fg=THEME["text_secondary"]
            )
            lbl_min.pack(side="left", padx=4)


# ==============================================================================
# ENTRY POINT
# ==============================================================================
def main():
    """Main execution function for the desktop app."""
    try:
        app = WeatherApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        logger.critical(f"Fatal application error: {exc}", exc_info=True)
        messagebox.showerror("Fatal Error", f"Atmosphere encountered a fatal crash:\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
