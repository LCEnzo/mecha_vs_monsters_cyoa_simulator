from mvm.core import CombatEngine
from tests.utils import create_combatant


def test_can_do_battle_without_terrain():
    c = create_combatant(50, 50, 10, 10, 10)
    engine = CombatEngine(combatant_a=c, combatant_b=c.model_copy())
    engine.start_battle()

    assert engine.is_battle_over()
    assert engine.current_round != 1
    assert (engine.combatant_a.armor == 0 and engine.combatant_a.shields == 0) or (
        engine.combatant_b.armor == 0 and engine.combatant_b.shields == 0
    )
