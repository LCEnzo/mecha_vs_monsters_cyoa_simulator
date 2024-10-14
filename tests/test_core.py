import pytest

from mvm.core import TurnStart
from mvm.sim_interface import BattleSimulator, Combatant
from tests.utils import create_combatant


@pytest.mark.timeout(3, method="thread")
def test_can_do_battle_without_terrain() -> None:
    c: Combatant = create_combatant(50, 50, 10, 10, 10)
    simulator = BattleSimulator(main_a=c.model_copy(deep=True), main_b=c.model_copy(deep=True))
    simulator.run_battle()

    round_count = simulator.get_round_count()

    assert simulator.is_battle_over()
    assert simulator.current_state is not None
    assert round_count is not None
    assert round_count != 1
    assert (simulator.current_state.combatant_a.armor == 0 and simulator.current_state.combatant_a.shields == 0) or (
        simulator.current_state.combatant_b.armor == 0 and simulator.current_state.combatant_b.shields == 0
    )


@pytest.mark.timeout(60, method="thread")
def test_can_repeat_battle_alot() -> None:
    c = create_combatant(50, 50, 10, 10, 10)
    simulator = BattleSimulator(main_a=c.model_copy(deep=True), main_b=c.model_copy(deep=True))
    target_battle_count = 60

    res, avg_round_count = simulator.run_multiple_battles(target_battle_count)

    assert sum([int(val) for val in res.values()]) == target_battle_count  # type: ignore

def test_velocity_roll():
    """Tests velocity roll and turn order"""
    fast = create_combatant(100, 50, 20, 20, 20, 1000)
    slow = create_combatant(100, 50, 20, 20, 20, 0)
    simulator = BattleSimulator(main_a=fast, main_b=slow)
    for _ in range(100):
        simulator.start_battle()
        simulator.run_round(until=TurnStart)
        # The fast combatant should almost always attack first
        assert simulator.current_state.a_is_attacking
