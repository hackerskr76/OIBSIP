"""
Cryptographically Secure Password Generator
============================================
A production-ready desktop application built with Python, Tkinter, and secrets.
Adheres to cybersecurity best practices for strong password generation.

Features:
- Cryptographically secure pseudo-random number generator (CSPRNG) via `secrets`
- Strictly unbiased Fisher-Yates cryptographic permutation
- Guaranteed inclusion of at least one character from every selected category
- Strict validation rules (minimum 8 characters, minimum 2 character categories)
- Live dynamic password strength meter and Shannon entropy calculation
- Ambiguous character filtering (e.g., 0, O, 1, l, I, |)
- Clipboard integration with automatic copy and visual feedback via `pyperclip`
- Ephemeral in-memory session history (never written to disk or database)
- Shoulder-surfing mask/unmask toggle for recent passwords
"""

import collections
import math
import secrets
import string
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Deque, List, Optional, Set, Tuple

import pyperclip

# ==============================================================================
# CONSTANTS & CONFIGURATION
# ==============================================================================

# Character Pools
POOL_UPPERCASE: str = string.ascii_uppercase
POOL_LOWERCASE: str = string.ascii_lowercase
POOL_DIGITS: str = string.digits
# High-entropy, standard punctuation symbols (RFC / OWASP recommended)
POOL_SYMBOLS: str = "!@#$%^&*()_+-=[]{}|;:,.<>?/~"

# Ambiguous characters frequently misread in user interfaces or printed forms
AMBIGUOUS_CHARACTERS: Set[str] = {"0", "O", "1", "l", "I", "|"}

# Validation Rules
MIN_PASSWORD_LENGTH: int = 8
MAX_SLIDER_LENGTH: int = 64
DEFAULT_PASSWORD_LENGTH: int = 16
MIN_SELECTED_POOLS: int = 2
MAX_HISTORY_ENTRIES: int = 5

# Color Palette (Modern Cybersecurity Slate Theme)
THEME = {
    "bg_main": "#0f172a",          # Dark Slate 900
    "bg_card": "#1e293b",          # Dark Slate 800
    "bg_input": "#090d16",         # Deep Black/Navy
    "bg_hover": "#334155",         # Slate 700
    "fg_primary": "#f8fafc",       # Off-white / Slate 50
    "fg_secondary": "#94a3b8",     # Slate 400
    "fg_muted": "#64748b",         # Slate 500
    "accent_primary": "#3b82f6",   # Electric Blue 500
    "accent_hover": "#2563eb",     # Blue 600
    "accent_success": "#10b981",   # Emerald 500
    "accent_warning": "#f59e0b",   # Amber 500
    "accent_danger": "#ef4444",    # Rose / Red 500
    "accent_purple": "#8b5cf6",    # Violet 500
    "border": "#334155",           # Slate 700
}


# ==============================================================================
# CORE DOMAIN & CRYPTOGRAPHY LOGIC
# ==============================================================================

@dataclass
class PasswordCriteria:
    """Holds user-specified parameters for password generation."""
    length: int
    use_uppercase: bool
    use_lowercase: bool
    use_numbers: bool
    use_symbols: bool
    exclude_ambiguous: bool


class PasswordGenerator:
    """
    Cryptographically secure password generation engine.
    Uses the OS-level CSPRNG provided by Python's `secrets` module.
    Never relies on deterministic pseudo-random generators (`random`).
    """

    @staticmethod
    def get_character_pools(criteria: PasswordCriteria) -> List[Tuple[str, str]]:
        """
        Builds the active character pools based on criteria.
        Returns a list of tuples: (pool_name, filtered_characters).
        """
        active_pools: List[Tuple[str, str]] = []

        def filter_pool(chars: str) -> str:
            if criteria.exclude_ambiguous:
                return "".join(c for c in chars if c not in AMBIGUOUS_CHARACTERS)
            return chars

        if criteria.use_uppercase:
            pool = filter_pool(POOL_UPPERCASE)
            if pool:
                active_pools.append(("Uppercase", pool))

        if criteria.use_lowercase:
            pool = filter_pool(POOL_LOWERCASE)
            if pool:
                active_pools.append(("Lowercase", pool))

        if criteria.use_numbers:
            pool = filter_pool(POOL_DIGITS)
            if pool:
                active_pools.append(("Numbers", pool))

        if criteria.use_symbols:
            pool = filter_pool(POOL_SYMBOLS)
            if pool:
                active_pools.append(("Symbols", pool))

        return active_pools

    @staticmethod
    def validate_criteria(criteria: PasswordCriteria) -> None:
        """
        Validates criteria against core cybersecurity requirements.
        Raises ValueError with an explanatory message upon violation.
        """
        if criteria.length < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password length must be at least {MIN_PASSWORD_LENGTH} characters.\n"
                f"Shorter lengths do not provide sufficient entropy against modern cracking techniques."
            )

        active_pools = PasswordGenerator.get_character_pools(criteria)
        if len(active_pools) < MIN_SELECTED_POOLS:
            raise ValueError(
                f"At least {MIN_SELECTED_POOLS} character types must be selected.\n"
                f"Combining multiple character spaces significantly expands the keyspace."
            )

    @classmethod
    def generate(cls, criteria: PasswordCriteria) -> str:
        """
        Generates a cryptographically secure password satisfying all criteria.
        
        Guarantees:
        1. Strict inclusion: At least one character from each selected category.
        2. Uniform distribution: Remaining positions sampled from the combined pool.
        3. Cryptographic permutation: Shuffled in-place via Fisher-Yates with `secrets.randbelow`.
        """
        cls.validate_criteria(criteria)
        active_pools = cls.get_character_pools(criteria)

        # 1. Guarantee strict inclusion: 1 character from each chosen pool
        password_chars: List[str] = [
            secrets.choice(pool_chars) for _, pool_chars in active_pools
        ]

        # 2. Combined pool for remaining characters
        combined_pool = "".join(pool_chars for _, pool_chars in active_pools)
        remaining_count = criteria.length - len(password_chars)

        for _ in range(remaining_count):
            password_chars.append(secrets.choice(combined_pool))

        # 3. Cryptographic Fisher-Yates Shuffle
        # Ensures uniform permutation without relying on random.shuffle
        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

        return "".join(password_chars)


# ==============================================================================
# PASSWORD STRENGTH & ENTROPY ANALYZER
# ==============================================================================

@dataclass
class StrengthReport:
    """Analytical evaluation of a password's cryptographic strength."""
    score_percentage: int
    label: str
    color: str
    entropy_bits: float
    description: str


class PasswordStrengthAnalyzer:
    """Evaluates password strength using Shannon entropy and character space metrics."""

    @staticmethod
    def evaluate(criteria: PasswordCriteria) -> StrengthReport:
        active_pools = PasswordGenerator.get_character_pools(criteria)
        pool_size = sum(len(pool_chars) for _, pool_chars in active_pools)

        if pool_size == 0 or criteria.length <= 0:
            return StrengthReport(
                score_percentage=0,
                label="Invalid",
                color=THEME["fg_muted"],
                entropy_bits=0.0,
                description="Select valid criteria to evaluate strength."
            )

        # Shannon Entropy Formula: H = L * log2(R)
        entropy = criteria.length * math.log2(pool_size)

        # Evaluation thresholds based on NIST & OWASP password guidelines
        if criteria.length < MIN_PASSWORD_LENGTH or len(active_pools) < MIN_SELECTED_POOLS or entropy < 50:
            score = min(35, int((entropy / 50) * 35))
            return StrengthReport(
                score_percentage=max(10, score),
                label="Weak",
                color=THEME["accent_danger"],
                entropy_bits=entropy,
                description=f"Vulnerable to automated brute-force ({entropy:.1f} bits)."
            )
        elif entropy < 72:
            score = 35 + int(((entropy - 50) / 22) * 30)
            return StrengthReport(
                score_percentage=score,
                label="Medium",
                color=THEME["accent_warning"],
                entropy_bits=entropy,
                description=f"Acceptable for low-risk accounts ({entropy:.1f} bits)."
            )
        elif entropy < 95:
            score = 65 + int(((entropy - 72) / 23) * 25)
            return StrengthReport(
                score_percentage=score,
                label="Strong",
                color=THEME["accent_success"],
                entropy_bits=entropy,
                description=f"Highly resilient against offline cracking ({entropy:.1f} bits)."
            )
        else:
            score = min(100, 90 + int(((entropy - 95) / 30) * 10))
            return StrengthReport(
                score_percentage=score,
                label="Very Strong",
                color=THEME["accent_purple"],
                entropy_bits=entropy,
                description=f"Military/Enterprise-grade security ({entropy:.1f} bits)."
            )


# ==============================================================================
# VOLATILE SESSION HISTORY MANAGER
# ==============================================================================

@dataclass
class HistoryEntry:
    timestamp: str
    password: str
    strength_label: str
    strength_color: str


class SessionHistoryManager:
    """
    In-memory FIFO history buffer.
    
    SECURITY CONTRACT:
    - Lives exclusively in volatile memory (RAM).
    - Never written to persistent storage, filesystem, or database.
    - Automatically cleared when the application exits or when user requests.
    """

    def __init__(self, max_size: int = MAX_HISTORY_ENTRIES):
        self._history: Deque[HistoryEntry] = collections.deque(maxlen=max_size)

    def add(self, password: str, strength_label: str, strength_color: str) -> None:
        timestamp_str = time.strftime("%H:%M:%S")
        self._history.appendleft(
            HistoryEntry(
                timestamp=timestamp_str,
                password=password,
                strength_label=strength_label,
                strength_color=strength_color
            )
        )

    def get_entries(self) -> List[HistoryEntry]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()


# ==============================================================================
# GRAPHICAL USER INTERFACE (TKINTER OOP)
# ==============================================================================

class PasswordGeneratorApp:
    """Main Application GUI orchestrating user interaction and cryptographic logic."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("KeyShield — Cryptographically Secure Password Generator")
        self.root.geometry("640x780")
        self.root.minsize(580, 700)
        self.root.configure(bg=THEME["bg_main"])

        # Core State
        self.history_manager = SessionHistoryManager(max_size=MAX_HISTORY_ENTRIES)
        self.mask_history = tk.BooleanVar(value=False)
        self.auto_copy_var = tk.BooleanVar(value=True)

        # Control Variables
        self.length_var = tk.IntVar(value=DEFAULT_PASSWORD_LENGTH)
        self.uppercase_var = tk.BooleanVar(value=True)
        self.lowercase_var = tk.BooleanVar(value=True)
        self.numbers_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.exclude_ambiguous_var = tk.BooleanVar(value=False)
        self.password_display_var = tk.StringVar(value="")
        self.status_message_var = tk.StringVar(value="Ready. Configure your preferences and generate.")

        # GUI Components references
        self.strength_canvas: Optional[tk.Canvas] = None
        self.strength_label: Optional[tk.Label] = None
        self.strength_desc_label: Optional[tk.Label] = None
        self.history_container: Optional[tk.Frame] = None
        self._toast_after_id: Optional[str] = None

        self._init_styles()
        self._build_ui()
        self._bind_events()

        # Generate an initial password on startup
        self.generate_password()

    def _init_styles(self) -> None:
        """Configures ttk styles for consistent theme integration."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Checkbutton styling
        style.configure(
            "Dark.TCheckbutton",
            background=THEME["bg_card"],
            foreground=THEME["fg_primary"],
            font=("Segoe UI", 10),
            focuscolor=THEME["bg_card"]
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", THEME["bg_card"])],
            foreground=[("active", THEME["accent_primary"])]
        )

        # Scale slider styling
        style.configure(
            "Dark.Horizontal.TScale",
            background=THEME["bg_card"],
            troughcolor=THEME["bg_input"],
            sliderrelief="flat"
        )

    def _build_ui(self) -> None:
        """Constructs the structured GUI layout."""
        # Top-level Scrollable/Padding Canvas or Main Frame
        main_container = tk.Frame(self.root, bg=THEME["bg_main"], padx=20, pady=16)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Header Section
        self._build_header(main_container)

        # 2. Password Result & Action Frame
        self._build_result_section(main_container)

        # 3. Dynamic Strength Indicator Section
        self._build_strength_section(main_container)

        # 4. Configuration Controls Section
        self._build_controls_section(main_container)

        # 5. Session History Section
        self._build_history_section(main_container)

        # 6. Status / Footer Bar
        self._build_status_bar(main_container)

    def _build_header(self, parent: tk.Frame) -> None:
        header_frame = tk.Frame(parent, bg=THEME["bg_main"])
        header_frame.pack(fill=tk.X, pady=(0, 12))

        title_label = tk.Label(
            header_frame,
            text="🔒 KeyShield Password Generator",
            font=("Segoe UI", 17, "bold"),
            fg=THEME["fg_primary"],
            bg=THEME["bg_main"]
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            header_frame,
            text="Cryptographically Secure Pseudo-Random Number Generator (CSPRNG via Python secrets)",
            font=("Segoe UI", 9),
            fg=THEME["fg_secondary"],
            bg=THEME["bg_main"]
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

    def _build_result_section(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=14
        )
        card.pack(fill=tk.X, pady=(0, 10))

        # Result Label Header
        res_header = tk.Frame(card, bg=THEME["bg_card"])
        res_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            res_header,
            text="GENERATED PASSWORD",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["fg_muted"],
            bg=THEME["bg_card"]
        ).pack(side=tk.LEFT)

        self.auto_copy_checkbox = ttk.Checkbutton(
            res_header,
            text="Auto-copy on generate",
            variable=self.auto_copy_var,
            style="Dark.TCheckbutton"
        )
        self.auto_copy_checkbox.pack(side=tk.RIGHT)

        # Password Entry Display Box
        display_frame = tk.Frame(card, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        display_frame.pack(fill=tk.X, pady=(0, 10))

        self.password_entry = tk.Entry(
            display_frame,
            textvariable=self.password_display_var,
            font=("Consolas", 14, "bold"),
            fg=THEME["accent_primary"],
            bg=THEME["bg_input"],
            bd=0,
            relief="flat",
            justify="center",
            insertbackground=THEME["fg_primary"]
        )
        self.password_entry.pack(fill=tk.X, ipady=10, padx=10)

        # Primary Action Buttons Frame
        btn_frame = tk.Frame(card, bg=THEME["bg_card"])
        btn_frame.pack(fill=tk.X)

        self.generate_btn = tk.Button(
            btn_frame,
            text="⚡ Generate New Password",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg=THEME["accent_primary"],
            activebackground=THEME["accent_hover"],
            activeforeground="#ffffff",
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=8,
            command=self.generate_password
        )
        self.generate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.copy_btn = tk.Button(
            btn_frame,
            text="📋 Copy to Clipboard",
            font=("Segoe UI", 10, "bold"),
            fg=THEME["fg_primary"],
            bg=THEME["bg_hover"],
            activebackground=THEME["border"],
            activeforeground=THEME["fg_primary"],
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=8,
            command=lambda: self.copy_to_clipboard(self.password_display_var.get())
        )
        self.copy_btn.pack(side=tk.RIGHT)

    def _build_strength_section(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=10
        )
        card.pack(fill=tk.X, pady=(0, 10))

        header_frame = tk.Frame(card, bg=THEME["bg_card"])
        header_frame.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            header_frame,
            text="SECURITY STRENGTH METER",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["fg_muted"],
            bg=THEME["bg_card"]
        ).pack(side=tk.LEFT)

        self.strength_label = tk.Label(
            header_frame,
            text="Evaluating...",
            font=("Segoe UI", 9, "bold"),
            fg=THEME["accent_success"],
            bg=THEME["bg_card"]
        )
        self.strength_label.pack(side=tk.RIGHT)

        # Custom High-Quality Canvas Bar (avoids native OS progressbar theme glitches)
        self.strength_canvas = tk.Canvas(
            card,
            height=10,
            bg=THEME["bg_input"],
            bd=0,
            highlightthickness=1,
            highlightbackground=THEME["border"]
        )
        self.strength_canvas.pack(fill=tk.X, pady=(0, 6))

        self.strength_desc_label = tk.Label(
            card,
            text="",
            font=("Segoe UI", 8),
            fg=THEME["fg_secondary"],
            bg=THEME["bg_card"],
            anchor="w"
        )
        self.strength_desc_label.pack(fill=tk.X)

    def _build_controls_section(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=12
        )
        card.pack(fill=tk.X, pady=(0, 10))

        # Title
        tk.Label(
            card,
            text="GENERATION PREFERENCES & CRITERIA",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["fg_muted"],
            bg=THEME["bg_card"]
        ).pack(anchor="w", pady=(0, 8))

        # --- Password Length Control (Slider + Spinbox) ---
        len_container = tk.Frame(card, bg=THEME["bg_card"])
        len_container.pack(fill=tk.X, pady=(0, 12))

        len_top = tk.Frame(len_container, bg=THEME["bg_card"])
        len_top.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            len_top,
            text="Password Length (Min: 8):",
            font=("Segoe UI", 10),
            fg=THEME["fg_primary"],
            bg=THEME["bg_card"]
        ).pack(side=tk.LEFT)

        # Spinbox for precise input
        self.length_spinbox = tk.Spinbox(
            len_top,
            from_=MIN_PASSWORD_LENGTH,
            to=128,
            textvariable=self.length_var,
            width=5,
            font=("Segoe UI", 10, "bold"),
            fg=THEME["fg_primary"],
            bg=THEME["bg_input"],
            buttonbackground=THEME["bg_hover"],
            relief="flat",
            justify="center",
            command=self._on_spinbox_change
        )
        self.length_spinbox.pack(side=tk.RIGHT)
        self.length_spinbox.bind("<KeyRelease>", lambda e: self._on_spinbox_change())

        # Scale Slider
        self.length_scale = ttk.Scale(
            len_container,
            from_=MIN_PASSWORD_LENGTH,
            to=MAX_SLIDER_LENGTH,
            orient=tk.HORIZONTAL,
            variable=self.length_var,
            style="Dark.Horizontal.TScale",
            command=self._on_slider_change
        )
        self.length_scale.pack(fill=tk.X)

        # --- Character Types Checkboxes Grid ---
        chars_grid = tk.Frame(card, bg=THEME["bg_card"])
        chars_grid.pack(fill=tk.X, pady=(0, 8))

        # Row 1: Uppercase & Lowercase
        self.chk_upper = ttk.Checkbutton(
            chars_grid,
            text="Uppercase Letters (A-Z)",
            variable=self.uppercase_var,
            style="Dark.TCheckbutton",
            command=self._on_criteria_change
        )
        self.chk_upper.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)

        self.chk_lower = ttk.Checkbutton(
            chars_grid,
            text="Lowercase Letters (a-z)",
            variable=self.lowercase_var,
            style="Dark.TCheckbutton",
            command=self._on_criteria_change
        )
        self.chk_lower.grid(row=0, column=1, sticky="w", pady=4)

        # Row 2: Numbers & Symbols
        self.chk_numbers = ttk.Checkbutton(
            chars_grid,
            text="Numbers (0-9)",
            variable=self.numbers_var,
            style="Dark.TCheckbutton",
            command=self._on_criteria_change
        )
        self.chk_numbers.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)

        self.chk_symbols = ttk.Checkbutton(
            chars_grid,
            text="Special Symbols (!@#$%)",
            variable=self.symbols_var,
            style="Dark.TCheckbutton",
            command=self._on_criteria_change
        )
        self.chk_symbols.grid(row=1, column=1, sticky="w", pady=4)

        # --- Security Filter: Ambiguous Characters ---
        filter_frame = tk.Frame(card, bg=THEME["bg_card"])
        filter_frame.pack(fill=tk.X, pady=(6, 0))

        self.chk_ambiguous = ttk.Checkbutton(
            filter_frame,
            text="Exclude Ambiguous Characters (0, O, 1, l, I, |)",
            variable=self.exclude_ambiguous_var,
            style="Dark.TCheckbutton",
            command=self._on_criteria_change
        )
        self.chk_ambiguous.pack(anchor="w")

    def _build_history_section(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=10
        )
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Header with actions
        hist_header = tk.Frame(card, bg=THEME["bg_card"])
        hist_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            hist_header,
            text="SESSION HISTORY (LAST 5 — IN-MEMORY ONLY)",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["fg_muted"],
            bg=THEME["bg_card"]
        ).pack(side=tk.LEFT)

        action_box = tk.Frame(hist_header, bg=THEME["bg_card"])
        action_box.pack(side=tk.RIGHT)

        mask_chk = ttk.Checkbutton(
            action_box,
            text="Mask passwords",
            variable=self.mask_history,
            style="Dark.TCheckbutton",
            command=self._refresh_history_ui
        )
        mask_chk.pack(side=tk.LEFT, padx=(0, 8))

        clear_btn = tk.Button(
            action_box,
            text="🗑 Clear",
            font=("Segoe UI", 8),
            fg=THEME["fg_secondary"],
            bg=THEME["bg_card"],
            activebackground=THEME["bg_hover"],
            activeforeground=THEME["fg_primary"],
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.clear_history
        )
        clear_btn.pack(side=tk.LEFT)

        # Container where history rows will be dynamically placed
        self.history_container = tk.Frame(card, bg=THEME["bg_card"])
        self.history_container.pack(fill=tk.BOTH, expand=True)

        # Security disclaimer note
        tk.Label(
            card,
            text="🛡 Stored strictly in volatile RAM. Permanently destroyed upon closing this window.",
            font=("Segoe UI", 7, "italic"),
            fg=THEME["fg_muted"],
            bg=THEME["bg_card"]
        ).pack(anchor="w", pady=(6, 0))

    def _build_status_bar(self, parent: tk.Frame) -> None:
        status_frame = tk.Frame(parent, bg=THEME["bg_main"])
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_message_var,
            font=("Segoe UI", 8),
            fg=THEME["accent_success"],
            bg=THEME["bg_main"],
            anchor="w"
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        csprng_badge = tk.Label(
            status_frame,
            text="🔒 CSPRNG Verified",
            font=("Segoe UI", 8, "bold"),
            fg=THEME["accent_primary"],
            bg=THEME["bg_main"]
        )
        csprng_badge.pack(side=tk.RIGHT)

    def _bind_events(self) -> None:
        """Binds keyboard shortcuts for optimal productivity."""
        self.root.bind("<Return>", lambda event: self.generate_password())
        self.root.bind("<Control-g>", lambda event: self.generate_password())
        self.root.bind("<Control-c>", lambda event: self._on_copy_shortcut())

    # ==========================================================================
    # USER ACTION HANDLERS & VALIDATION
    # ==========================================================================

    def _get_current_criteria(self) -> PasswordCriteria:
        try:
            length = int(self.length_var.get())
        except Exception:
            length = MIN_PASSWORD_LENGTH

        return PasswordCriteria(
            length=length,
            use_uppercase=self.uppercase_var.get(),
            use_lowercase=self.lowercase_var.get(),
            use_numbers=self.numbers_var.get(),
            use_symbols=self.symbols_var.get(),
            exclude_ambiguous=self.exclude_ambiguous_var.get()
        )

    def _on_slider_change(self, value: str) -> None:
        try:
            int_val = int(float(value))
            self.length_var.set(int_val)
        except Exception:
            pass
        self._on_criteria_change()

    def _on_spinbox_change(self) -> None:
        try:
            val = int(self.length_var.get())
            if val > MAX_SLIDER_LENGTH:
                # Keep slider pegged to max without capping the spinbox
                self.length_scale.set(MAX_SLIDER_LENGTH)
            else:
                self.length_scale.set(val)
        except Exception:
            pass
        self._on_criteria_change()

    def _on_criteria_change(self) -> None:
        """Dynamically updates the live strength meter whenever criteria change."""
        criteria = self._get_current_criteria()
        report = PasswordStrengthAnalyzer.evaluate(criteria)
        self._update_strength_ui(report)

    def _on_copy_shortcut(self) -> None:
        if self.password_display_var.get():
            self.copy_to_clipboard(self.password_display_var.get())

    def generate_password(self) -> None:
        """Validates criteria, generates password via CSPRNG, updates UI, and manages history."""
        criteria = self._get_current_criteria()

        # Enforce validation: Minimum Length
        if criteria.length < MIN_PASSWORD_LENGTH:
            messagebox.showwarning(
                "Password Length Validation Warning",
                f"Password length cannot be less than {MIN_PASSWORD_LENGTH} characters.\n\n"
                f"Cybersecurity guidelines mandate at least {MIN_PASSWORD_LENGTH} characters "
                f"to protect against automated password-cracking attacks."
            )
            self.length_var.set(MIN_PASSWORD_LENGTH)
            self.length_scale.set(MIN_PASSWORD_LENGTH)
            self._on_criteria_change()
            return

        # Enforce validation: Minimum 2 Character Types
        active_pools = PasswordGenerator.get_character_pools(criteria)
        if len(active_pools) < MIN_SELECTED_POOLS:
            messagebox.showwarning(
                "Character Set Diversity Warning",
                f"At least {MIN_SELECTED_POOLS} character types must be selected.\n\n"
                f"Please enable at least two categories (Uppercase, Lowercase, Numbers, or Symbols) "
                f"to guarantee adequate character entropy."
            )
            return

        try:
            # Cryptographically secure generation
            password = PasswordGenerator.generate(criteria)
            self.password_display_var.set(password)

            # Evaluate strength
            strength = PasswordStrengthAnalyzer.evaluate(criteria)
            self._update_strength_ui(strength)

            # Add to ephemeral in-memory session history
            self.history_manager.add(password, strength.label, strength.color)
            self._refresh_history_ui()

            # Automatic clipboard copying if enabled
            if self.auto_copy_var.get():
                self.copy_to_clipboard(password, is_auto=True)
            else:
                self.set_status("✓ New cryptographically secure password generated.", THEME["accent_success"])

        except Exception as ex:
            messagebox.showerror("Password Generation Error", f"An unexpected error occurred:\n{str(ex)}")

    def copy_to_clipboard(self, text: str, is_auto: bool = False) -> None:
        """Copies text to the system clipboard via pyperclip with fallback and visual feedback."""
        if not text:
            return

        try:
            pyperclip.copy(text)
        except Exception:
            # Fallback to Tkinter clipboard if pyperclip fails on unusual OS configs
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
            except Exception as e:
                self.set_status(f"Clipboard error: {str(e)}", THEME["accent_danger"])
                return

        feedback_msg = "✓ Copied to clipboard! (Auto-copy active)" if is_auto else "✓ Copied to clipboard!"
        self.set_status(feedback_msg, THEME["accent_success"])

    def set_status(self, message: str, color: str = THEME["fg_secondary"]) -> None:
        """Displays transient feedback message on the status bar."""
        self.status_message_var.set(message)
        self.status_label.configure(fg=color)

        if self._toast_after_id:
            self.root.after_cancel(self._toast_after_id)

        # Clear toast after 3 seconds
        self._toast_after_id = self.root.after(
            3000,
            lambda: self.status_message_var.set("Ready. CSPRNG engine active.")
        )

    def clear_history(self) -> None:
        """Wipes the in-memory session history."""
        self.history_manager.clear()
        self._refresh_history_ui()
        self.set_status("Session history purged from memory.", THEME["fg_muted"])

    # ==========================================================================
    # UI RENDERING & DYNAMIC UPDATES
    # ==========================================================================

    def _update_strength_ui(self, report: StrengthReport) -> None:
        """Draws dynamic bar and updates labels according to the strength evaluation."""
        if not self.strength_canvas:
            return

        self.strength_label.configure(text=f"{report.label} ({report.entropy_bits:.1f} bits)", fg=report.color)
        self.strength_desc_label.configure(text=report.description)

        # Redraw canvas bar
        self.strength_canvas.delete("all")
        canvas_width = self.strength_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 560  # Default initial fallback width

        fill_width = int((report.score_percentage / 100.0) * canvas_width)
        fill_width = max(6, fill_width)

        # Render filled progress segment
        self.strength_canvas.create_rectangle(
            0, 0, fill_width, 10,
            fill=report.color,
            outline=""
        )

    def _refresh_history_ui(self) -> None:
        """Re-renders the session history cards."""
        if not self.history_container:
            return

        for child in self.history_container.winfo_children():
            child.destroy()

        entries = self.history_manager.get_entries()
        if not entries:
            empty_lbl = tk.Label(
                self.history_container,
                text="No passwords generated in this session yet.",
                font=("Segoe UI", 9, "italic"),
                fg=THEME["fg_muted"],
                bg=THEME["bg_card"],
                pady=12
            )
            empty_lbl.pack()
            return

        for entry in entries:
            row = tk.Frame(
                self.history_container,
                bg=THEME["bg_input"],
                highlightbackground=THEME["border"],
                highlightthickness=1,
                padx=10,
                pady=4
            )
            row.pack(fill=tk.X, pady=2)

            # Timestamp badge
            tk.Label(
                row,
                text=entry.timestamp,
                font=("Consolas", 8),
                fg=THEME["fg_muted"],
                bg=THEME["bg_input"],
                width=8,
                anchor="w"
            ).pack(side=tk.LEFT)

            # Password text (masked or unmasked)
            display_pwd = "•" * len(entry.password) if self.mask_history.get() else entry.password
            pwd_lbl = tk.Label(
                row,
                text=display_pwd,
                font=("Consolas", 9, "bold"),
                fg=THEME["fg_primary"],
                bg=THEME["bg_input"],
                anchor="w"
            )
            pwd_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

            # Strength Pill
            tk.Label(
                row,
                text=entry.strength_label,
                font=("Segoe UI", 8, "bold"),
                fg=entry.strength_color,
                bg=THEME["bg_input"],
                padx=6
            ).pack(side=tk.LEFT)

            # Copy button for this specific item
            copy_item_btn = tk.Button(
                row,
                text="Copy",
                font=("Segoe UI", 8),
                fg=THEME["fg_primary"],
                bg=THEME["bg_hover"],
                activebackground=THEME["border"],
                activeforeground=THEME["fg_primary"],
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=8,
                pady=2,
                command=lambda p=entry.password: self.copy_to_clipboard(p)
            )
            copy_item_btn.pack(side=tk.RIGHT)


# ==============================================================================
# APPLICATION ENTRYPOINT
# ==============================================================================

def main() -> None:
    """Initializes and runs the KeyShield GUI application."""
    root = tk.Tk()
    
    # Configure high DPI scaling awareness on Windows if supported
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = PasswordGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
