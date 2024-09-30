from mvm.core import BattleSimulator, CombatEngine
from tests.utils import create_combatant


def test_can_do_battle_without_terrain() -> None:
    c = create_combatant(50, 50, 10, 10, 10)
    engine = CombatEngine(combatant_a=c, combatant_b=c.model_copy(deep=True))
    engine.start_battle()

    assert engine.is_battle_over()
    assert engine.current_round != 1
    assert (engine.combatant_a.armor == 0 and engine.combatant_a.shields == 0) or (
        engine.combatant_b.armor == 0 and engine.combatant_b.shields == 0
    )


def test_can_repeat_battle_alot() -> None:
    c = create_combatant(50, 50, 10, 10, 10)
    engine = CombatEngine(combatant_a=c.model_copy(deep=True), combatant_b=c.model_copy(deep=True))
    simulator = BattleSimulator(
        combat_engine=engine, combatant_a=c.model_copy(deep=True), combatant_b=c.model_copy(deep=True)
    )
    target_round_count = 250

    res, avg_round_count = simulator.run_multiple_battles(target_round_count)

    assert sum([int(val) for val in res.values()]) == target_round_count
