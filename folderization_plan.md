# Project Folderization Plan

This document outlines the plan to refactor the `HomeUnitCalculator` project by organizing existing files into a more structured folder system. The primary goal is to improve code organization and maintainability by grouping related files.

## 1. Proposed Folder Structure:

The following folder structure is proposed:

```
d:/hmc/HomeUnitCalculator/
├── src/
│   ├── core/
│   │   ├── HomeUnitCalculator.py
│   │   ├── db_manager.py
│   │   ├── encryption_utils.py
│   │   ├── key_manager.py
│   │   └── utils.py
│   ├── ui/
│   │   ├── custom_widgets.py
│   │   ├── dialogs.py
│   │   ├── styles.py
│   │   └── tabs/
│   │       ├── main_tab.py
│   │       ├── rooms_tab.py
│   │       ├── history_tab.py
│   │       ├── supabase_config_tab.py
│   │       ├── rental_info_tab.py
│   │       └── archived_info_tab.py
├── icons/
│   ├── calculate_icon.png
│   ├── database_icon.png
│   ├── down_arrow.png
│   ├── icon.png
│   ├── save_icon.png
│   └── up_arrow.png
├── .gitignore
├── README.md
└── requirements.txt
```

### Explanation of Folder Choices:

*   **`src/`**: This will be the main source code directory.
*   **`src/core/`**: This folder will contain core application logic, data management, encryption, and utility functions that are fundamental to the application's operation and are likely to be imported across various parts of the application.
    *   `HomeUnitCalculator.py`: The main application entry point.
    *   `db_manager.py`: Handles database interactions.
    *   `encryption_utils.py`: Provides encryption functionalities.
    *   `key_manager.py`: Manages encryption keys.
    *   `utils.py`: Contains general utility functions.
*   **`src/ui/`**: This folder will house all UI-related components.
    *   `custom_widgets.py`: Contains custom PyQt widgets.
    *   `dialogs.py`: Contains dialog box definitions.
    *   `styles.py`: Manages application styling.
    *   **`src/ui/tabs/`**: A sub-folder specifically for the different tab implementations, as they are all UI components and logically grouped.
        *   `main_tab.py`
        *   `rooms_tab.py`
        *   `history_tab.py`
        *   `supabase_config_tab.py`
        *   `rental_info_tab.py`
        *   `archived_info_tab.py`
*   **`icons/`**: This folder already exists and contains image assets, which is a good separation.
*   **Root Level**: `.gitignore`, `README.md`, and `requirements.txt` remain at the root as they are project-level configuration and documentation files.

## 2. Plan for Code Changes:

The primary changes will involve updating import statements in Python files to reflect the new folder structure.

*   **Step 1: Create the new directories.**
    *   `src/`
    *   `src/core/`
    *   `src/ui/`
    *   `src/ui/tabs/`
*   **Step 2: Move files to their respective new directories.**
    *   Move `HomeUnitCalculator.py`, `db_manager.py`, `encryption_utils.py`, `key_manager.py`, `utils.py` to `src/core/`.
    *   Move `custom_widgets.py`, `dialogs.py`, `styles.py` to `src/ui/`.
    *   Move `main_tab.py`, `rooms_tab.py`, `history_tab.py`, `supabase_config_tab.py`, `rental_info_tab.py`, `archived_info_tab.py` to `src/ui/tabs/`.
*   **Step 3: Update import statements.** This is the most critical step. I will need to go through each Python file and modify the `import` statements to reflect the new paths. For example:
    *   `from db_manager import DBManager` will become `from src.core.db_manager import DBManager`
    *   `from main_tab import MainTab` will become `from src.ui.tabs.main_tab import MainTab`
    *   Relative imports within the `src/ui/tabs/` directory will also need adjustment (e.g., if `history_tab.py` imports something from `main_tab.py`).

### Mermaid Diagram of Proposed Structure:

```mermaid
graph TD
    A[HomeUnitCalculator/] --> B[src/]
    B --> C[core/]
    B --> D[ui/]
    D --> E[tabs/]
    C --> C1[HomeUnitCalculator.py]
    C --> C2[db_manager.py]
    C --> C3[encryption_utils.py]
    C --> C4[key_manager.py]
    C --> C5[utils.py]
    D --> D1[custom_widgets.py]
    D --> D2[dialogs.py]
    D --> D3[styles.py]
    E --> E1[main_tab.py]
    E --> E2[rooms_tab.py]
    E --> E3[history_tab.py]
    E --> E4[supabase_config_tab.py]
    E --> E5[rental_info_tab.py]
    E --> E6[archived_info_tab.py]
    A --> F[icons/]
    A --> G[.gitignore]
    A --> H[README.md]
    A --> I[requirements.txt]