from src.ui.tabs.dashboard_tab import DashboardTab


class _FakeDbManager:
    def __init__(self, records_by_room):
        self.records_by_room = records_by_room
        self.calls = []

    def get_rental_records_for_room(self, room_number):
        self.calls.append(str(room_number))
        return list(self.records_by_room.get(str(room_number), []))


def test_build_tenant_lookup_for_year_handles_archived_and_next_tenant():
    dashboard = DashboardTab.__new__(DashboardTab)

    records = [
        {
            "tenant_name": "Alice",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-03-15T00:00:00",
            "is_archived": 1,
        },
        {
            "tenant_name": "Bob",
            "created_at": "2025-04-01T00:00:00",
            "updated_at": "2025-04-01T00:00:00",
            "is_archived": 0,
        },
    ]

    lookup = dashboard._build_tenant_lookup_for_year(2025, records)

    assert lookup[1] == "Alice"
    assert lookup[2] == "Alice"
    assert lookup[3] == "Alice"
    assert lookup[4] == "Bob"
    assert lookup[12] == "Bob"


def test_room_tooltips_use_precomputed_tenant_lookup_without_db_queries():
    dashboard = DashboardTab.__new__(DashboardTab)
    dashboard.db_manager = _FakeDbManager({})
    dashboard._tenant_for_month = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError(
            "_tenant_for_month should not be called when tenant lookup is provided"
        )
    )

    tooltips = dashboard._build_owner_room_tooltips(
        raw_values=[100.0, 120.0] + [None] * 10,
        year=2025,
        room_name="Room 101",
        mode="Room",
        tenant_lookup={1: "Alice", 2: "Bob"},
    )

    assert "Tenant: Alice" in tooltips[0]
    assert "Tenant: Bob" in tooltips[1]


def test_get_rental_records_for_room_uses_candidate_fallbacks_once_per_candidate():
    dashboard = DashboardTab.__new__(DashboardTab)
    dashboard.db_manager = _FakeDbManager(
        {
            "101": [
                {
                    "tenant_name": "Alice",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00",
                    "is_archived": 0,
                }
            ]
        }
    )

    records = dashboard._get_rental_records_for_room("Room 101")

    assert len(records) == 1
    assert dashboard.db_manager.calls == ["Room 101", "101"]
