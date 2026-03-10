## Goal
Make packaged app open “instantly” by:
- Showing first window fast (target: ~1–3s typical).
- Reducing worst-case spikes (target: no 20s outliers).

## Key facts driving the approach
- The slowness is mainly in the packaged build.
- One-file builds inherently have extraction + AV scan variance.
- Your code also eagerly imports heavy tabs (e.g. [rental_info_tab.py](file:///d:/hmc/HomeUnitCalculator/src/ui/tabs/rental_info_tab.py#L14-L45) imports reportlab/requests at module import time), which is paid at startup today.

## Plan (Startup first)
### Phase A — Measure baseline accurately
- Improve startup timing output around:
  - application imports
  - main window creation
  - each tab construction
- Update [tools/startup_profiler.py](file:///d:/hmc/HomeUnitCalculator/tools/startup_profiler.py) so it profiles what the app actually imports (avoid importing reportlab/PIL/supabase eagerly if the app doesn’t).

### Phase B — Reduce code-level startup cost
1. **Lazy-load heavy tabs** using [lazy_tab_loader.py](file:///d:/hmc/HomeUnitCalculator/src/core/lazy_tab_loader.py)
   - Eager: Main (and optionally Rooms).
   - Lazy: History/Rental/Archived/Supabase Config via placeholders.
2. **Defer heavy imports inside tab actions**
   - Move `reportlab` imports into PDF-generation functions in rental/archived tabs.
   - Move `requests` imports into image-download code paths.
3. **Delay non-critical initialization until after first paint**
   - Supabase init and data loads happen after the UI is visible (QTimer/worker).

### Phase C — Reduce packaged startup variance (distribution change)
- Recommend shipping **onedir** as the default “fast startup” build (you already have this pattern in [QFluentUi_Build.yml](file:///d:/hmc/HomeUnitCalculator/.github/workflows/QFluentUi_Build.yml#L40-L46)).
- Keep onefile as optional (it will always be slower/more variable, but Phase B still helps it).

## Verification after every edit (your requirement)
After each logical edit, I will immediately run a quick validation step before continuing:
- **Syntax/compile check**: `python -m py_compile` on changed modules.
- **Import smoke test**: `python -c "from src.core.HomeUnitCalculator import MeterCalculationApp"`.
- **Runtime smoke** (when needed): start the app briefly to ensure it launches.
- After major milestones: build verification (PyInstaller onedir/onefile or Nuitka) to ensure packaging still works.

If you accept this plan, I’ll start implementing Phase A → B → C, and I’ll keep each change small and verifiable with the checks above.