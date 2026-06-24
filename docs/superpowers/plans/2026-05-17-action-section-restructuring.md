# Action Section Restructuring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Calculator tab's Action section into three visually distinct containers (Load Data, Save Options, Add Next Month) while preserving all existing functionality and preventing UI distortion.

**Architecture:** Replace the monolithic `create_load_info_group()` method with three focused container-creation methods. Update `init_ui()` to stack them vertically inside the existing `CollapsibleSection`. All widget references on `self` are preserved for compatibility.

**Tech Stack:** PyQt5, QFluentWidgets, Python

---

### Task 1: Create the Load Data container method

**Files:**
- Modify: `src/ui/tabs/main_tab.py`

This method creates the first container with Month combo, Year spinbox, Source dropdown, and Load button in a horizontal flow.

- [ ] **Step 1: Add `_create_load_data_container()` method**

Add this new method to the `MainTab` class. Place it after the existing `create_load_info_group()` method (around line 2208). This method returns a `QWidget` containing the load controls.

```python
def _create_load_data_container(self):
    """Container 1: Load Data — Month/Year selection, source, and load button."""
    container = QWidget()
    container.setObjectName("load_data_container")
    container.setAttribute(Qt.WA_StyledBackground, True)
    container.setAutoFillBackground(True)
    container.setFocusPolicy(Qt.NoFocus)
    container.setAttribute(Qt.WA_Hover, False)
    container.setMouseTracking(False)
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    container.setStyleSheet("""
        #load_data_container {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-left: 3px solid #3d3d3d;
            border-radius: 8px;
        }
    """)

    layout = QHBoxLayout(container)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    # Month
    load_month_label = BodyLabel("Month:")
    load_month_label.setStyleSheet("font-weight: bold; color: #ffffff;")
    self.load_month_combo = ComboBox()
    self.load_month_combo.addItems([
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ])
    self.load_month_combo.setCurrentIndex(datetime.now().month - 1)
    self.load_month_combo.setMinimumWidth(140)
    self.load_month_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # Year
    load_year_label = BodyLabel("Year:")
    load_year_label.setStyleSheet("font-weight: bold; color: #ffffff;")
    self.load_year_spinbox = SpinBox()
    self.load_year_spinbox.setRange(2000, 2100)
    self.load_year_spinbox.setValue(datetime.now().year)
    self._apply_no_select_to_spinbox(self.load_year_spinbox)
    self.load_year_spinbox.setFocusPolicy(Qt.NoFocus)
    QTimer.singleShot(0, lambda: (self.load_year_spinbox.lineEdit() and self.load_year_spinbox.lineEdit().setFocusPolicy(Qt.NoFocus)))
    self.load_year_spinbox.setMinimumWidth(100)
    self.load_year_spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    try:
        le2 = self.load_year_spinbox.lineEdit() if hasattr(self.load_year_spinbox, 'lineEdit') else None
        if le2 is None:
            QTimer.singleShot(0, lambda: (
                self.load_year_spinbox.lineEdit() and self.load_year_spinbox.lineEdit().setFont(self.load_year_spinbox.lineEdit().font().setBold(True))
            ))
        else:
            f2 = le2.font()
            f2.setBold(True)
            le2.setFont(f2)
    except Exception:
        pass

    layout.addWidget(load_month_label, 0)
    layout.addWidget(self.load_month_combo, 2)
    layout.addSpacing(12)
    layout.addWidget(load_year_label, 0)
    layout.addWidget(self.load_year_spinbox, 1)

    # Source dropdown button
    self.main_window.load_info_source_combo.setVisible(False)
    current_source = self.main_window.load_info_source_combo.currentText()
    if "Cloud" in current_source:
        initial_icon = FluentIcon.CLOUD
        initial_label = "Load from Cloud"
    else:
        initial_icon = FluentIcon.DOCUMENT
        initial_label = "Load from CSV"

    self.load_source_button = DropDownPushButton(initial_icon, initial_label)
    self.load_source_button.setFixedHeight(36)
    try:
        self.load_source_button.setIcon(initial_icon.icon(color=QColor(255, 255, 255)))
    except Exception:
        pass
    self.load_source_button.setIconSize(QSize(20, 20))
    self.load_source_button.setMinimumWidth(180)
    self.load_source_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    menu = RoundMenu(parent=self.load_source_button)
    def _set_source(text, icon, label):
        self.main_window.load_info_source_combo.setCurrentText(text)
        try:
            qicon = icon.icon(color=QColor(255, 255, 255)) if hasattr(icon, 'icon') else icon
        except Exception:
            qicon = icon
        self.load_source_button.setIcon(qicon)
        self.load_source_button.setText(label)
        self._update_source_button_color(label)
    menu.addAction(Action(FluentIcon.DOCUMENT, "Load from CSV", triggered=lambda: _set_source("Load from PC (CSV)", FluentIcon.DOCUMENT, "Load from CSV")))
    menu.addAction(Action(FluentIcon.CLOUD, "Load from Cloud", triggered=lambda: _set_source("Load from Cloud", FluentIcon.CLOUD, "Load from Cloud")))
    self.load_source_button.setMenu(menu)
    self._update_source_button_color(initial_label)

    layout.addSpacing(12)
    layout.addWidget(self.load_source_button, 2)

    # Load button
    load_button = PrimaryPushButton("Load")
    load_button.setIcon(FluentIcon.DOWNLOAD.icon(color=QColor(255, 255, 255)))
    load_button.setIconSize(QSize(20, 20))
    load_button.clicked.connect(self.load_info_to_inputs)
    load_button.setFixedHeight(36)
    load_button.setStyleSheet("""
        PrimaryPushButton {
            color: white;
            background-color: #0078D4;
            border: 1px solid #0078D4;
            border-radius: 6px;
            font-weight: 600;
            qproperty-iconSize: 20px 20px;
            padding: 8px 16px 8px 36px;
        }
        PrimaryPushButton:hover {
            background-color: #106ebe;
            border-color: #106ebe;
        }
        PrimaryPushButton:pressed {
            background-color: #005a9e;
            border-color: #005a9e;
        }
    """)
    load_button.setMinimumWidth(120)
    load_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    layout.addSpacing(12)
    layout.addWidget(load_button, 1)

    return container
```

- [ ] **Step 2: Commit**

```bash
git add src/ui/tabs/main_tab.py
git commit -m "feat: add _create_load_data_container method"
```

---

### Task 2: Create the Save Options container method

**Files:**
- Modify: `src/ui/tabs/main_tab.py`

This method creates the second container with three equal-width save buttons.

- [ ] **Step 1: Add `_create_save_options_container()` method**

Add this method right after `_create_load_data_container()`. It returns a `QWidget` with three save buttons in a horizontal row, separated from the top by a hairline.

```python
def _create_save_options_container(self):
    """Container 2: Save Options — PDF, CSV, and Cloud save buttons."""
    container = QWidget()
    container.setObjectName("save_options_container")
    container.setAttribute(Qt.WA_StyledBackground, True)
    container.setAutoFillBackground(True)
    container.setFocusPolicy(Qt.NoFocus)
    container.setAttribute(Qt.WA_Hover, False)
    container.setMouseTracking(False)
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    container.setStyleSheet("""
        #save_options_container {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
        }
    """)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    # Top hairline separator
    top_sep = QFrame()
    top_sep.setFrameShape(QFrame.HLine)
    top_sep.setFrameShadow(QFrame.Plain)
    top_sep.setStyleSheet("color: #3d3d3d; background-color: #3d3d3d; border: none; height: 1px;")
    layout.addWidget(top_sep)

    # Buttons row
    buttons_row = QHBoxLayout()
    buttons_row.setSpacing(8)
    buttons_row.setContentsMargins(0, 4, 0, 0)

    # Save PDF
    pdf_button = PrimaryPushButton("Save PDF")
    pdf_button.setIcon(FluentIcon.DOCUMENT.icon(color=QColor(255, 255, 255)))
    pdf_button.setIconSize(QSize(20, 20))
    pdf_button.setFixedHeight(40)
    pdf_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    pdf_button.clicked.connect(self.main_window.save_to_pdf)
    pdf_button.setStyleSheet("""
        PrimaryPushButton {
            color: white;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d32f2f, stop:1 #b71c1c);
            border: 2px solid #d32f2f; border-radius: 8px; font-weight: 600; font-size: 14px;
            qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center;
        }
        PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f44336, stop:1 #d32f2f); border-color: #f44336; }
        PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b71c1c, stop:1 #8f1414); border-color: #b71c1c; }
    """)

    # Save CSV
    csv_button = PrimaryPushButton("Save CSV")
    csv_button.setIcon(FluentIcon.SAVE.icon(color=QColor(255, 255, 255)))
    csv_button.setIconSize(QSize(20, 20))
    csv_button.setFixedHeight(40)
    csv_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    csv_button.clicked.connect(self.main_window.save_calculation_to_csv)
    csv_button.setStyleSheet("""
        PrimaryPushButton {
            color: white;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #388e3c, stop:1 #2e7d32);
            border: 2px solid #388e3c; border-radius: 8px; font-weight: 600; font-size: 14px;
            qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center;
        }
        PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4caf50, stop:1 #388e3c); border-color: #4caf50; }
        PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2e7d32, stop:1 #1b5e20); border-color: #2e7d32; }
    """)

    # Save Cloud
    cloud_button = PrimaryPushButton("Save Cloud")
    cloud_button.setIcon(FluentIcon.CLOUD.icon(color=QColor(255, 255, 255)))
    cloud_button.setIconSize(QSize(20, 20))
    cloud_button.setFixedHeight(40)
    cloud_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    cloud_button.clicked.connect(self.main_window.save_calculation_to_supabase)
    cloud_button.setStyleSheet("""
        PrimaryPushButton {
            color: white;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7b1fa2, stop:1 #6a1b9a);
            border: 2px solid #7b1fa2; border-radius: 8px; font-weight: 600; font-size: 14px;
            qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center;
        }
        PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9c27b0, stop:1 #7b1fa2); border-color: #9c27b0; }
        PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a1b9a, stop:1 #4a148c); border-color: #6a1b9a; }
    """)

    buttons_row.addWidget(pdf_button, 1)
    buttons_row.addWidget(csv_button, 1)
    buttons_row.addWidget(cloud_button, 1)
    self._save_buttons_row = buttons_row
    layout.addLayout(buttons_row)

    return container
```

- [ ] **Step 2: Commit**

```bash
git add src/ui/tabs/main_tab.py
git commit -m "feat: add _create_save_options_container method"
```

---

### Task 3: Create the Add Next Month container method

**Files:**
- Modify: `src/ui/tabs/main_tab.py`

This method creates the third container with a single centered "Add Next Month" button.

- [ ] **Step 1: Add `_create_add_next_month_container()` method**

Add this method right after `_create_save_options_container()`.

```python
def _create_add_next_month_container(self):
    """Container 3: Add Next Month — single centered button."""
    container = QWidget()
    container.setObjectName("add_next_month_container")
    container.setAttribute(Qt.WA_StyledBackground, True)
    container.setAutoFillBackground(True)
    container.setFocusPolicy(Qt.NoFocus)
    container.setAttribute(Qt.WA_Hover, False)
    container.setMouseTracking(False)
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    container.setStyleSheet("""
        #add_next_month_container {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
        }
    """)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    # Dotted separator
    dotted_sep = QFrame()
    dotted_sep.setFrameShape(QFrame.HLine)
    dotted_sep.setFrameShadow(QFrame.Plain)
    dotted_sep.setStyleSheet("color: #4a4a4a; background-color: #4a4a4a; border: none; height: 1px;")
    layout.addWidget(dotted_sep)

    # Centered button
    add_next_month_button = PrimaryPushButton("Add Next Month")
    add_next_month_button.setIcon(FluentIcon.ADD.icon(color=QColor(255, 255, 255)))
    add_next_month_button.setIconSize(QSize(20, 20))
    add_next_month_button.clicked.connect(self.add_month_action)
    add_next_month_button.setFixedHeight(36)
    add_next_month_button.setStyleSheet("""
        PrimaryPushButton {
            color: white;
            background-color: #FF8C00;
            border: 1px solid #FF8C00;
            border-radius: 6px;
            font-weight: 600;
            qproperty-iconSize: 20px 20px;
            padding: 8px 16px 8px 36px;
        }
        PrimaryPushButton:hover {
            background-color: #FF7F00;
            border-color: #FF7F00;
        }
        PrimaryPushButton:pressed {
            background-color: #FF6600;
            border-color: #FF6600;
        }
    """)
    add_next_month_button.setMinimumWidth(240)
    add_next_month_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

    button_row = QHBoxLayout()
    button_row.setContentsMargins(0, 0, 0, 0)
    button_row.setSpacing(0)
    button_row.addStretch(1)
    button_row.addWidget(add_next_month_button)
    button_row.addStretch(1)
    layout.addLayout(button_row)

    return container
```

- [ ] **Step 2: Commit**

```bash
git add src/ui/tabs/main_tab.py
git commit -m "feat: add _create_add_next_month_container method"
```

---

### Task 4: Update `init_ui()` to use the three new containers

**Files:**
- Modify: `src/ui/tabs/main_tab.py` (lines 922-1008)

Replace the Actions section setup in `init_ui()` to call the three new methods and stack them vertically.

- [ ] **Step 1: Replace the Actions section in `init_ui()`**

Find the block from `# ── 1. Actions (collapsible, expanded by default)` through `actions_section = CollapsibleSection(...)` (lines 922-1008) and replace it with:

```python
        # ── 1. Actions (collapsible, expanded by default) ──────────────
        actions_content = QWidget()
        actions_content.setStyleSheet("""
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 12px;
        """)
        actions_content.setAttribute(Qt.WA_StyledBackground, True)
        actions_content.setAutoFillBackground(True)
        actions_content.setFocusPolicy(Qt.NoFocus)
        actions_content.setAttribute(Qt.WA_Hover, False)
        actions_content.setMouseTracking(False)
        self._load_data_group = actions_content
        actions_content.installEventFilter(self)

        actions_layout = QVBoxLayout(actions_content)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        # Three distinct containers stacked vertically
        load_data_container = self._create_load_data_container()
        actions_layout.addWidget(load_data_container)

        save_options_container = self._create_save_options_container()
        actions_layout.addWidget(save_options_container)

        add_next_month_container = self._create_add_next_month_container()
        actions_layout.addWidget(add_next_month_container)

        actions_section = CollapsibleSection("\u26a1 Actions", actions_content, expanded=True)
        main_layout.addWidget(actions_section)
```

Key changes:
- `actions_layout.setContentsMargins(0, 0, 0, 0)` — no inner margins since each container has its own padding
- `actions_layout.setSpacing(8)` — 8px gap between the three containers
- Three `addWidget` calls instead of the old inline widget creation
- Removed `self._save_buttons_row` assignment from inline code (now handled in `_create_save_options_container`)

- [ ] **Step 2: Commit**

```bash
git add src/ui/tabs/main_tab.py
git commit -m "refactor: restructure init_ui Actions section into three containers"
```

---

### Task 5: Remove the old `create_load_info_group()` method

**Files:**
- Modify: `src/ui/tabs/main_tab.py`

The old method is no longer called. Remove it to avoid dead code.

- [ ] **Step 1: Delete `create_load_info_group()` method**

Remove the entire `create_load_info_group()` method (lines 2042-2208). This method is no longer referenced anywhere.

- [ ] **Step 2: Commit**

```bash
git add src/ui/tabs/main_tab.py
git commit -m "refactor: remove obsolete create_load_info_group method"
```

---

### Task 6: Verify and test

**Files:**
- `src/ui/tabs/main_tab.py`

- [ ] **Step 1: Run the application**

```bash
python src/core/HomeUnitCalculator.py
```

Verify:
1. The Actions section shows three distinct containers stacked vertically
2. Load Data container has Month, Year, Source dropdown, Load button in a row
3. Save Options container has Save PDF, Save CSV, Save Cloud buttons in a row
4. Add Next Month container has a single centered button with dotted separator above
5. All buttons are functional (click Load, Save PDF, Save CSV, Save Cloud, Add Next Month)
6. Source dropdown menu works (CSV/Cloud toggle with color changes)
7. No UI distortion when resizing the window
8. The collapsible section still expands/collapses all three containers together
9. No console errors on startup

- [ ] **Step 2: Final commit**

```bash
git add src/ui/tabs/main_tab.py
git commit -m "feat: restructure Action section into three distinct containers"
```
