# Home Unit Calculation Application

This is a desktop application built with PyQt5 for calculating and managing home unit consumption and costs. It allows users to input meter readings, calculate differences, add additional costs, calculate room-specific consumption, save records locally (CSV) or to a Supabase database, generate PDF reports, and view historical data.

## Features

- **Main Calculation Tab:**
  - Input current meter readings (Meter 1, Meter 2, Meter 3).
  - Automatically calculates the difference from previous readings.
  - Input additional amounts (e.g., service charges).
  - Displays calculated total units and per-unit cost.
- **Room Calculation Tab:**
  - Dynamically generated input fields for each room based on configuration (requires setup or data loading).
  - Input present and previous meter readings for each room.
  - Calculates individual room consumption and cost.
- **History Tab:**
  - View historical calculation records.
  - Filter history by month and year.
  - Load previous records into the main calculation fields.
  - Edit and delete historical records (requires Supabase integration).
- **Data Persistence:**
  - Save calculation records to a local CSV file (`meter_calculation_history.csv`).
  - Save calculation records to a Supabase database (requires configuration).
  - Load historical data from CSV or Supabase.
- **PDF Report Generation:**
  - Generate a detailed PDF report of the current calculation.
- **Custom UI and Navigation:**
  - Custom styled widgets using CSS-like stylesheets.
  - Custom navigation between input fields using arrow keys and Enter/Return.
  - Auto-scrolling in areas with many inputs.
  - Basic accessibility features.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd HomeUnitCalculator
    ```

2.  **Install dependencies:**
    Make sure you have Python installed. Then install the required packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Supabase Configuration (Optional):**
    If you plan to use the Supabase integration for cloud saving and loading, create a `.env` file in the project root directory with your Supabase project URL and Anon key:
    ```env
    SUPABASE_URL="YOUR_SUPABASE_URL"
    SUPABASE_KEY="YOUR_SUPABASE_ANON_KEY"
    ```
    Replace `"YOUR_SUPABASE_URL"` and `"YOUR_SUPABASE_ANON_KEY"` with your actual Supabase project details.

## Usage

To run the application, execute the main Python script:

```bash
python HomeUnitCalculator.py
```

The application window will open, allowing you to input data, perform calculations, and manage records.

## Project Structure

-   `HomeUnitCalculator.py`: The main application script containing the PyQt5 GUI logic and calculation functions.
-   `styles.py`: Contains functions that return CSS-like strings for styling the application's widgets.
-   `utils.py`: Contains utility functions, such as `resource_path` for handling file paths in a way that works with PyInstaller.
-   `requirements.txt`: Lists the Python dependencies required to run the application.
-   `meter_calculation_history.csv`: (Created on first save) Stores calculation history in CSV format.
-   `icons/`: Directory containing icons used in the application.
-   `README.md`: This file.

## Dependencies

The project relies on the following Python libraries, listed in `requirements.txt`:

-   `PyQt5`: For creating the graphical user interface.
-   `reportlab`: For generating PDF reports.
-   `supabase`: The Supabase Python client library for database interaction.
-   `python-dotenv`: For loading environment variables from a `.env` file.
-   `postgrest`: A dependency for the Supabase client.

## Styling

The application's look and feel are controlled by the styles defined in [`styles.py`](styles.py). This file provides various CSS-like stylesheets for different PyQt5 widgets, ensuring a consistent and visually appealing interface.

## Utility Functions

The [`utils.py`](utils.py) file contains helper functions. Currently, it includes the `resource_path` function, which is essential for correctly locating application resources (like icons) whether the application is run directly as a script or as a bundled executable created by tools like PyInstaller.

## Supabase Integration

The application includes functionality to save and load calculation records from a Supabase database. This feature requires a Supabase project and the correct configuration in a `.env` file. The relevant logic is handled within the `HomeUnitCalculator.py` file, utilizing the `supabase` and `postgrest` libraries.

## PDF Generation

Users can generate a PDF report of the current calculation using the "Save as PDF" button. The PDF generation logic is implemented using the `reportlab` library, formatting the calculation details into a printable document.

## CSV Handling

Calculation history can be saved to and loaded from a local CSV file (`meter_calculation_history.csv`). This provides a simple way to persist data without requiring a database setup. The `csv` module is used for reading and writing this file.

## Navigation and Accessibility

Custom navigation is implemented for input fields using the `CustomLineEdit` and `CustomNavButton` classes, allowing users to navigate using arrow keys and the Enter/Return key. The `AutoScrollArea` class provides automatic scrolling when the mouse is near the edges. Basic accessibility features are also included to improve usability.

## Error Handling

Basic error handling is included using `try...except` blocks, particularly for file operations and database interactions. The `traceback` module is used to log detailed error information when exceptions occur.

---

Feel free to contribute to the project or report any issues!