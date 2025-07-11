# Home Unit Calculation Application

This is a desktop application built with **PyQt5** for **Windows** designed to simplify the calculation and management of household utility consumption and associated costs. It provides a comprehensive solution for tracking meter readings, calculating differences, managing additional expenses, and generating detailed reports for individual rooms and overall property.

## ✨ Features

-   **Intuitive Main Calculation Interface:**
    -   Input current meter readings.
    -   Automatically calculates unit differences.
    -   Include additional charges (e.g., service fees).
    -   Displays total consumed units and per-unit cost.
-   **Flexible Room-Specific Calculations:**
    -   Dynamically generated input fields for each room.
    -   Input present and previous meter readings for individual rooms.
    -   Calculates specific consumption and costs for each room, including gas, water, and house rent.
-   **Comprehensive History Management:**
    -   View and filter past calculation records.
    -   Load previous records to pre-fill current calculation fields.
    -   Edit and delete historical entries (requires Supabase integration).
-   **Robust Data Persistence Options:**
    -   Save calculation records to a local CSV file (`meter_calculation_history.csv`).
    -   Securely save and load data from a **Supabase** database for cloud synchronization.
-   **Professional PDF Report Generation:**
    -   Generate detailed, printable PDF reports of current and historical calculations.
-   **Enhanced User Experience:**
    -   Modern, custom-styled interface.
    -   Efficient keyboard navigation for rapid data entry.
    -   Auto-scrolling in input-heavy sections.
    -   Non-blocking information, warning, and critical messages.

## 🚀 Installation

To get started with the Home Unit Calculation Application, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/HomeUnitCalculator.git
    cd HomeUnitCalculator
    ```
    *(Replace `https://github.com/your-username/HomeUnitCalculator.git` with the actual repository URL)*

2.  **Install dependencies:**
    Ensure you have Python (3.8+) installed. Then, install the required packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Supabase Configuration (Optional):**
    If you wish to utilize the cloud saving and loading features with Supabase, you will configure your Supabase project URL and Anon key directly within the application's "Supabase Config" tab. These credentials are securely stored in a local encrypted database.

## 💡 Usage

To launch the application, navigate to the project's root directory in your terminal and execute the main Python script:

```bash
python src/core/HomeUnitCalculator.py
```

The application window will appear, ready for you to input data, perform calculations, and manage your home unit records.


## 🛠️ Dependencies

The project relies on standard Python libraries for GUI, reporting, and database interaction:

-   `PyQt5`: Graphical user interface framework.
-   `reportlab`: PDF report generation.
-   `supabase`: Supabase Python client.
-   `postgrest`: Supabase client dependency.
-   `PyQt-Fluent-Widgets`: Modern UI components.
-   `cryptography`: For encryption of sensitive data.
-   `keyring`: For secure storage of encryption keys.

