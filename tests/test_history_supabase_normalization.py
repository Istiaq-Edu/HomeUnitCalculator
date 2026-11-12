from src.ui.tabs.history_tab import HistoryTab


class _FakeSupabaseManager:
    def __init__(self, grouped_rooms):
        self.grouped_rooms = grouped_rooms
        self.calls = []

    def get_room_calculations_bulk(self, ids):
        self.calls.append(list(ids))
        return self.grouped_rooms


def test_coerce_json_dict_handles_dict_string_and_invalid_json():
    history = HistoryTab.__new__(HistoryTab)

    assert history._coerce_json_dict({"a": 1}) == {"a": 1}
    assert history._coerce_json_dict('{"a": 2}') == {"a": 2}
    assert history._coerce_json_dict("{bad json") == {}
    assert history._coerce_json_dict([1, 2, 3]) == {}


def test_prepare_supabase_history_records_normalizes_main_and_room_payloads():
    history = HistoryTab.__new__(HistoryTab)
    history.main_window = type("MainWindow", (), {})()
    history.main_window.supabase_manager = _FakeSupabaseManager(
        {
            "1": [
                {
                    "id": 10,
                    "room_data": '{"room_name": "Room 101", "unit_bill": 123.45}',
                }
            ],
            "2": [
                {
                    "id": 20,
                    "room_data": "{bad json",
                }
            ],
        }
    )
    main_calculations = [
        {
            "id": 1,
            "month": "January",
            "year": 2025,
            "main_data": '{"grand_total": 1000}',
        },
        {
            "id": 2,
            "month": "February",
            "year": 2025,
            "main_data": {"grand_total": 2000},
        },
    ]

    records_with_rooms, all_room_rows = history._prepare_supabase_history_records(
        main_calculations
    )

    assert history.main_window.supabase_manager.calls == [[1, 2]]
    assert records_with_rooms[0]["main_calc"]["main_data"] == {"grand_total": 1000}
    assert records_with_rooms[1]["main_calc"]["main_data"] == {"grand_total": 2000}
    assert (
        records_with_rooms[0]["room_records"][0]["room_data"]["room_name"] == "Room 101"
    )
    assert records_with_rooms[0]["room_records"][0]["month"] == "January"
    assert records_with_rooms[1]["room_records"][0]["room_data"] == {}
    assert all_room_rows[1]["year"] == 2025
