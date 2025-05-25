# Detailed Plan: Adding "Rental Info" Tab

**Goal:** Integrate a new "Rental Info" tab into the Home Unit Calculator application to manage tenant details and image uploads, with image-to-PDF conversion, using **offline storage for images**, and including **tenant details as text in the generated PDF**.

## Phase 1: Core Tab Integration and UI Design

1.  **Create `rental_info_tab.py`:**
    *   Define a new class `RentalInfoTab` inheriting from `QWidget`.
    *   Initialize the tab with references to `main_window_ref` (the `MeterCalculationApp` instance) for potential cross-tab communication and access to shared resources like `db_manager`.
    *   Implement `init_ui` method to set up the basic layout for the tab.
    *   Include input fields for:
        *   Tenant Name (`QLineEdit`)
        *   Room Number (`QLineEdit` - free-form text)
        *   Advanced Paid (`QLineEdit`)
    *   Add `QPushButton` widgets for image uploads:
        *   "Upload Photo"
        *   "Upload NID Front"
        *   "Upload NID Back"
        *   "Upload Police Form"
    *   Add a `QPushButton` for "Convert Images to PDF".
    *   Include `QLabel` widgets to display the paths of uploaded images (e.g., "Photo: C:/path/to/image.jpg").
    *   Consider using `QFormLayout` or `QGridLayout` for organizing the input fields and buttons.
    *   Add a `QTableWidget` to display a list of rented rooms with tenant details (Name, Room, Advanced Paid). This will be populated from a local database (e.g., using `db_manager`).

2.  **Integrate `RentalInfoTab` into `HomeUnitCalculator.py`:**
    *   Import `RentalInfoTab` at the top of the file.
    *   Create an instance of `RentalInfoTab` in the `MeterCalculationApp.__init__` method, similar to other tabs:
        ```python
        self.rental_info_tab_instance = RentalInfoTab(self)
        ```
    *   Add the new tab to the `QTabWidget` in `init_ui`:
        ```python
        self.tab_widget.addTab(self.rental_info_tab_instance, "Rental Info")
        ```
    *   Ensure `setup_navigation` and `set_focus_on_tab_change` correctly handle the new tab.

## Phase 2: Data Management and Image Handling (Offline)

1.  **Local Database Schema Design (via `db_manager.py`):**
    *   Define a new table in the local SQLite database (e.g., `rentals`) to store rental information.
    *   Columns:
        *   `id` (Primary Key, INTEGER AUTOINCREMENT)
        *   `tenant_name` (TEXT)
        *   `room_number` (TEXT)
        *   `advanced_paid` (REAL)
        *   `photo_path` (TEXT, local file path)
        *   `nid_front_path` (TEXT, local file path)
        *   `nid_back_path` (TEXT, local file path)
        *   `police_form_path` (TEXT, local file path)
        *   `created_at` (TEXT, ISO format)
        *   `updated_at` (TEXT, ISO format)
    *   Update `db_manager.py` to create this table if it doesn't exist and provide methods for inserting, retrieving, updating, and deleting rental records.

2.  **Local Image Path Storage:**
    *   Implement methods in `RentalInfoTab` to handle image selection using `QFileDialog`.
    *   Instead of uploading, store the *local file paths* of the selected images in the `rentals` table.
    *   The `QLabel` widgets will display these local paths.

3.  **Image to PDF Conversion:**
    *   Implement a method in `RentalInfoTab` (e.g., `convert_images_to_pdf`).
    *   This method will retrieve the local image paths and tenant details from the stored rental record.
    *   Use `reportlab` (already imported in `HomeUnitCalculator.py`) to create a single PDF document.
    *   The PDF will include the tenant's name, room number, and advanced paid details as text, followed by each image as an `Image` element.
    *   The generated PDF will be saved locally using `QFileDialog.getSaveFileName`.

## Phase 3: Functionality and Enhancements

1.  **Add/Edit/Delete Rental Records:**
    *   Implement methods to save new rental records to the local `rentals` table via `db_manager`.
    *   Implement functionality to load existing rental records from the local database into the `QTableWidget`.
    *   Add context menu or buttons for editing and deleting records from the table and the local database.

2.  **Input Validation:**
    *   Add validators for `QLineEdit` fields (e.g., numeric for `Advanced Paid`).

3.  **Error Handling and User Feedback:**
    *   Use `QMessageBox` for success/error messages during database operations and file selections.
    *   Provide visual feedback (e.g., changing button states, status labels) during long-running operations.

4.  **Refactoring (Optional but Recommended):**
    *   If the `_clear_layout` function is still copied, move it to `utils.py` to avoid duplication.

## Mermaid Diagram: Application Flow with New Tab (Offline Storage & Detailed PDF)

```mermaid
graph TD
    A[MeterCalculationApp] --> B(init_ui)
    B --> C{QTabWidget}
    C --> D[Main Calculation Tab]
    C --> E[Room Calculations Tab]
    C --> F[Calculation History Tab]
    C --> G[Supabase Config Tab]
    C --> H[Rental Info Tab]

    H --> H1[init_ui (RentalInfoTab)]
    H1 --> H2[Tenant Name Input]
    H1 --> H3[Room Number Input]
    H1 --> H4[Advanced Paid Input]
    H1 --> H5[Upload Photo Button]
    H1 --> H6[Upload NID Front Button]
    H1 --> H7[Upload NID Back Button]
    H1 --> H8[Upload Police Form Button]
    H1 --> H9[Convert Images to PDF Button]
    H1 --> H10[Rental Records Table]

    H5 --> I[QFileDialog (Select Image)]
    H6 --> I
    H7 --> I
    H8 --> I
    I --> J[Store Local Path in RentalInfoTab]
    J --> K[Save Record to Local DB (rentals table via db_manager)]

    H9 --> L[Retrieve Local Image Paths & Tenant Details from RentalInfoTab/DB]
    L --> M[reportlab (Generate PDF with Text & Images)]
    M --> N[QFileDialog (Save PDF)]

    H10 --> O[Load Data from Local DB (db_manager)]
    O --> P[Display Data in Table]
    P --> Q[Edit/Delete Record Functionality]