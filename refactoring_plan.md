# Project Refactoring Plan: Folderization and Import Updates

This document outlines the detailed plan for refactoring the `HomeUnitCalculator` project by organizing existing Python files into a more structured folder system and updating all necessary import statements.

## Proposed Folder Structure

```
d:/hmc/HomeUnitCalculator/
├── src/
│   ├── main.py                     # Renamed HomeUnitCalculator.py to main.py (main application entry)
│   ├── ui/
│   │   ├── tabs/
│   │   │   ├── main_tab.py
│   │   │   ├── rooms_tab.py
│   │   │   ├── history_tab.py
│   │   │   ├── supabase_config_tab.py
│   │   │   ├── rental_info_tab.py
│   │   │   └── archived_info_tab.py
│   │   ├── widgets/
│   │   │   ├── custom_widgets.py
│   │   │   └── dialogs.py
│   │   └── styles.py
│   ├── core/
│   │   ├── db_manager.py
│   │   ├── encryption_utils.py
│   │   └── key_manager.py
│   └── utils/
│       └── utils.py
├── icons/
│   └── ... (existing icon files)
├── app_config.db                   # Database file (remains at root or could be moved to a 'data' folder)
├── requirements.txt
├── README.md
├── .gitignore
└── ... (other non-code files like PDFs, CSVs, markdown plans)
```

## Reasoning for the Proposed Structure

*   **`src/`**: A common practice to put all source code under a `src` directory, clearly separating it from configuration, documentation, or data files.
*   **`src/main.py`**: Renaming `HomeUnitCalculator.py` to `main.py` makes it clearer that this is the primary entry point of the application.
*   **`src/ui/`**: Groups all UI-related components.
    *   **`src/ui/tabs/`**: Contains all the individual tab implementations, as they are distinct UI sections. This improves modularity and makes it easier to locate specific tab logic.
    *   **`src/ui/widgets/`**: Contains reusable UI components like `custom_widgets.py` and `dialogs.py`. `dialogs.py` is a collection of UI dialogs, so it fits well here, promoting reusability and separation of concerns.
    *   **`src/ui/styles.py`**: `styles.py` is purely UI-related, centralizing all styling definitions, so it belongs directly under `ui`.
*   **`src/core/`**: Groups core functionalities that are fundamental to the application's operation and might be used across different UI components or backend processes.
    *   `db_manager.py`, `encryption_utils.py`, and `key_manager.py` are tightly coupled (database interactions, encryption logic, and key management) and form the "backend" or "data layer" of the application. Grouping them enhances clarity and maintainability.
*   **`src/utils/`**: For general utility functions that don't fit into `ui` or `core`. `utils.py` with `resource_path` and `_clear_layout` fits here, providing a common place for shared helper functions.
*   **`icons/`**: Remains at the root as it's a resource directory, not source code.
*   **`app_config.db`**: Remains at the root for now, as it's a data file. Could be moved to a `data/` folder if the project grows and more data files are introduced.

## Detailed Plan for Code Modifications

The primary change will be updating `import` statements in all Python files to reflect the new folder structure.

1.  **Rename `HomeUnitCalculator.py` to `src/main.py`**.
2.  **Create new directories**: `src`, `src/ui`, `src/ui/tabs`, `src/ui/widgets`, `src/core`, `src/utils`.
3.  **Move files to their respective new locations**:
    *   `HomeUnitCalculator.py` -> `src/main.py`
    *   `main_tab.py` -> `src/ui/tabs/main_tab.py`
    *   `rooms_tab.py` -> `src/ui/tabs/rooms_tab.py`
    *   `history_tab.py` -> `src/ui/tabs/history_tab.py`
    *   `supabase_config_tab.py` -> `src/ui/tabs/supabase_config_tab.py`
    *   `rental_info_tab.py` -> `src/ui/tabs/rental_info_tab.py`
    *   `archived_info_tab.py` -> `src/ui/tabs/archived_info_tab.py`
    *   `custom_widgets.py` -> `src/ui/widgets/custom_widgets.py`
    *   `dialogs.py` -> `src/ui/widgets/dialogs.py`
    *   `styles.py` -> `src/ui/styles.py`
    *   `db_manager.py` -> `src/core/db_manager.py`
    *   `encryption_utils.py` -> `src/core/encryption_utils.py`
    *   `key_manager.py` -> `src/core/key_manager.py`
    *   `utils.py` -> `src/utils/utils.py`

4.  **Update `import` statements in all Python files**:

    *   **`src/main.py` (formerly `HomeUnitCalculator.py`)**:
        *   `from db_manager import DBManager` -> `from core.db_manager import DBManager`
        *   `from encryption_utils import EncryptionUtil` -> `from core.encryption_utils import EncryptionUtil`
        *   `from key_manager import get_or_create_key` -> `from core.key_manager import get_or_create_key`
        *   `from styles import ...` -> `from ui.styles import ...`
        *   `from utils import resource_path` -> `from utils.utils import resource_path`
        *   `from custom_widgets import ...` -> `from ui.widgets.custom_widgets import ...`
        *   `from main_tab import MainTab` -> `from ui.tabs.main_tab import MainTab`
        *   `from rooms_tab import RoomsTab` -> `from ui.tabs.rooms_tab import RoomsTab`
        *   `from history_tab import HistoryTab, EditRecordDialog` -> `from ui.tabs.history_tab import HistoryTab` (Note: `EditRecordDialog` is now in `dialogs.py` and imported by `history_tab.py` itself, so `main.py` doesn't need to import it directly)
        *   `from supabase_config_tab import SupabaseConfigTab` -> `from ui.tabs.supabase_config_tab import SupabaseConfigTab`
        *   `from rental_info_tab import RentalInfoTab` -> `from ui.tabs.rental_info_tab import RentalInfoTab`
        *   `from archived_info_tab import ArchivedInfoTab` -> `from ui.tabs.archived_info_tab import ArchivedInfoTab`

    *   **Files in `src/ui/tabs/` (e.g., `main_tab.py`, `rooms_tab.py`, `history_tab.py`, `supabase_config_tab.py`, `rental_info_tab.py`, `archived_info_tab.py`)**:
        *   `from styles import ...` -> `from ..styles import ...` (relative import)
        *   `from utils import resource_path, _clear_layout` -> `from ...utils.utils import resource_path, _clear_layout` (relative import)
        *   `from custom_widgets import ...` -> `from ..widgets.custom_widgets import ...` (relative import)
        *   `from db_manager import DBManager` (if any tab directly imports it) -> `from ...core.db_manager import DBManager`
        *   `from dialogs import RentalRecordDialog` (in `rental_info_tab.py`, `archived_info_tab.py`) -> `from ..widgets.dialogs import RentalRecordDialog`
        *   **Correction for `history_tab.py`**:
            *   The `EditRecordDialog` class definition itself needs to be moved from `history_tab.py` to `src/ui/widgets/dialogs.py`.
            *   Then, in `history_tab.py`, change `from history_tab import HistoryTab, EditRecordDialog` to `from ..widgets.dialogs import EditRecordDialog`.

    *   **Files in `src/ui/widgets/` (e.g., `custom_widgets.py`, `dialogs.py`)**:
        *   `from styles import ...` -> `from ..styles import ...` (relative import)
        *   `from utils import resource_path` -> `from ...utils.utils import resource_path` (relative import)
        *   `from db_manager import DBManager` (in `dialogs.py` if it uses it directly) -> `from ...core.db_manager import DBManager`
        *   `from utils import _is_safe_path` (in `dialogs.py` if `RentalRecordDialog` uses it) -> `from ...utils.utils import _is_safe_path`
        *   `from rental_info_tab import RentalInfoTab` (in `dialogs.py` if `RentalRecordDialog` calls `generate_rental_pdf_from_data` on it) -> `from ..tabs.rental_info_tab import RentalInfoTab`

    *   **Files in `src/core/` (e.g., `db_manager.py`, `encryption_utils.py`, `key_manager.py`)**:
        *   `from encryption_utils import EncryptionUtil` (in `db_manager.py`) -> `from .encryption_utils import EncryptionUtil` (relative import)
        *   `from key_manager import get_or_create_key` (in `encryption_utils.py`) -> `from .key_manager import get_or_create_key` (relative import)

    *   **Files in `src/utils/` (e.g., `utils.py`)**:
        *   No internal imports to change.

## Module Dependencies (High-Level)

```mermaid
graph TD
    A[src/main.py] --> B[src/ui/tabs/]
    A --> C[src/core/]
    A --> D[src/ui/widgets/]
    A --> E[src/ui/styles.py]
    A --> F[src/utils/utils.py]

    B --> D
    B --> E
    B --> F
    B --> C

    D --> E
    D --> F

    C --> C_sub[src/core/encryption_utils.py]
    C_sub --> C_sub_sub[src/core/key_manager.py]