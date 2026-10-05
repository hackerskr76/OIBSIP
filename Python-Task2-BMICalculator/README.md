# ⚖️ BMI Health Tracker & Calculator

A desktop application for calculating Body Mass Index (BMI), tracking historical health trends across multiple user profiles, and visualizing long-term progress with embedded data charts.

Built with **Python**, **Tkinter**, **SQLite3**, and **Matplotlib**.

---

## 🌟 Key Features

### 1. Core Logic & Health Assessment (Baseline Spec)
- **Standard BMI Calculation**: Evaluates BMI using the standard formula:
  $$\text{BMI} = \frac{\text{Weight (kg)}}{\left(\text{Height (m)}\right)^2}$$
- **Exact Precision**: Automatically rounds and formats all BMI values to **2 decimal places** (e.g., `22.86`).
- **Standard WHO Categorization**:
  - **Underweight**: $\text{BMI} < 18.5$
  - **Normal**: $18.5 \le \text{BMI} \le 24.9$ (or $< 25.0$)
  - **Overweight**: $25.0 \le \text{BMI} \le 29.9$ (or $< 30.0$)
  - **Obese**: $\text{BMI} \ge 30.0$
- **Robust Input Validation**:
  - Verifies non-empty user profiles.
  - Rejects non-numeric, zero, and negative values with helpful GUI pop-ups (`MessageBox`).
  - Unit guidance and auto-correction prompt if height is accidentally entered in centimeters instead of meters (e.g., entering `175` instead of `1.75`).

### 2. Desktop GUI & Multi-User Architecture (Advanced Spec)
- **Modern Tkinter Interface**: Desktop interface with high-DPI awareness, card layouts, clean typography, and keyboard shortcuts (`Enter` to calculate).
- **Dynamic Color-Coded Feedback**:
  - 🔵 **Underweight**: Blue accent (`#0284C7`)
  - 🟢 **Normal Weight**: Green accent (`#16A34A`)
  - 🟠 **Overweight**: Amber/Orange accent (`#D97706`)
  - 🔴 **Obese**: Crimson Red accent (`#DC2626`)
- **Multi-User Profile Support**: Save and switch between different family members or clients seamlessly using the dropdown combobox or typing a new name.
- **Embedded SQLite Database (`sqlite3`)**:
  - All records automatically persisted to a local `bmi_records.db` database.
  - Tables and indices created automatically on initial run.
  - Every CRUD operation is protected by `try/except` handlers for database reliability.
- **Interactive Trend Visualization (`matplotlib`)**:
  - Click **"View BMI Trend Graph"** to render a high-resolution trend chart of the user's BMI trajectory over time.
  - Features color-coded horizontal health zones (Underweight, Normal, Overweight, Obese).
  - Annotates exact BMI values and timestamps at each recorded data point.
  - Integrated Matplotlib navigation toolbar to zoom, pan, and save charts as high-resolution PNG or PDF files.
- **Data Management Table**:
  - View full history in a structured table (`Treeview`).
  - Delete mistaken entries or export historical records to **CSV**.

---

## 📁 Project Structure

```text
BMI_Calculator/
│
├── main.py              # Primary application file (Tkinter GUI, logic, Matplotlib integration)
├── database.py          # SQLite database helper module (CRUD queries, table setup, error handling)
├── test_bmi.py          # Comprehensive automated unit tests for math, categories, & DB
├── requirements.txt     # Python dependencies (matplotlib)
├── README.md            # Documentation, setup guide, and usage instructions
└── bmi_records.db       # Local SQLite database (auto-generated on first run)
```

---

## 🛠️ Prerequisites & Installation

### 1. Prerequisites
- **Python 3.8+** installed on your system.
- Standard libraries: `tkinter` and `sqlite3` (bundled with official Python installations on Windows and macOS).

> **Note for Linux users:** If Tkinter is not bundled with your Python installation, install it using:
> ```bash
> sudo apt-get install python3-tk
> ```

### 2. Clone or Navigate to the Project Directory
```bash
cd f:\OASIS\BMI_Calculator
```

### 3. Create a Virtual Environment (Optional but Recommended)
```bash
# On Windows:
python -m venv venv
venv\Scripts\activate

# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
Install Matplotlib using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run the Application

Launch the desktop application by executing:
```bash
python main.py
```

---

## 📖 How to Use the Application

1. **Select or Enter a User Name**:
   - Type a new name into the **User / Name** field or choose an existing user from the dropdown list.
2. **Enter Metrics**:
   - **Weight (kg)**: Enter your weight in kilograms (e.g., `70.5`).
   - **Height (m)**: Enter your height in meters (e.g., `1.75`).
3. **Calculate & Save**:
   - Click the **"💾 Calculate & Save Record"** button (or press `Enter` on your keyboard).
   - Your BMI is computed, rounded to 2 decimal places, and categorized.
   - The result card updates with color-coded feedback and tailored health guidance.
   - The record is saved into the local SQLite database.
4. **View Trends & Charts**:
   - Click **"📈 View BMI Trend Graph"** to inspect a visual line chart of your BMI progression over time with health category reference bands.
   - Use the Matplotlib toolbar to zoom in, pan, or save the chart image.
5. **View Records Log & CSV Export**:
   - Click **"📋 View Records Log"** to inspect all saved records in a tabular format.
   - Select any entry to delete it, or click **"📥 Export to CSV"** to generate a spreadsheet backup.

---

## 🗄️ Database Schema

The application uses an SQLite database (`bmi_records.db`) with the following table definition:

```sql
CREATE TABLE IF NOT EXISTS bmi_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    weight REAL NOT NULL,
    height REAL NOT NULL,
    bmi REAL NOT NULL,
    category TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

-- Fast lookup indices:
CREATE INDEX IF NOT EXISTS idx_bmi_user_name ON bmi_records(user_name);
CREATE INDEX IF NOT EXISTS idx_bmi_timestamp ON bmi_records(timestamp);
```

---

## 🧪 Running Automated Tests

Run the test suite to verify calculation accuracy, category classifications, edge cases, and SQLite database CRUD operations:

```bash
python -m unittest test_bmi.py
```

All tests execute in an isolated environment and verify:
- Accurate BMI calculation matching $weight / height^2$.
- WHO category thresholds and edge cases.
- Rejection of non-positive metrics and invalid user names.
- Database persistence, multi-user retrieval, and deletion.

---

## 📜 License

This project is licensed under the MIT License. Feel free to customize and extend for personal or clinical tracking!
