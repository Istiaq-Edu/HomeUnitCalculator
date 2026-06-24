# Changelog

All notable changes to HomeUnitCalculator will be documented in this file.

## [6.5.0] - 2026-06-24

### Bug Fixes

- Fix startup flicker and stabilize initial UI
- **ci:** Escape backticks in release body to fix SyntaxError
- **ci:** Use upload_url from release API for asset uploads
- **ci:** Use --jq to extract upload_url instead of --silent|ConvertFrom-Json

### Documentation

- Add action section redesign spec

### Enhancements

- Update db_manager.py
- Update history_tab.py
- Update HomeUnitCalculator.py
- Update HomeUnitCalculator.py
- Update main_tab.py

### Features

- Add frontend-design & supabase-postgres skills
- Add update coordinator & remote change polling
- Add writing-plans skill; refine brainstorming and UI
- Add _create_load_data_container method
- Add _create_save_options_container method
- Add _create_add_next_month_container method
- Add Calculator theme and refactor MainTab UI
- Add redesign plans and refine UI widgets

### Miscellaneous Tasks

- Add release workflow with draft release, PyInstaller build, and changelog

### Other

- Dashboard UI: widgets, charts & gas bill cache
- Merge rooms tab into MainTab, add widgets
- Make smooth scrolling more responsive
- Disable QFluentWidgets smooth scrolling

### Performance

- Improve UI scrolling, table resizing, and nav width
- Polish calculator UI: layout, styles, animations

### Refactor

- Restructure init_ui Actions section into three containers
- Remove obsolete create_load_info_group method
- Move save buttons to Calculate button row, remove save options container
- Unify billing container, move month/year top-left, add next month top-right, gray pair button

## [.6.1.0] - 2026-03-10

### Features

- Add electricity chart and dashboard improvements

## [.6.0.0] - 2026-01-15

### Features

- Add dashboard tab with yearly bill chart and Supabase sync
- Add room and rental records cache, enhance dashboard

## [.5.5.1] - 2026-01-14

### Enhancements

- Update installer paths to use RepoRoot variable

### Features

- Add Windows installer build and icon generation

### Other

- Refactor tab loading to use lazy initialization
- Use user data directory for app storage paths

## [5.2.0] - 2025-11-09

### Bug Fixes

- Fix owner unit bill calculation logic

## [.5.1.0] - 2025-10-18

### Enhancements

- Update PyInstaller build paths for CI workflow
- Update build-pyinstaller-spec.yml

### Features

- Add lean PyInstaller workflow and update hooks
- Add PyInstaller spec and CI workflow for lean build
- Add Owner Unit Bill section to PDF report
- Add optimized parallel image fetching and caching
- Add Supabase error handler and thumbnail image caching

### Other

- Revert "Update build-pyinstaller-spec.yml"
- Revert "Update PyInstaller build paths for CI workflow"
- Revert "Add PyInstaller spec and CI workflow for lean build"

### Performance

- Optimize image upload with JPEG compression
- Optimize startup performance and add profiling tools

## [.5.0.0] - 2025-10-04

### Enhancements

- Update PyQt-Fluent-Widgets to version 1.9.0

### Features

- Add modern save dialog and enhance data source UI

## [.4.5.0] - 2025-10-04

### Enhancements

- Update db_manager.py
- Update build workflow for multi-OS and Nuitka
- Update styles.py
- Update build workflow for Nuitka and artifact handling
- Update build.yml
- Update build-pyinstaller.yml
- Update PyInstaller workflow to manual trigger only
- Update QFluentUi_Build.yml
- Update QFluentUi_Build.yml
- Update QFluentUi_Build.yml
- Update QFluentUi_Build.yml
- Update QFluentUi_Build.yml
- Update QFluentUi_Build.yml
- Update supabase_patch.py
- Update QFluentUi_Build.yml
- Update QFluentUi_Build.yml
- Update main_tab.py

### Features

- Add new file types to ignore
- Implement secure database configuration management
- Add data encryption and decryption utilities
- Introduce robust encryption key management
- Add data and images directories to .gitignore
- Add save options and refactor rental record saving
- Add tests/ directory to .gitignore
- Add background worker for async Supabase record loading
- Add Fluent design InfoBar and progress dialog support
- Implement unified keyboard navigation across all tabs
- Add websockets dependency to requirements.txt
- Add icons directory to PyInstaller build
- Add imageio and pillow to build dependencies
- Add GitHub Actions workflow for PyInstaller build
- Create pyinstaller-build.yml
- Add requests and urllib3 dependencies, improve urllib3 import
- Add non-blocking message boxes and rental record insert
- Add inline progress bars for cloud fetch in rental tabs
- Add new feature to user profile page
- Add responsive UI infrastructure and enhance styling
- Add async image loading and cloud pagination for rentals
- Add automatic month progression and UI integration
- Add advanced table optimization and caching infrastructure
- Add GitHub Actions workflow for QFluentUi build
- Add PyInstaller hooks for supabase and realtime packages
- Add Supabase/realtime compatibility patch for PyInstaller

### Other

- New requirements added
- Better ignore
- New in app supabase configuration added
- Huge code refactored
- Make the colour palette immutable
- More improvement
- Modularize tab components into separate files.
- Some bug fixes and improvements
- More fix
- Advancement's
- More Improvements
- More improvements and features'
- Bug fixes
- Bug fixes
- Bug fix
- Refactor existing files into structured folder
- Bug fixes
- Initial commit
- Refactor Supabase data loading and filtering logic
- Refactor Supabase rental record handling and image support
- Refactor SupabaseManager and improve data handling
- Refactor color variable and update result value style
- Set build workflow to run only on Windows
- Disable SSL verification and suppress warnings in requests
- Refresh rental records from local DB after local save
- Fallback to insert if update affects no rows
- Cache remote images locally when saving rental records
- Redesign history tab controls and add LeftIconButton
- Use main window as parent for dialogs
- Forward table scroll events to parent scroll area
- Refactor table resize logic with debounced and cached resizing
- Standardize build log output messages
- Simplify QFluentUi build workflow
- Restrict QFluentUi build workflow to manual triggers
- Refactor meter and diff value extraction in EditRecordDialog
- Refactor result and billing UI for static card styling
- Refactor main tab layout and improve button styling
- Stabilize table sizing in Rental and Archived tabs
- Refactor table layout to use stretch mode in tabs
- Unify CardWidget styling and add StaticCardWidget
- Modernize table controls and save options UI
- Redesign EditRecordDialog with dark theme and custom UI
- Refactor RentalRecordDialog to standalone module

### Performance

- Improvements
- Improve image handling and PDF generation for rentals
- Enhance history tab and Supabase integration for room bills
- Improve resource_path to support Nuitka and robust root detection
- Improve numeric input handling and data normalization
- Improve dialog styling and message handling in UI tabs
- Improve UI layout and styling in MainTab
- Improve UI consistency and source selection in tabs
- Enhance RoomsTab UI with styling and separators
- Enhance history tables with modern styling and UX
- Enhance UI with smooth scrolling and modern button styles
- Improve data consistency and UI for history and room tables
- Improve table column resizing and styling logic
- Improve table cache handling and scroll sensitivity
- Improve Supabase/realtime compatibility patch for PyInstaller
- Improve Supabase realtime compatibility and packaging
- Improve icon loading for bundled app compatibility
- Enhance UI with responsive layout and modern styling
- Improve table column sizing and styling in info tabs
- Refine room tab UI and improve hover handling
- Improve info section styling in dialogs and tabs

### Removed

- Delete rental_info_tab_plan.md
- Delete folderization_plan.md
- Delete refactoring_plan.md
- Remove automatic build triggers from workflow
- Delete .github/workflows/pyinstaller-build.yml
- Remove excessive CSS effects from UI styles
- Remove debug prints and disable problematic animations
- Remove dialogs.py and improve rental tab refresh logic

## [.2.0.0] - 2025-05-19

### Other

- Revamped and Improved with some new features

## [.1.2.0] - 2024-10-18

### Other

- Improvement
- Little improvement
- Add new feature Load info

## [1.1.0] - 2024-10-09

### Enhancements

- Update .gitignore

### Features

- Added Demo Software Images
- Add Demo Images of software
- Add additional amount opntion

### Other

- Refactor with extensive comments
- Improve scroll bar and room selection section

## [1.0.0] - 2024-10-07

### Bug Fixes

- Fix Navigations

### Features

- Add files via upload
- Add files via upload
- Add files via upload
- Add files via upload
- Add gitignore

### Other

- Reform
- Reform
- Add build yml file
- Not needed
- Updated artifact version
- Reform of icons
- Version updated
- Refactor the use of icons
- Add manual trigger
- Icons style change
- Refactor the use of icons

### Removed

- Delete 10.pdf
- Delete HUC.py

<!-- generated by git-cliff -->
