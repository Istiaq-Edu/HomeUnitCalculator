import os
import sqlite3
import json
import re
from datetime import datetime
from src.core.encryption_utils import EncryptionUtil
from src.core.utils import get_user_data_dir

class DBManager:
    def __init__(self, db_name="app_config.db"):
        if db_name and not os.path.isabs(db_name) and os.path.dirname(db_name) == "":
            data_dir = get_user_data_dir()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_name = str(data_dir / db_name)
        else:
            self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.encryption_util = EncryptionUtil()
        self._connect()
        self._create_table()

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point, ensures connection is closed."""
        self.close()

    def __del__(self):
        """Destructor to ensure the connection is closed when the object is garbage collected."""
        self.close()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            # Return rows as dictionaries instead of bare tuples
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise

    def _create_table(self):
        """Creates the app_config table if it doesn't exist."""
        try:
            self.create_table("""
                CREATE TABLE IF NOT EXISTS app_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value BLOB
                )
            """)
        except sqlite3.Error as e:
            print(f"Error creating app_config table: {e}")
            raise

    def bootstrap_rentals_table(self):
        """Creates the rentals table and ensures all necessary columns exist."""
        try:
            self.create_table("""
                CREATE TABLE IF NOT EXISTS rentals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    room_number TEXT NOT NULL,
                    advanced_paid REAL,
                    photo_path TEXT,
                    nid_front_path TEXT,
                    nid_back_path TEXT,
                    police_form_path TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    is_archived INTEGER DEFAULT 0,
                    supabase_id TEXT UNIQUE
                )
            """)
            # Add is_archived column if it doesn't exist (for backward compatibility)
            columns = self.execute_query(
                "PRAGMA table_info(rentals);"
            )
            column_names = [col[1] for col in columns]
            if 'is_archived' not in column_names:
                try:
                    self.execute_query("""
                        ALTER TABLE rentals ADD COLUMN is_archived INTEGER DEFAULT 0;
                    """)
                    print("Added 'is_archived' column to rentals table.")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("Column 'is_archived' already exists, skipping addition.")
                    else:
                        raise # Re-raise other operational errors
            
            # Add supabase_id column and its unique index if they don't exist
            if 'supabase_id' not in column_names:
                try:
                    # Add the column without the UNIQUE constraint first
                    self.execute_query("""
                        ALTER TABLE rentals ADD COLUMN supabase_id TEXT;
                    """)
                    print("Added 'supabase_id' column to rentals table.")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise # Re-raise other operational errors

            # Now, create a unique index on the column.
            # This is the recommended way to add a unique constraint to an existing table in SQLite.
            try:
                self.execute_query("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_rentals_supabase_id ON rentals (supabase_id);
                """)
                # Unique index ensured
                pass
            except sqlite3.OperationalError as e:
                # This might fail if there are duplicate values in existing rows (e.g., all NULLs).
                # Depending on the desired behavior, you might want to handle this.
                # For now, we'll print a warning.
                print(f"Could not create unique index on 'supabase_id'. This may be because of existing duplicate values. Error: {e}")

            # Rentals table ready
            pass
        except Exception as e:
            print(f"Database Error: Failed to bootstrap rentals table: {e}")
            raise

    def bootstrap_dashboard_cache_tables(self):
        try:
            self.create_table("""
                CREATE TABLE IF NOT EXISTS main_calculations_cache (
                    source TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    month TEXT,
                    year INTEGER,
                    grand_total REAL,
                    added_amount REAL,
                    main_data_json TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    synced_at TEXT NOT NULL,
                    PRIMARY KEY (source, record_id),
                    UNIQUE (source, month, year)
                )
            """)
            cols = self.execute_query("PRAGMA table_info(main_calculations_cache);")
            col_names = [c[1] for c in cols] if cols else []
            if "added_amount" not in col_names:
                try:
                    self.execute_query("ALTER TABLE main_calculations_cache ADD COLUMN added_amount REAL;")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise

            self.create_table("""
                CREATE TABLE IF NOT EXISTS room_calculations_cache (
                    source TEXT NOT NULL,
                    main_record_id TEXT NOT NULL,
                    room_record_id TEXT NOT NULL,
                    month TEXT,
                    year INTEGER,
                    room_name TEXT,
                    grand_total REAL,
                    room_data_json TEXT,
                    synced_at TEXT NOT NULL,
                    PRIMARY KEY (source, room_record_id),
                    UNIQUE (source, year, month, room_name)
                )
            """)
            self.create_table("""
                CREATE TABLE IF NOT EXISTS rental_records_cache (
                    source TEXT NOT NULL,
                    supabase_id TEXT,
                    tenant_name TEXT,
                    room_number TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    start_year INTEGER,
                    start_month INTEGER,
                    end_year INTEGER,
                    end_month INTEGER,
                    is_archived INTEGER DEFAULT 0,
                    synced_at TEXT NOT NULL,
                    PRIMARY KEY (source, supabase_id),
                    UNIQUE (source, room_number, tenant_name, created_at)
                )
            """)
            self.create_table("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
        except Exception as e:
            print(f"Database Error: Failed to bootstrap dashboard cache tables: {e}")
            raise

    def get_sync_state(self, key: str) -> str | None:
        row = self.execute_query(
            "SELECT value FROM sync_state WHERE key = ?",
            (key,),
            fetch_one=True,
        )
        return row["value"] if row else None

    def set_sync_state(self, key: str, value: str) -> None:
        self.execute_query(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
            (key, value),
        )

    def upsert_main_calculations_cache(self, records: list[dict], source: str = "supabase") -> None:
        if not records:
            return

        now_iso = datetime.utcnow().isoformat()
        for record in records:
            record_id = record.get("id")
            if record_id is None:
                continue

            month = record.get("month")
            year = record.get("year")
            main_data = record.get("main_data") or {}
            grand_total = None
            added_amount = None
            try:
                grand_total = float(main_data.get("grand_total")) if main_data.get("grand_total") is not None else None
            except Exception:
                grand_total = None
            try:
                added_amount = float(main_data.get("added_amount")) if main_data.get("added_amount") is not None else None
            except Exception:
                added_amount = None

            created_at = record.get("created_at")
            updated_at = record.get("updated_at")

            try:
                main_data_json = json.dumps(main_data, ensure_ascii=False)
            except Exception:
                main_data_json = None

            self.execute_query(
                """
                INSERT INTO main_calculations_cache
                    (source, record_id, month, year, grand_total, added_amount, main_data_json, created_at, updated_at, synced_at)
                VALUES
                    (:source, :record_id, :month, :year, :grand_total, :added_amount, :main_data_json, :created_at, :updated_at, :synced_at)
                ON CONFLICT(source, month, year) DO UPDATE SET
                    record_id=excluded.record_id,
                    grand_total=excluded.grand_total,
                    added_amount=excluded.added_amount,
                    main_data_json=excluded.main_data_json,
                    created_at=COALESCE(excluded.created_at, main_calculations_cache.created_at),
                    updated_at=COALESCE(excluded.updated_at, main_calculations_cache.updated_at),
                    synced_at=excluded.synced_at
                """,
                {
                    "source": source,
                    "record_id": str(record_id),
                    "month": month,
                    "year": year,
                    "grand_total": grand_total,
                    "added_amount": added_amount,
                    "main_data_json": main_data_json,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "synced_at": now_iso,
                },
            )

    def upsert_room_calculations_cache(self, entries: list[dict], source: str = "supabase") -> None:
        if not entries:
            return

        now_iso = datetime.utcnow().isoformat()
        for e in entries:
            room_record_id = e.get("room_record_id")
            main_record_id = e.get("main_record_id")
            if room_record_id is None or main_record_id is None:
                continue

            month = e.get("month")
            year = e.get("year")
            room_name = e.get("room_name")
            grand_total = e.get("grand_total")
            room_data = e.get("room_data") or {}

            try:
                room_data_json = json.dumps(room_data, ensure_ascii=False)
            except Exception:
                room_data_json = None

            try:
                grand_total_val = float(grand_total) if grand_total is not None else None
            except Exception:
                grand_total_val = None

            self.execute_query(
                """
                INSERT INTO room_calculations_cache
                    (source, main_record_id, room_record_id, month, year, room_name, grand_total, room_data_json, synced_at)
                VALUES
                    (:source, :main_record_id, :room_record_id, :month, :year, :room_name, :grand_total, :room_data_json, :synced_at)
                ON CONFLICT(source, year, month, room_name) DO UPDATE SET
                    main_record_id=excluded.main_record_id,
                    room_record_id=excluded.room_record_id,
                    grand_total=excluded.grand_total,
                    room_data_json=excluded.room_data_json,
                    synced_at=excluded.synced_at
                """,
                {
                    "source": source,
                    "main_record_id": str(main_record_id),
                    "room_record_id": str(room_record_id),
                    "month": month,
                    "year": year,
                    "room_name": room_name,
                    "grand_total": grand_total_val,
                    "room_data_json": room_data_json,
                    "synced_at": now_iso,
                },
            )

    def upsert_rental_records_cache(self, records: list[dict], source: str = "supabase") -> None:
        if not records:
            return

        now_iso = datetime.utcnow().isoformat()
        for r in records:
            supabase_id = r.get("supabase_id") or r.get("id")
            if not supabase_id:
                continue

            self.execute_query(
                """
                INSERT INTO rental_records_cache
                    (source, supabase_id, tenant_name, room_number, created_at, updated_at, start_year, start_month, end_year, end_month, is_archived, synced_at)
                VALUES
                    (:source, :supabase_id, :tenant_name, :room_number, :created_at, :updated_at, :start_year, :start_month, :end_year, :end_month, :is_archived, :synced_at)
                ON CONFLICT(source, supabase_id) DO UPDATE SET
                    tenant_name=excluded.tenant_name,
                    room_number=excluded.room_number,
                    created_at=COALESCE(excluded.created_at, rental_records_cache.created_at),
                    updated_at=COALESCE(excluded.updated_at, rental_records_cache.updated_at),
                    start_year=excluded.start_year,
                    start_month=excluded.start_month,
                    end_year=excluded.end_year,
                    end_month=excluded.end_month,
                    is_archived=excluded.is_archived,
                    synced_at=excluded.synced_at
                """,
                {
                    "source": source,
                    "supabase_id": str(supabase_id),
                    "tenant_name": r.get("tenant_name"),
                    "room_number": r.get("room_number"),
                    "created_at": r.get("created_at"),
                    "updated_at": r.get("updated_at"),
                    "start_year": r.get("start_year"),
                    "start_month": r.get("start_month"),
                    "end_year": r.get("end_year"),
                    "end_month": r.get("end_month"),
                    "is_archived": int(r.get("is_archived") or 0),
                    "synced_at": now_iso,
                },
            )

    def get_cached_rooms(self, year: int, source: str = "supabase") -> list[str]:
        rows = self.execute_query(
            """
            SELECT DISTINCT room_name
            FROM room_calculations_cache
            WHERE source = ? AND year = ? AND room_name IS NOT NULL
            ORDER BY room_name
            """,
            (source, int(year)),
        )
        return [str(r["room_name"]) for r in rows] if rows else []

    def get_cached_monthly_room_totals(self, year: int, room_name: str, source: str = "supabase") -> dict[str, float | None]:
        rows = self.execute_query(
            """
            SELECT month, grand_total
            FROM room_calculations_cache
            WHERE source = ? AND year = ? AND room_name = ?
            """,
            (source, int(year), str(room_name)),
        )
        out: dict[str, float | None] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                v = r["grand_total"]
                if v is None:
                    out[str(m)] = None
                else:
                    try:
                        out[str(m)] = float(v)
                    except Exception:
                        out[str(m)] = None
        return out

    def get_cached_monthly_room_unit_bills(self, year: int, room_name: str, source: str = "supabase") -> dict[str, float | None]:
        rows = self.execute_query(
            """
            SELECT month, room_data_json
            FROM room_calculations_cache
            WHERE source = ? AND year = ? AND room_name = ?
            """,
            (source, int(year), str(room_name)),
        )
        out: dict[str, float | None] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                try:
                    room_data = json.loads(r["room_data_json"] or "{}")
                except Exception:
                    room_data = {}
                v = room_data.get("unit_bill")
                if v is None:
                    out[str(m)] = None
                else:
                    try:
                        out[str(m)] = float(v)
                    except Exception:
                        out[str(m)] = None
        return out

    def get_cached_monthly_room_water_bills(self, year: int, room_name: str, source: str = "supabase") -> dict[str, float | None]:
        rows = self.execute_query(
            """
            SELECT month, room_data_json
            FROM room_calculations_cache
            WHERE source = ? AND year = ? AND room_name = ?
            """,
            (source, int(year), str(room_name)),
        )
        out: dict[str, float | None] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                try:
                    room_data = json.loads(r["room_data_json"] or "{}")
                except Exception:
                    room_data = {}
                v = room_data.get("water_bill")
                if v is None:
                    out[str(m)] = None
                else:
                    try:
                        out[str(m)] = float(v)
                    except Exception:
                        out[str(m)] = None
        return out

    def get_cached_monthly_owner_added_amounts(self, year: int, source: str = "supabase") -> dict[str, float | None]:
        rows = self.execute_query(
            """
            SELECT month, added_amount
            FROM main_calculations_cache
            WHERE source = ? AND year = ?
            """,
            (source, int(year)),
        )
        out: dict[str, float | None] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                v = r["added_amount"]
                if v is None:
                    out[str(m)] = None
                else:
                    try:
                        out[str(m)] = float(v)
                    except Exception:
                        out[str(m)] = None
        return out

    def get_cached_monthly_owner_unit_bills(self, year: int, source: str = "supabase") -> dict[str, float | None]:
        main_rows = self.execute_query(
            """
            SELECT month, main_data_json
            FROM main_calculations_cache
            WHERE source = ? AND year = ?
            """,
            (source, int(year)),
        )
        main_by_month: dict[str, dict] = {}
        if main_rows:
            for r in main_rows:
                m = r["month"]
                if not m:
                    continue
                try:
                    main_by_month[str(m)] = json.loads(r["main_data_json"] or "{}")
                except Exception:
                    main_by_month[str(m)] = {}

        room_rows = self.execute_query(
            """
            SELECT month, room_data_json
            FROM room_calculations_cache
            WHERE source = ? AND year = ?
            """,
            (source, int(year)),
        )
        sums: dict[str, dict[str, float]] = {}
        if room_rows:
            for r in room_rows:
                m = r["month"]
                if not m:
                    continue
                mm = str(m)
                if mm not in sums:
                    sums[mm] = {"water": 0.0, "unit": 0.0}
                try:
                    room_data = json.loads(r["room_data_json"] or "{}")
                except Exception:
                    room_data = {}
                try:
                    sums[mm]["water"] += float(room_data.get("water_bill") or 0.0)
                except Exception:
                    pass
                try:
                    sums[mm]["unit"] += float(room_data.get("unit_bill") or 0.0)
                except Exception:
                    pass

        out: dict[str, float | None] = {}
        for month, main_data in main_by_month.items():
            try:
                total_unit_cost = float(main_data.get("total_unit_cost"))
            except Exception:
                total_unit_cost = None
            if total_unit_cost is None:
                out[month] = None
                continue
            month_sums = sums.get(month)
            if not month_sums:
                out[month] = None
                continue
            out[month] = float(total_unit_cost) - (float(month_sums["water"]) + float(month_sums["unit"]))
        return out

    def get_cached_monthly_per_unit_cost(self, year: int, source: str = "supabase") -> dict[str, float | None]:
        rows = self.execute_query(
            """
            SELECT month, main_data_json
            FROM main_calculations_cache
            WHERE source = ? AND year = ?
            """,
            (source, int(year)),
        )
        out: dict[str, float | None] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                try:
                    main_data = json.loads(r["main_data_json"] or "{}")
                except Exception:
                    main_data = {}
                v = main_data.get("per_unit_cost")
                if v is None:
                    out[str(m)] = None
                else:
                    try:
                        out[str(m)] = float(v)
                    except Exception:
                        out[str(m)] = None
        return out

    def get_cached_monthly_total_electricity_bills(self, year: int, source: str = "supabase") -> dict[str, float | None]:
        """Return total electricity (unit) bill for the entire building per month.

        Reads ``total_unit_cost`` from ``main_calculations_cache.main_data_json``.
        Returns a ``dict`` mapping month-name string → float (or None if missing).
        """
        rows = self.execute_query(
            """
            SELECT month, main_data_json
            FROM main_calculations_cache
            WHERE source = ? AND year = ?
            """,
            (source, int(year)),
        )
        out: dict[str, float | None] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                try:
                    main_data = json.loads(r["main_data_json"] or "{}")
                except Exception:
                    main_data = {}
                v = main_data.get("total_unit_cost")
                if v is None:
                    out[str(m)] = None
                else:
                    try:
                        out[str(m)] = float(v)
                    except Exception:
                        out[str(m)] = None
        return out

    def get_rental_records_for_room(self, room_number: str) -> list[sqlite3.Row]:
        rows = self.execute_query(
            """
            SELECT tenant_name, room_number, created_at, updated_at, is_archived
            FROM rental_records_cache
            WHERE room_number = ?
            ORDER BY created_at
            """,
            (str(room_number),),
        )
        if rows:
            return rows
        return self.execute_query(
            """
            SELECT tenant_name, room_number, created_at, updated_at, is_archived
            FROM rentals
            WHERE room_number = ?
            ORDER BY created_at
            """,
            (str(room_number),),
        ) or []

    def get_cached_years(self, source: str = "supabase") -> list[int]:
        rows = self.execute_query(
            "SELECT DISTINCT year FROM main_calculations_cache WHERE source = ? AND year IS NOT NULL ORDER BY year DESC",
            (source,),
        )
        return [int(r["year"]) for r in rows] if rows else []

    def get_cached_monthly_totals(self, year: int, source: str = "supabase") -> dict[str, float]:
        rows = self.execute_query(
            """
            SELECT month, SUM(COALESCE(grand_total, 0)) AS total
            FROM main_calculations_cache
            WHERE source = ? AND year = ?
            GROUP BY month
            """,
            (source, year),
        )
        out: dict[str, float] = {}
        if rows:
            for r in rows:
                m = r["month"]
                if not m:
                    continue
                try:
                    out[str(m)] = float(r["total"] or 0.0)
                except Exception:
                    out[str(m)] = 0.0
        return out

    def execute_query(
        self,
        query: str,
        params: tuple | dict | None = None,
        fetch_one: bool = False,
    ) -> sqlite3.Row | list[sqlite3.Row] | int | None:
        """
        Executes a SQL query with optional parameters.

        For data-modifying queries (INSERT, UPDATE, DELETE), changes are committed.
        - For INSERT or REPLACE queries, the last inserted row ID (int) is returned.
        - For other data-modifying queries (e.g., UPDATE, DELETE), None is returned.

        For data-retrieval queries (e.g., SELECT, PRAGMA):
        - If `fetch_one` is True, a single row (sqlite3.Row) is returned, or None if no row is found.
        - If `fetch_one` is False, all matching rows (list[sqlite3.Row]) are returned.
          An empty list is returned if no rows match.

        :param query: The SQL query string to execute.
        :param params: Optional. A tuple for positional placeholders, or a dictionary for
                       named placeholders. If None, the query is executed without parameters.
        :param fetch_one: If True, fetches only the first row for data-retrieval queries.
                          If False, fetches all matching rows.
        :return: A single row (sqlite3.Row), a list of rows (list[sqlite3.Row]),
                 the last inserted row ID (int), or None, depending on the query
                 type and fetch flags.
        :raises sqlite3.Error: If a database error occurs during query execution.
        :raises Exception: For other unexpected errors.
        """
        try:
            # execute once with empty dict if params is None, to handle named placeholders
            if params is None:
                self.cursor.execute(query)
            else:
                self.cursor.execute(query, params)
            
            # If the statement produced a result-set, fetch it; otherwise commit.
            if self.cursor.description:  # SELECT / PRAGMA / etc.
                if fetch_one:
                    return self.cursor.fetchone()
                # If fetch_one is not requested, default to fetching all results.
                return self.cursor.fetchall()

            # No result-set → it's a write or DDL
            self.conn.commit()
            if query.lstrip().upper().startswith(("INSERT", "REPLACE")):
                return self.cursor.lastrowid
            return None
        except sqlite3.Error as e:
            print(f"Database query error: {e}\nQuery: {query}\nParams: {params}")
            self.conn.rollback()
            raise
        except Exception as e:
            print(f"An unexpected error occurred during query execution: {e}")
            raise

    def create_table(self, query: str):
        """
        Executes a CREATE TABLE query.
        """
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
            raise

    def save_config(self, supabase_url: str, supabase_key: str):
        """
        Encrypts and saves Supabase URL and Key to the database.
        Overwrites existing configuration if present.
        """
        try:
            encrypted_url = self.encryption_util.encrypt_data(supabase_url)
            encrypted_key = self.encryption_util.encrypt_data(supabase_key)

            # Store as JSON string to keep both values associated with one entry if needed,
            # or as separate entries. For simplicity, let's store them as separate keys.
            # Alternatively, you could store a JSON blob of all config.
            
            # Using separate keys for clarity and easy retrieval
            self.cursor.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                                ("SUPABASE_URL", encrypted_url))
            self.cursor.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                                ("SUPABASE_KEY", encrypted_key))
            self.conn.commit()
            print("Supabase configuration saved successfully.")
        except sqlite3.Error as e:
            print(f"Error saving configuration: {e}")
            self.conn.rollback()
            raise
        except Exception as e:
            print(f"Encryption/decryption error during save: {e}")
            raise

    def get_config(self) -> dict:
        """
        Retrieves and decrypts Supabase URL and Key from the database.
        Returns a dictionary with 'SUPABASE_URL' and 'SUPABASE_KEY'.
        Returns empty dict if not found.
        """
        config = {}
        try:
            self.cursor.execute("SELECT key, value FROM app_config WHERE key IN ('SUPABASE_URL', 'SUPABASE_KEY')")
            rows = self.cursor.fetchall()
            
            for row in rows:
                try:
                    decrypted_value = self.encryption_util.decrypt_data(row["value"])
                    config[row["key"]] = decrypted_value
                except Exception as e:
                    print(f"Error decrypting value for key {row['key']}: {e}")
                    # Continue to try decrypting other values
            
            if "SUPABASE_URL" not in config or "SUPABASE_KEY" not in config:
                print("Supabase configuration not found or incomplete in database.")
                return {}

        except sqlite3.Error as e:
            print(f"Error retrieving configuration: {e}")
            return {}
        except Exception as e:
            print(f"Encryption/decryption error during retrieval: {e}")
            return {}
        return config

    def config_exists(self) -> bool:
        """Checks if Supabase configuration exists in the database."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM app_config WHERE key IN ('SUPABASE_URL', 'SUPABASE_KEY')")
            count = self.cursor.fetchone()[0]
            return count >= 2 # Both URL and Key must be present
        except sqlite3.Error as e:
            print(f"Error checking config existence: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            # Connection closed
            pass

    def insert_rental_record(self, record_data: dict) -> int:
        """Insert a new rental record and return its new row-id.

        ``record_data`` follows the structure assembled in RentalInfoTab.save_rental_record.
        Extra keys are ignored.
        """
        insert_sql = (
            "INSERT OR REPLACE INTO rentals (tenant_name, room_number, advanced_paid, "
            "photo_path, nid_front_path, nid_back_path, police_form_path, "
            "created_at, updated_at, is_archived, supabase_id) "
            "VALUES (:tenant_name, :room_number, :advanced_paid, :photo_path, "
            ":nid_front_path, :nid_back_path, :police_form_path, :created_at, :updated_at, "
            ":is_archived, :supabase_id)"
        )
        # Execute and return the lastrowid
        return int(self.execute_query(insert_sql, record_data))

if __name__ == "__main__":
    # Example usage and testing
    print("Testing db_manager.py...")
    test_db_name = "test_app_config.db"
    
    # Clean up previous test database if it exists
    if os.path.exists(test_db_name):
        os.remove(test_db_name)
        print(f"Removed existing test database: {test_db_name}")

    db_manager = None
    try:
        db_manager = DBManager(db_name=test_db_name)
        
        # Test create_table
        print("\nTesting create_table...")
        db_manager.create_table("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        print("test_table created successfully.")

        # Test execute_query (INSERT)
        print("\nTesting execute_query (INSERT)...")
        last_id = db_manager.execute_query("INSERT INTO test_table (name) VALUES (?)", ("Test Name 1",))
        print(f"Inserted record with ID: {last_id}")
        assert last_id is not None

        # Test execute_query (SELECT)
        print("\nTesting execute_query (SELECT)...")
        rows = db_manager.execute_query("SELECT * FROM test_table", fetch_all=True)
        print(f"Retrieved rows: {rows}")
        assert len(rows) == 1
        assert rows[0][1] == "Test Name 1"

        # Test execute_query (UPDATE)
        print("\nTesting execute_query (UPDATE)...")
        db_manager.execute_query("UPDATE test_table SET name = ? WHERE id = ?", ("Updated Name", 1))
        updated_row = db_manager.execute_query("SELECT * FROM test_table WHERE id = ?", (1,), fetch_one=True)
        print(f"Updated row: {updated_row}")
        assert updated_row[1] == "Updated Name"

        # Test execute_query (DELETE)
        print("\nTesting execute_query (DELETE)...")
        db_manager.execute_query("DELETE FROM test_table WHERE id = ?", (1,))
        deleted_row = db_manager.execute_query("SELECT * FROM test_table WHERE id = ?", (1,), fetch_one=True)
        print(f"Deleted row: {deleted_row}")
        assert deleted_row is None

        # Test saving config
        test_url = "https://test.supabase.co"
        test_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoIiwicm9sZSI6ImFub24iLCJpYXQiOjE2NzgyMzU2MDAsImV4cCI6MTk5MzgxMTYwMH0.some_random_key_here"
        
        print("\nSaving test configuration...")
        db_manager.save_config(test_url, test_key)
        
        # Test config_exists
        exists = db_manager.config_exists()
        print(f"Config exists after saving: {exists}")
        assert exists == True

        # Test retrieving config
        print("\nRetrieving test configuration...")
        retrieved_config = db_manager.get_config()
        print(f"Retrieved URL: {retrieved_config.get('SUPABASE_URL')}")
        print(f"Retrieved Key: {retrieved_config.get('SUPABASE_KEY')}")
        assert retrieved_config.get("SUPABASE_URL") == test_url
        assert retrieved_config.get("SUPABASE_KEY") == test_key
        print("Configuration retrieval successful and matches original.")

        # Test overwriting config
        new_test_url = "https://new.supabase.co"
        new_test_key = "new_key_12345"
        print("\nSaving new configuration (overwriting)...")
        db_manager.save_config(new_test_url, new_test_key)
        
        retrieved_new_config = db_manager.get_config()
        print(f"Retrieved New URL: {retrieved_new_config.get('SUPABASE_URL')}")
        print(f"Retrieved New Key: {retrieved_new_config.get('SUPABASE_KEY')}")
        assert retrieved_new_config.get("SUPABASE_URL") == new_test_url
        assert retrieved_new_config.get("SUPABASE_KEY") == new_test_key
        print("Configuration overwrite successful.")

        # Test with no config
        db_manager.execute_query("DELETE FROM app_config")
        print("\nDeleted all config entries.")
        exists_after_delete = db_manager.config_exists()
        print(f"Config exists after deleting: {exists_after_delete}")
        assert exists_after_delete == False
        
        empty_config = db_manager.get_config()
        print(f"Retrieved config after deleting: {empty_config}")
        assert empty_config == {}

    except Exception as e:
        print(f"An error occurred during testing: {e}")
    finally:
        if db_manager:
            db_manager.close()
        if os.path.exists(test_db_name):
            os.remove(test_db_name)
            print(f"Cleaned up test database: {test_db_name}")
