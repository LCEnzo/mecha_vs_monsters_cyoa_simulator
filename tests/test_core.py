import pytest

from mvm.core import Effect, SignalType, Terrain, TurnStart
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
    fast = create_combatant(100, 50, 20, 20, 20, 1000, name="Fast")
    slow = create_combatant(100, 50, 20, 20, 20, 0, name="Slow")
    simulator = BattleSimulator(main_a=fast, main_b=slow)
    for _ in range(100):
        simulator.start_battle()
        simulator.run_round(until=TurnStart)

        assert isinstance(simulator.current_state, TurnStart)
        # The fast combatant should almost always attack first
        assert simulator.current_state.a_is_attacking


def test_effect_triggering():
    def test_effect(effect, state, signal, effect_from_a):
        if effect_from_a:
            state.combatant_a.firepower += 10

    effect = Effect(
        name="Power Up",
        trigger_condition=lambda e, s, sig, a: sig.type == SignalType.ROUND_START,
        effect_func=test_effect,
    )
    combatant = create_combatant(100, 50, 20, 20, 20, 10, name="Powered")
    combatant.effects.append(effect)
    simulator = BattleSimulator(main_a=combatant, main_b=create_combatant(100, 50, 20, 20, 20, 10, name="Normal"))

    simulator.start_battle()
    simulator.run_round()

    assert simulator.current_state is not None
    assert simulator.current_state.combatant_a.firepower == 30


def test_terrain_effects():
    def terrain_effect(terrain, state, signal):
        state.combatant_a.velocity -= 5
        state.combatant_a.velocity = max(state.combatant_a.velocity, 0)
        state.combatant_b.velocity -= 5
        state.combatant_b.velocity = max(state.combatant_b.velocity, 0)

    terrain = Terrain(
        name="Swamp",
        description="Decreases velocity",
        effect=terrain_effect,
        condition=lambda t, s, sig: sig.type == SignalType.ROUND_START,
    )
    combatant_a = create_combatant(100, 50, 20, 20, 20, 10)
    combatant_b = create_combatant(100, 50, 20, 20, 20, 10)
    simulator = BattleSimulator(main_a=combatant_a, main_b=combatant_b, terrain=terrain)

    simulator.start_battle()
    simulator.run_round()

    assert simulator.current_state.combatant_a.velocity == 5
    assert simulator.current_state.combatant_b.velocity == 5
