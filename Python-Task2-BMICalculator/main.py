import sys
import os
import csv
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.dates as mdates

import database

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


BMI_CATEGORIES = {
    "Underweight": {
        "label": "Underweight",
        "range_text": "< 18.5",
        "color": "#0284C7",
        "bg_pill": "#E0F2FE",
        "advice": "Your BMI indicates you may be underweight. Ensure adequate nutrition and consult a healthcare provider."
    },
    "Normal": {
        "label": "Normal",
        "range_text": "18.5 - 24.9",
        "color": "#16A34A",
        "bg_pill": "#DCFCE7",
        "advice": "Great work! Your BMI falls within the healthy, recommended weight range for optimal wellness."
    },
    "Overweight": {
        "label": "Overweight",
        "range_text": "25.0 - 29.9",
        "color": "#D97706",
        "bg_pill": "#FEF3C7",
        "advice": "Your BMI falls in the overweight range. Incorporating regular exercise and a balanced diet can help."
    },
    "Obese": {
        "label": "Obese",
        "range_text": ">= 30.0",
        "color": "#DC2626",
        "bg_pill": "#FEE2E2",
        "advice": "Your BMI indicates obesity, which may increase health risks. Consult a doctor for tailored medical guidance."
    }
}


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)


def get_bmi_category(bmi: float) -> Tuple[str, Dict[str, Any]]:
    if bmi < 18.5:
        key = "Underweight"
    elif bmi < 25.0:
        key = "Normal"
    elif bmi < 30.0:
        key = "Overweight"
    else:
        key = "Obese"
    return key, BMI_CATEGORIES[key]


class BMICalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BMI Health Tracker & Calculator")
        self.geometry("640x780")
        self.minsize(560, 680)

        self.COLOR_BG = "#F8FAFC"
        self.COLOR_CARD = "#FFFFFF"
        self.COLOR_PRIMARY = "#2563EB"
        self.COLOR_PRIMARY_HOVER = "#1D4ED8"
        self.COLOR_TEXT_MAIN = "#0F172A"
        self.COLOR_TEXT_MUTED = "#64748B"
        self.COLOR_BORDER = "#E2E8F0"

        self.configure(bg=self.COLOR_BG)

        try:
            database.init_db()
        except database.DatabaseError as e:
            messagebox.showerror("Database Initialization Error", f"Failed to initialize SQLite database:\n{e}")

        self._setup_styles()
        self._build_header()
        self._build_input_card()
        self._build_result_card()
        self._build_history_card()
        self._build_status_bar()

        self._refresh_user_list()
        self.bind("<Return>", lambda event: self.handle_calculate_and_save())

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=self.COLOR_BG)
        style.configure("Card.TFrame", background=self.COLOR_CARD, relief="solid", borderwidth=1)

        style.configure("HeaderTitle.TLabel", background=self.COLOR_BG, foreground=self.COLOR_TEXT_MAIN,
                        font=("Segoe UI", 18, "bold"))
        style.configure("HeaderSubtitle.TLabel", background=self.COLOR_BG, foreground=self.COLOR_TEXT_MUTED,
                        font=("Segoe UI", 10))
        style.configure("FieldLabel.TLabel", background=self.COLOR_CARD, foreground=self.COLOR_TEXT_MAIN,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Helper.TLabel", background=self.COLOR_CARD, foreground=self.COLOR_TEXT_MUTED,
                        font=("Segoe UI", 8))

        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"),
                        background=self.COLOR_PRIMARY, foreground="#FFFFFF", borderwidth=0, padding=8)
        style.map("Primary.TButton",
                  background=[("active", self.COLOR_PRIMARY_HOVER), ("pressed", "#1E40AF")],
                  foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])

        style.configure("Secondary.TButton", font=("Segoe UI", 9),
                        background="#F1F5F9", foreground=self.COLOR_TEXT_MAIN, borderwidth=1, padding=6)
        style.map("Secondary.TButton",
                  background=[("active", "#E2E8F0")],
                  foreground=[("active", self.COLOR_TEXT_MAIN)])

        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"),
                        background="#0EA5E9", foreground="#FFFFFF", padding=6)
        style.map("Accent.TButton",
                  background=[("active", "#0284C7")])

    def _build_header(self):
        header_frame = ttk.Frame(self, style="TFrame", padding="20 16 20 8")
        header_frame.pack(fill="x")

        title = ttk.Label(header_frame, text="⚖️  BMI Calculator & Health Tracker", style="HeaderTitle.TLabel")
        title.pack(anchor="w")

        subtitle = ttk.Label(
            header_frame,
            text="Track your Body Mass Index, record multi-user health trends, and visualize progress over time.",
            style="HeaderSubtitle.TLabel"
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_input_card(self):
        card_outer = tk.Frame(self, bg=self.COLOR_BORDER, padx=1, pady=1)
        card_outer.pack(fill="x", padx=20, pady=8)

        card = tk.Frame(card_outer, bg=self.COLOR_CARD, padx=18, pady=16)
        card.pack(fill="both", expand=True)

        card_title = tk.Label(card, text="👤 Enter User Metrics", font=("Segoe UI", 11, "bold"),
                              bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MAIN)
        card_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        name_lbl = tk.Label(card, text="User / Name:", font=("Segoe UI", 9, "bold"),
                            bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MAIN)
        name_lbl.grid(row=1, column=0, sticky="w", pady=6)

        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(card, textvariable=self.user_var, font=("Segoe UI", 10), width=26)
        self.user_combo.grid(row=1, column=1, sticky="w", pady=6, padx=(8, 4))
        self.user_combo.bind("<<ComboboxSelected>>", self._on_user_selected)

        user_hint = tk.Label(card, text="(Select or type new name)", font=("Segoe UI", 8),
                             bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MUTED)
        user_hint.grid(row=1, column=2, sticky="w", padx=4)

        weight_lbl = tk.Label(card, text="Weight (kg):", font=("Segoe UI", 9, "bold"),
                              bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MAIN)
        weight_lbl.grid(row=2, column=0, sticky="w", pady=6)

        self.weight_var = tk.StringVar()
        self.weight_entry = ttk.Entry(card, textvariable=self.weight_var, font=("Segoe UI", 10), width=28)
        self.weight_entry.grid(row=2, column=1, sticky="w", pady=6, padx=(8, 4))

        weight_hint = tk.Label(card, text="e.g. 70.5", font=("Segoe UI", 8),
                               bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MUTED)
        weight_hint.grid(row=2, column=2, sticky="w", padx=4)

        height_lbl = tk.Label(card, text="Height (m):", font=("Segoe UI", 9, "bold"),
                              bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MAIN)
        height_lbl.grid(row=3, column=0, sticky="w", pady=6)

        self.height_var = tk.StringVar()
        self.height_entry = ttk.Entry(card, textvariable=self.height_var, font=("Segoe UI", 10), width=28)
        self.height_entry.grid(row=3, column=1, sticky="w", pady=6, padx=(8, 4))

        height_hint = tk.Label(card, text="e.g. 1.75 (meters)", font=("Segoe UI", 8),
                               bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MUTED)
        height_hint.grid(row=3, column=2, sticky="w", padx=4)

        btn_frame = tk.Frame(card, bg=self.COLOR_CARD)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky="we", pady=(14, 4))

        calc_btn = ttk.Button(btn_frame, text="💾 Calculate & Save Record",
                              style="Primary.TButton", command=self.handle_calculate_and_save)
        calc_btn.pack(side="left", padx=(0, 8))

        clear_btn = ttk.Button(btn_frame, text="Clear Inputs",
                               style="Secondary.TButton", command=self.handle_clear_inputs)
        clear_btn.pack(side="left")

    def _build_result_card(self):
        card_outer = tk.Frame(self, bg=self.COLOR_BORDER, padx=1, pady=1)
        card_outer.pack(fill="x", padx=20, pady=6)

        self.result_card = tk.Frame(card_outer, bg=self.COLOR_CARD, padx=18, pady=16)
        self.result_card.pack(fill="both", expand=True)

        res_title = tk.Label(self.result_card, text="📊 Health Assessment Result",
                             font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MAIN)
        res_title.pack(anchor="w", pady=(0, 8))

        self.res_display_frame = tk.Frame(self.result_card, bg="#F8FAFC", relief="solid", bd=1, padx=14, pady=14)
        self.res_display_frame.configure(highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        self.res_display_frame.pack(fill="x", pady=4)

        self.bmi_value_lbl = tk.Label(
            self.res_display_frame,
            text="--.--",
            font=("Segoe UI", 32, "bold"),
            bg="#F8FAFC",
            fg=self.COLOR_TEXT_MUTED
        )
        self.bmi_value_lbl.pack()

        self.category_badge = tk.Label(
            self.res_display_frame,
            text="Ready for Calculation",
            font=("Segoe UI", 11, "bold"),
            bg="#E2E8F0",
            fg=self.COLOR_TEXT_MUTED,
            padx=12,
            pady=4
        )
        self.category_badge.pack(pady=(4, 6))

        self.advice_lbl = tk.Label(
            self.res_display_frame,
            text="Enter user name, weight in kg, and height in meters, then click 'Calculate & Save Record'.",
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            fg=self.COLOR_TEXT_MUTED,
            wraplength=480,
            justify="center"
        )
        self.advice_lbl.pack(pady=(2, 4))

        self.saved_info_lbl = tk.Label(
            self.result_card,
            text="",
            font=("Segoe UI", 8, "italic"),
            bg=self.COLOR_CARD,
            fg="#16A34A"
        )
        self.saved_info_lbl.pack(anchor="w", pady=(6, 0))

    def _build_history_card(self):
        card_outer = tk.Frame(self, bg=self.COLOR_BORDER, padx=1, pady=1)
        card_outer.pack(fill="x", padx=20, pady=6)

        card = tk.Frame(card_outer, bg=self.COLOR_CARD, padx=18, pady=16)
        card.pack(fill="both", expand=True)

        hist_title = tk.Label(card, text="📈 Historical Trends & Data",
                              font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT_MAIN)
        hist_title.pack(anchor="w", pady=(0, 6))

        self.user_stats_lbl = tk.Label(
            card,
            text="Select a user or calculate a BMI to view historical statistics.",
            font=("Segoe UI", 9),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_MUTED,
            justify="left"
        )
        self.user_stats_lbl.pack(anchor="w", pady=(0, 10))

        btn_box = tk.Frame(card, bg=self.COLOR_CARD)
        btn_box.pack(fill="x")

        view_chart_btn = ttk.Button(
            btn_box,
            text="📈 View BMI Trend Graph",
            style="Primary.TButton",
            command=self.handle_view_graph
        )
        view_chart_btn.pack(side="left", padx=(0, 8))

        view_table_btn = ttk.Button(
            btn_box,
            text="📋 View Records Log",
            style="Secondary.TButton",
            command=self.handle_view_records_table
        )
        view_table_btn.pack(side="left")

    def _build_status_bar(self):
        status_frame = tk.Frame(self, bg="#E2E8F0", height=24)
        status_frame.pack(side="bottom", fill="x")

        self.status_lbl = tk.Label(
            status_frame,
            text="Database Connected | Ready",
            font=("Segoe UI", 8),
            bg="#E2E8F0",
            fg=self.COLOR_TEXT_MUTED,
            padx=8,
            pady=3
        )
        self.status_lbl.pack(side="left")

    def _refresh_user_list(self):
        try:
            users = database.get_all_users()
            self.user_combo["values"] = users
            current = self.user_var.get().strip()
            if not current and users:
                self.user_combo.current(0)
                self._update_user_stats(users[0])
            elif current:
                self._update_user_stats(current)
        except database.DatabaseError as e:
            self.status_lbl.config(text=f"Database Warning: {e}")

    def _on_user_selected(self, event=None):
        selected_user = self.user_var.get().strip()
        if selected_user:
            self._update_user_stats(selected_user)

    def _update_user_stats(self, user_name: str):
        try:
            stats = database.get_user_stats(user_name)
            count = stats["count"]
            if count == 0:
                self.user_stats_lbl.config(
                    text=f"User: '{user_name}' has 0 saved records. Enter data to start tracking."
                )
            else:
                self.user_stats_lbl.config(
                    text=f"User: '{user_name}'  |  Total Entries: {count}  |  "
                         f"Latest: {stats['latest_bmi']} ({stats['latest_category']})  |  "
                         f"Range: {stats['min_bmi']} - {stats['max_bmi']}"
                )
        except database.DatabaseError as e:
            self.user_stats_lbl.config(text=f"Could not load stats: {e}")

    def validate_inputs(self) -> Optional[Tuple[str, float, float]]:
        user_name = self.user_var.get().strip()
        weight_raw = self.weight_var.get().strip()
        height_raw = self.height_var.get().strip()

        if not user_name:
            messagebox.showerror(
                "Input Error - Missing User Name",
                "Please enter or select a User Name.\n\n"
                "Multi-user tracking requires a user name to save and view trends."
            )
            self.user_combo.focus_set()
            return None

        if not weight_raw:
            messagebox.showerror(
                "Input Error - Missing Weight",
                "Please enter the weight in kilograms (kg).\nExample: 68.5"
            )
            self.weight_entry.focus_set()
            return None

        try:
            weight = float(weight_raw)
        except ValueError:
            messagebox.showerror(
                "Input Error - Invalid Weight",
                f"Weight must be a valid number.\nReceived: '{weight_raw}'\n\n"
                "Please enter a numeric value (e.g., 72.0)."
            )
            self.weight_entry.focus_set()
            return None

        if weight <= 0:
            messagebox.showerror(
                "Input Error - Non-Positive Weight",
                "Weight must be greater than zero.\nZero and negative numbers are not valid."
            )
            self.weight_entry.focus_set()
            return None

        if not height_raw:
            messagebox.showerror(
                "Input Error - Missing Height",
                "Please enter the height in meters (m).\nExample: 1.75"
            )
            self.height_entry.focus_set()
            return None

        try:
            height = float(height_raw)
        except ValueError:
            messagebox.showerror(
                "Input Error - Invalid Height",
                f"Height must be a valid number.\nReceived: '{height_raw}'\n\n"
                "Please enter a numeric value in meters (e.g., 1.75)."
            )
            self.height_entry.focus_set()
            return None

        if height <= 0:
            messagebox.showerror(
                "Input Error - Non-Positive Height",
                "Height must be greater than zero.\nZero and negative numbers are not valid."
            )
            self.height_entry.focus_set()
            return None

        if height > 3.0:
            converted = height / 100.0
            confirmed = messagebox.askyesno(
                "Height Unit Confirmation",
                f"You entered a height of {height} meters.\n\n"
                f"Did you mean {converted:.2f} meters ({height:.0f} cm)?\n\n"
                "Click 'Yes' to automatically convert to meters, or 'No' to keep current value."
            )
            if confirmed:
                height = round(converted, 2)
                self.height_var.set(str(height))
            else:
                if height > 3.0:
                    messagebox.showerror(
                        "Input Error - Unrealistic Height",
                        "Height must be entered in meters (typically 0.5 m to 2.8 m)."
                    )
                    self.height_entry.focus_set()
                    return None

        return user_name, weight, height

    def handle_calculate_and_save(self):
        validated = self.validate_inputs()
        if not validated:
            return

        user_name, weight, height = validated

        bmi_value = calculate_bmi(weight, height)
        category_name, cat_meta = get_bmi_category(bmi_value)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            record_id = database.add_record(
                user_name=user_name,
                weight=weight,
                height=height,
                bmi=bmi_value,
                category=category_name,
                timestamp=timestamp
            )
        except database.DatabaseError as e:
            messagebox.showerror(
                "Database Save Failure",
                f"An error occurred while saving to the database:\n{e}\n\n"
                "The calculation is displayed, but was not persisted."
            )
            return

        self._render_result(bmi_value, category_name, cat_meta, user_name, timestamp)

        self._refresh_user_list()
        self.user_var.set(user_name)
        self._update_user_stats(user_name)
        self.status_lbl.config(
            text=f"Record #{record_id} saved for '{user_name}' at {timestamp}"
        )

    def _render_result(self, bmi: float, category: str, meta: Dict[str, Any], user: str, timestamp: str):
        hex_color = meta["color"]
        bg_pill = meta["bg_pill"]

        self.bmi_value_lbl.config(
            text=f"{bmi:.2f}",
            fg=hex_color
        )

        self.category_badge.config(
            text=f"Category: {category} ({meta['range_text']})",
            bg=bg_pill,
            fg=hex_color
        )

        self.advice_lbl.config(
            text=meta["advice"],
            fg=self.COLOR_TEXT_MAIN
        )

        self.saved_info_lbl.config(
            text=f"✓ Record successfully saved for '{user}' ({timestamp})",
            fg=hex_color
        )

    def handle_clear_inputs(self):
        self.weight_var.set("")
        self.height_var.set("")
        self.weight_entry.focus_set()

    def handle_view_graph(self):
        user_name = self.user_var.get().strip()
        if not user_name:
            messagebox.showwarning(
                "User Required",
                "Please enter or select a user name to view historical charts."
            )
            self.user_combo.focus_set()
            return

        try:
            records = database.get_user_records(user_name)
        except database.DatabaseError as e:
            messagebox.showerror(
                "Database Error",
                f"Failed to load records for user '{user_name}':\n{e}"
            )
            return

        if not records:
            messagebox.showinfo(
                "No Historical Records Found",
                f"No saved BMI records were found for '{user_name}'.\n\n"
                "Please calculate and save at least one record first."
            )
            return

        self._display_trend_window(user_name, records)

    def _display_trend_window(self, user_name: str, records: List[Dict[str, Any]]):
        chart_win = tk.Toplevel(self)
        chart_win.title(f"BMI Progress Chart - {user_name}")
        chart_win.geometry("820x620")
        chart_win.minsize(700, 500)
        chart_win.configure(bg=self.COLOR_BG)

        hdr = tk.Frame(chart_win, bg=self.COLOR_BG, padx=16, pady=12)
        hdr.pack(fill="x")

        latest = records[-1]
        summary_text = (
            f"User: {user_name}   |   Total Readings: {len(records)}   |   "
            f"Latest BMI: {latest['bmi']:.2f} ({latest['category']})   |   "
            f"Last Recorded: {latest['timestamp']}"
        )
        tk.Label(
            hdr,
            text=f"Historical BMI Trend: {user_name}",
            font=("Segoe UI", 14, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT_MAIN
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text=summary_text,
            font=("Segoe UI", 9),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT_MUTED
        ).pack(anchor="w")

        dates = []
        date_labels = []
        bmis = []
        weights = []

        for r in records:
            ts_str = r["timestamp"]
            bmis.append(r["bmi"])
            weights.append(r["weight"])
            try:
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                dates.append(dt)
                date_labels.append(dt.strftime("%b %d\n%H:%M"))
            except ValueError:
                dates.append(ts_str)
                date_labels.append(ts_str)

        fig = Figure(figsize=(8, 4.8), dpi=100)
        fig.patch.set_facecolor("#FFFFFF")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#FAFAFA")

        min_bmi = min(bmis)
        max_bmi = max(bmis)
        y_bottom = max(12.0, min(15.0, min_bmi - 2.0))
        y_top = max(35.0, max_bmi + 4.0)

        ax.axhspan(0, 18.5, color="#BAE6FD", alpha=0.35, label="Underweight (< 18.5)")
        ax.axhspan(18.5, 25.0, color="#BBF7D0", alpha=0.45, label="Normal (18.5 - 24.9)")
        ax.axhspan(25.0, 30.0, color="#FED7AA", alpha=0.35, label="Overweight (25.0 - 29.9)")
        ax.axhspan(30.0, y_top + 10, color="#FECACA", alpha=0.35, label="Obese (>= 30.0)")

        x_indices = list(range(len(records)))

        if len(records) == 1:
            ax.plot(x_indices, bmis, marker="o", markersize=10, color="#1D4ED8",
                    linewidth=2.5, zorder=5)
            ax.text(
                0, bmis[0] + 0.6,
                f"Initial Record: {bmis[0]:.2f}\n({records[0]['category']})",
                ha="center", va="bottom", fontsize=10, weight="bold", color="#1E293B",
                bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFFF", ec="#1D4ED8", alpha=0.9)
            )
        else:
            ax.plot(x_indices, bmis, marker="o", markersize=7, color="#1D4ED8",
                    linewidth=2.5, label="User BMI Trend", zorder=5)

            for i, val in enumerate(bmis):
                ax.annotate(
                    f"{val:.2f}",
                    (x_indices[i], val),
                    textcoords="offset points",
                    xytext=(0, 9),
                    ha="center",
                    fontsize=8.5,
                    fontweight="bold",
                    color="#1E293B"
                )

        ax.set_xticks(x_indices)
        ax.set_xticklabels(date_labels, fontsize=8.5)
        ax.set_ylim(y_bottom, y_top)
        ax.set_ylabel("Body Mass Index (BMI)", fontsize=10, fontweight="bold", color="#334155")
        ax.set_xlabel("Measurement Date & Time", fontsize=10, fontweight="bold", color="#334155")
        ax.grid(True, linestyle="--", alpha=0.5, color="#CBD5E1")

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc="upper right", framealpha=0.92, fontsize=8.5)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 6))

        toolbar_frame = tk.Frame(chart_win, bg=self.COLOR_BG)
        toolbar_frame.pack(fill="x", padx=12, pady=(0, 8))
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

    def handle_view_records_table(self):
        user_name = self.user_var.get().strip()

        try:
            if user_name:
                records = database.get_user_records(user_name)
                title_suffix = f"for '{user_name}'"
            else:
                records = database.get_all_records()
                title_suffix = "for All Users"
        except database.DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to retrieve records:\n{e}")
            return

        table_win = tk.Toplevel(self)
        table_win.title(f"BMI History Log {title_suffix}")
        table_win.geometry("740x500")
        table_win.minsize(620, 380)
        table_win.configure(bg=self.COLOR_BG)

        top_frame = tk.Frame(table_win, bg=self.COLOR_BG, padx=16, pady=12)
        top_frame.pack(fill="x")

        tk.Label(
            top_frame,
            text=f"📋 BMI Historical Records {title_suffix}",
            font=("Segoe UI", 12, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT_MAIN
        ).pack(side="left")

        tree_frame = tk.Frame(table_win, bg=self.COLOR_CARD, padx=12, pady=8)
        tree_frame.pack(fill="both", expand=True)

        columns = ("id", "user_name", "timestamp", "weight", "height", "bmi", "category")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        tree.heading("id", text="ID")
        tree.heading("user_name", text="User")
        tree.heading("timestamp", text="Date & Time")
        tree.heading("weight", text="Weight (kg)")
        tree.heading("height", text="Height (m)")
        tree.heading("bmi", text="BMI")
        tree.heading("category", text="Category")

        tree.column("id", width=40, anchor="center")
        tree.column("user_name", width=110, anchor="w")
        tree.column("timestamp", width=140, anchor="center")
        tree.column("weight", width=80, anchor="center")
        tree.column("height", width=80, anchor="center")
        tree.column("bmi", width=70, anchor="center")
        tree.column("category", width=110, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        for r in records:
            tree.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["user_name"],
                    r["timestamp"],
                    f"{r['weight']:.2f}",
                    f"{r['height']:.2f}",
                    f"{r['bmi']:.2f}",
                    r["category"]
                )
            )

        actions_bar = tk.Frame(table_win, bg=self.COLOR_BG, padx=16, pady=10)
        actions_bar.pack(fill="x")

        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Selection Required", "Please select a record from the table to delete.")
                return
            item_data = tree.item(selected[0])["values"]
            record_id = item_data[0]
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete Record #{record_id} for user '{item_data[1]}'?"
            )
            if confirm:
                try:
                    success = database.delete_record(record_id)
                    if success:
                        tree.delete(selected[0])
                        self._refresh_user_list()
                        messagebox.showinfo("Success", f"Record #{record_id} successfully deleted.")
                    else:
                        messagebox.showwarning("Not Found", f"Record #{record_id} could not be found.")
                except database.DatabaseError as err:
                    messagebox.showerror("Database Deletion Error", f"Failed to delete record:\n{err}")

        def export_csv():
            if not records:
                messagebox.showinfo("Export Empty", "There are no records to export.")
                return
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="Save BMI Records as CSV"
            )
            if not file_path:
                return
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "User Name", "Date/Time", "Weight (kg)", "Height (m)", "BMI", "Category"])
                    for row_id in tree.get_children():
                        writer.writerow(tree.item(row_id)["values"])
                messagebox.showinfo("Export Complete", f"Successfully exported records to:\n{file_path}")
            except Exception as exp:
                messagebox.showerror("Export Failed", f"Failed to export CSV:\n{exp}")

        del_btn = ttk.Button(actions_bar, text="🗑️ Delete Selected Record",
                             style="Secondary.TButton", command=delete_selected)
        del_btn.pack(side="left", padx=(0, 8))

        export_btn = ttk.Button(actions_bar, text="📥 Export to CSV",
                                style="Secondary.TButton", command=export_csv)
        export_btn.pack(side="left")

        close_btn = ttk.Button(actions_bar, text="Close",
                               style="Secondary.TButton", command=table_win.destroy)
        close_btn.pack(side="right")


def main():
    app = BMICalculatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
