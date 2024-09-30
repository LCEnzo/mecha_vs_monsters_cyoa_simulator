from unittest.mock import MagicMock, patch

import pytest

from main import main, run_config_battles, select_from_list
from mvm.core import BattleSimulator, Combatant, Terrain

# Mock data for testing
mock_combatants = {
    "Mech1": Combatant(name="Mech1", armor=100, shields=100, ballistics=50, chemical=50, firepower=50, velocity=50),
    "Mech2": Combatant(name="Mech2", armor=120, shields=80, ballistics=60, chemical=40, firepower=60, velocity=40),
}

mock_terrains = {
    "Desert": Terrain(name="Desert", description="Hot and dry", effect=lambda x: None, condition=lambda x, y: True),
    "Forest": Terrain(
        name="Forest", description="Dense vegetation", effect=lambda x: None, condition=lambda x, y: True
    ),
}


@pytest.fixture
def mock_simulator():
    simulator = MagicMock(spec=BattleSimulator)
    simulator.combatant_a = None
    simulator.combatant_b = None
    simulator.terrain = None
    return simulator


def test_select_from_list_by_number():
    with patch("builtins.input", return_value="1"):
        result = select_from_list(mock_combatants, "combatant")
    assert result.name == "Mech1"


def test_select_from_list_by_name():
    with patch("builtins.input", return_value="Mech2"):
        result = select_from_list(mock_combatants, "combatant")
    assert result.name == "Mech2"


def test_select_from_list_invalid_input():
    with patch("builtins.input", side_effect=["invalid", "2"]):
        result = select_from_list(mock_combatants, "combatant")
    assert result.name == "Mech2"


def test_run_config_battles(mock_simulator):
    mock_battle_config = MagicMock()
    mock_battle = MagicMock()
    mock_battle.name = "Test Battle"
    mock_battle.combatant_a = "Mech1"
    mock_battle.combatant_b = "Mech2"
    mock_battle.terrain = "Desert"
    mock_battle_config.battles = [mock_battle]

    with patch("main.combatants", mock_combatants), patch("main.terrains", mock_terrains):
        run_config_battles(mock_battle_config, mock_simulator)

    mock_simulator.load_combatants.assert_called_once()
    mock_simulator.load_terrain.assert_called_once()
    mock_simulator.start_battle.assert_called_once()


@pytest.mark.parametrize(
    "user_input,expected_calls",
    [
        (["1", "Mech1", "Mech2", "10"], {"load_combatants": 1}),
        (["1", "Mech1", "Mech1", "10"], {"load_combatants": 1}),
        (["2", "Desert", "10"], {"load_terrain": 1}),
        (["3", "10"], {"view_combatants_and_terrain": 1}),
        (["3", "10"], {"view_combatants_and_terrain": 1}),
        (["2", "Desert", "3", "10"], {"load_terrain": 1, "view_combatants_and_terrain": 1}),
        (["5", "A", "armor", "150", "10"], {"modify_combatant": 1}),
        (["6", "10"], {"start_battle": 1}),
        (["7", "10"], {"simulate_round": 1}),
        (["8", "10"], {"get_battle_result": 1}),
        (["9", "5", "10"], {"run_multiple_battles": 1}),
    ],
)
def test_main_menu_options(mock_simulator, user_input, expected_calls):
    with patch('builtins.input', side_effect=user_input), \
         patch('main.BattleSimulator', return_value=mock_simulator), \
         patch('main.BattleConfig.load_battle_config', return_value=MagicMock(battles=[])), \
         patch('main.combatants', mock_combatants), \
         patch('main.terrains', mock_terrains), \
         patch('builtins.print'):
        main()

    for method, count in expected_calls.items():
        if method == "terrain" and expected_calls["terrain"] != 0:
            assert getattr(mock_simulator, method) is not None
        elif method == "terrain" and expected_calls["terrain"] == 0:
            assert getattr(mock_simulator, method) is None
        else:
            assert getattr(mock_simulator, method).call_count == count


def test_main_invalid_choice():
    with patch('builtins.input', side_effect=['invalid', '10']), \
         patch('main.BattleSimulator', return_value=MagicMock()), \
         patch('main.BattleConfig.load_battle_config', return_value=MagicMock(battles=[])), \
         patch('builtins.print') as mock_print:
        main()

    mock_print.assert_any_call("Invalid choice. Please try again.")


if __name__ == "__main__":
    pytest.main()
