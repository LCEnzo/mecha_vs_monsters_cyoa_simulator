from mvm.sim_interface import BattleSimulator
from tests.utils import create_combatant


def test_can_do_battle_without_terrain() -> None:
    c = create_combatant(50, 50, 10, 10, 10)
    simulator = BattleSimulator(main_a=c.model_copy(deep=True), main_b=c.model_copy(deep=True))
    simulator.run_battle()

    round_count = simulator.get_round_count()

    assert simulator.is_battle_over()
    assert round_count is not None
    assert round_count != 1
    assert (simulator.combatant_a.armor == 0 and simulator.combatant_a.shields == 0) or (
        simulator.combatant_b.armor == 0 and simulator.combatant_b.shields == 0
    )


def test_can_repeat_battle_alot() -> None:
    c = create_combatant(50, 50, 10, 10, 10)
    simulator = BattleSimulator(main_a=c.model_copy(deep=True), main_b=c.model_copy(deep=True))
    target_round_count = 250

    res, avg_round_count = simulator.run_multiple_battles(target_round_count)

    assert sum([int(val) for val in res.values()]) == target_round_count
