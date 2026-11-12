"""Regression tests for removing a room from the middle of Room Calculations."""

import types
from unittest.mock import MagicMock

import pytest
from PyQt5.QtWidgets import QComboBox

from src.ui.tabs.main_tab import MainTab


@pytest.fixture
def main_tab(qapp):
    window = types.SimpleNamespace()
    window.load_info_source_combo = QComboBox()
    window.save_to_pdf = MagicMock()
    window.save_calculation_to_csv = MagicMock()
    window.save_calculation_to_supabase = MagicMock()
    return MainTab(window)


def _titles(tab):
    return [tab._room_title(room).text() for room in tab.room_entries]


def _fill(tab):
    for i, room in enumerate(tab.room_entries):
        room['present_entry'].setText(str(100 + i))
        room['previous_entry'].setText(str(i))
        room['gas_bill_entry'].setText(str(10 + i))
        room['water_bill_entry'].setText(str(20 + i))
        room['house_rent_entry'].setText(str(1000 + i))
        room['unit_bill_label'].setText(f"{i} TK")


def test_remove_middle_room_renumbers_and_keeps_other_data(main_tab):
    _fill(main_tab)
    main_tab.remove_room(9, notify=False)  # delete Room 10 out of 11

    assert len(main_tab.room_entries) == 10
    assert main_tab.num_rooms_spinbox.value() == 10
    assert main_tab.rooms_scroll_layout.count() == 10
    assert _titles(main_tab) == [f"Room {i}" for i in range(1, 11)]

    # Rooms 1-9 keep their values; old Room 11 becomes Room 10 with its own values.
    assert main_tab.room_entries[0]['present_entry'].text() == '100'
    assert main_tab.room_entries[8]['present_entry'].text() == '108'
    assert main_tab.room_entries[9]['present_entry'].text() == '110'
    assert main_tab.room_entries[9]['house_rent_entry'].text() == '1010'
    assert main_tab.room_entries[9]['unit_bill_label'].text() == '10 TK'
    assert main_tab.room_entries[9]['present_entry'].objectName() == 'room_9_present'

    # Totals are computed from the surviving rooms only.
    assert main_tab.get_all_room_bill_totals()['total_house_rent'] == sum(
        float(r['house_rent_entry'].text() or 0) for r in main_tab.room_entries
    )


def test_remove_menu_and_card_button_list_current_rooms(main_tab, qapp):
    assert [a.text() for a in main_tab.remove_room_menu.actions()] == [
        f"Room {i}" for i in range(1, 12)
    ]

    main_tab.room_entries[9]['remove_button'].click()
    assert len(main_tab.room_entries) == 10
    assert [a.text() for a in main_tab.remove_room_menu.actions()] == [
        f"Room {i}" for i in range(1, 11)
    ]

    main_tab.remove_room_menu.actions()[2].trigger()  # remove Room 3
    qapp.processEvents()  # menu actions defer the rebuild to the event loop
    assert len(main_tab.room_entries) == 9
    assert main_tab.num_rooms_spinbox.value() == 9


def test_undo_restores_room_in_original_position(main_tab):
    _fill(main_tab)
    main_tab.remove_room(9, notify=False)
    main_tab._undo_remove_room()

    assert len(main_tab.room_entries) == 11
    assert main_tab.num_rooms_spinbox.value() == 11
    assert _titles(main_tab) == [f"Room {i}" for i in range(1, 12)]
    assert main_tab.room_entries[9]['present_entry'].text() == '109'
    assert main_tab.room_entries[10]['present_entry'].text() == '110'


def test_undo_survives_a_recalculation(main_tab):
    for i, room in enumerate(main_tab.room_entries):
        room['present_entry'].setText(str(100 + i))
        room['previous_entry'].setText(str(50 + i))
        room['house_rent_entry'].setText('1000')
    main_tab.per_unit_cost_value_label.setText('Per Unit Cost: 5 TK')
    main_tab.calculate_rooms()

    main_tab.remove_room(9, notify=False)
    main_tab.per_unit_cost_value_label.setText('Per Unit Cost: 9 TK')
    main_tab.calculate_rooms()

    main_tab._undo_remove_room()
    assert len(main_tab.room_entries) == 11
    # The recalculated totals on the surviving rooms must not be rolled back.
    assert main_tab.room_entries[0]['unit_bill_label'].text() == '450 TK'


def test_loading_or_clearing_retires_pending_undo(main_tab):
    main_tab.remove_room(9, notify=False)
    assert main_tab._pending_room_undo is not None

    main_tab.clear_room_inputs()
    assert main_tab._pending_room_undo is None

    main_tab.remove_room(4, notify=False)
    main_tab.num_rooms_spinbox.setValue(12)  # user-driven count change
    assert main_tab._pending_room_undo is None

    main_tab.remove_room(4, notify=False)
    main_tab.load_room_data_from_supabase_rows([])
    assert main_tab._pending_room_undo is None
    main_tab._undo_remove_room()
    assert len(main_tab.room_entries) == 1


def test_clear_room_inputs_drops_custom_names_and_cloud_ids(main_tab):
    main_tab._room_title(main_tab.room_entries[0]).setText('Flat C')
    main_tab.room_entries[0]['supabase_id'] = 4242

    main_tab.clear_room_inputs()

    assert _titles(main_tab)[0] == 'Room 1'
    assert 'supabase_id' not in main_tab.room_entries[0]


def test_stale_or_invalid_undo_is_rejected(main_tab):
    _fill(main_tab)
    main_tab.remove_room(9, notify=False)
    first_token = main_tab._pending_room_undo[0]
    main_tab.remove_room(0, notify=False)

    count_before = len(main_tab.room_entries)
    main_tab._undo_remove_room(first_token)  # older toast must not undo the newer deletion
    assert len(main_tab.room_entries) == count_before

    main_tab.room_entries[0]['present_entry'].setText('777')  # user edited after removal
    main_tab._undo_remove_room()
    assert len(main_tab.room_entries) == count_before


def test_spinbox_change_preserves_entered_room_data(main_tab):
    _fill(main_tab)
    main_tab.num_rooms_spinbox.setValue(12)

    assert len(main_tab.room_entries) == 12
    assert main_tab.room_entries[10]['present_entry'].text() == '110'
    assert main_tab.room_entries[11]['present_entry'].text() == ''
    assert main_tab.room_entries[11]['unit_bill_label'].text() == 'N/A'


def test_custom_room_names_survive_rebuild(main_tab):
    main_tab._room_title(main_tab.room_entries[2]).setText('Flat C')
    main_tab.num_rooms_spinbox.setValue(12)

    assert _titles(main_tab)[2] == 'Flat C'
    assert _titles(main_tab)[11] == 'Room 12'


def test_loading_saved_rooms_clears_previous_calculated_totals(main_tab):
    for i, room in enumerate(main_tab.room_entries):
        room['present_entry'].setText(str(200 + i))
        room['grand_total_label'].setText(f"{500 + i} TK")

    records = [
        {
            'id': 1000 + i,
            'room_data': {
                'present_unit': '', 'previous_unit': 200 + i,
                'gas_bill': 10, 'water_bill': 20, 'house_rent': 1000,
            },
        }
        for i in range(8)
    ]
    main_tab.load_room_data_from_supabase_rows(records, auto_calculate=False)

    assert len(main_tab.room_entries) == 8
    assert main_tab.room_entries[0]['grand_total_label'].text() == 'N/A'
    assert main_tab.room_entries[0]['unit_bill_label'].text() == 'N/A'
    assert main_tab.room_entries[7]['previous_entry'].text() == '207'


def test_loading_with_no_room_records_resets_to_one_empty_room(main_tab):
    main_tab.room_entries[0]['present_entry'].setText('999')
    main_tab.room_entries[0]['grand_total_label'].setText('123 TK')

    main_tab.load_room_data_from_supabase_rows([])

    assert len(main_tab.room_entries) == 1
    assert main_tab.num_rooms_spinbox.value() == 1
    assert main_tab.room_entries[0]['present_entry'].text() == ''
    assert main_tab.room_entries[0]['grand_total_label'].text() == 'N/A'


def test_csv_row_load_clears_derived_labels(main_tab):
    main_tab.room_entries[0]['grand_total_label'].setText('999 TK')
    main_tab.load_room_data_from_csv_row(
        {'Present Unit': '120', 'Previous Unit': '100', 'Gas Bill': '10',
         'Water Bill': '20', 'House Rent': '1000'},
        0,
    )

    assert main_tab.room_entries[0]['present_entry'].text() == '120'
    assert main_tab.room_entries[0]['grand_total_label'].text() == 'N/A'


def test_decimal_values_survive_rebuild(main_tab):
    main_tab.room_entries[0]['gas_bill_entry'].setText('12.50')
    main_tab.num_rooms_spinbox.setValue(12)
    assert main_tab.room_entries[0]['gas_bill_entry'].text() == '12.50'


def test_last_room_cannot_be_removed(main_tab):
    main_tab._apply_room_data(main_tab._snapshot_room_data()[:1])
    assert len(main_tab.room_entries) == 1

    main_tab.remove_room(0, notify=False)

    assert len(main_tab.room_entries) == 1
    assert not main_tab.room_entries[0]['remove_button'].isEnabled()
    assert not main_tab.remove_room_button.isEnabled()
