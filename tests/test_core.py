from pprint import pprint

import pytest

from mvm.combatants import shinigami, suit
from mvm.core import Effect, End, SignalType, Start, Terrain, TurnStart
from mvm.sim_interface import BattleSimulator, Combatant
from mvm.terrains import badaxsan, lake_tampua
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


@pytest.mark.timeout(2, method="thread")
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

    assert simulator.current_state is not None
    assert simulator.current_state.combatant_a.velocity == 5
    assert simulator.current_state.combatant_b.velocity == 5


def test_battle_determinism():
    """Test that battles with same seed produce identical results"""
    seeds = [0, 420, 1453, 10000, 41635158]
    terrains = [None, lake_tampua, badaxsan]

    c = create_combatant(500, 500, 10, 10, 10, 250)

    # fmt: off
    combatant_pair_list: list[tuple[Combatant, Combatant]] = [
        (suit, suit),
        (suit, shinigami),
        (c, c)
    ]
    # fmt: on

    battle_count = 0

    for seed in seeds:
        for terrain in terrains:
            for cpair in combatant_pair_list:
                for _loop_count in range(5):
                    # fmt: off
                    sim1 = BattleSimulator(
                        main_a=cpair[0], 
                        main_b=cpair[1],
                        terrain=terrain,
                        random_seed=seed
                    )
                    # fmt: on
                    sim1.run_battle()
                    assert sim1.current_state is not None
                    states1 = sim1.current_state.saved_states
                    result1 = (
                        sim1.current_state.combatant_a.armor,
                        sim1.current_state.combatant_a.shields,
                        sim1.current_state.combatant_b.armor,
                        sim1.current_state.combatant_b.shields,
                    )

                    # fmt: off
                    sim2 = BattleSimulator(
                        main_a=cpair[0], 
                        main_b=cpair[1],
                        terrain=terrain,
                        random_seed=seed
                    )
                    # fmt: on
                    sim2.run_battle()
                    assert sim2.current_state is not None
                    states2 = sim2.current_state.saved_states
                    result2 = (
                        sim2.current_state.combatant_a.armor,
                        sim2.current_state.combatant_a.shields,
                        sim2.current_state.combatant_b.armor,
                        sim2.current_state.combatant_b.shields,
                    )

                    battle_count += 1

                    # Verify results match
                    if result1 != result2:
                        print(f"{battle_count = }\n")
                        pprint(sim1)
                        pprint(result1)
                        print("")
                        pprint(sim2)
                        pprint(result2)
                        print("")

                    assert result1 == result2
                    assert len(states1) == len(states2)

                    # Verify each state transition matched
                    for state1, state2 in zip(states1, states2):
                        assert state1.__class__ == state2.__class__
                        assert state1.combatant_a.armor == state2.combatant_a.armor
                        assert state1.combatant_b.armor == state2.combatant_b.armor
                        assert state1.combatant_a.shields == state2.combatant_a.shields
                        assert state1.combatant_b.shields == state2.combatant_b.shields

    print(f"{battle_count = }")


def test_replay_from_saved_state():
    c = create_combatant(500, 500, 10, 10, 10, 250)
    seed = 42
    simulator = BattleSimulator(main_a=c, main_b=c, random_seed=seed)

    simulator.run_battle()
    assert simulator.current_state is not None

    saved_states = simulator.current_state.saved_states

    initial_state = next(state for state in saved_states if isinstance(state, Start))
    final_state = next(state for state in reversed(saved_states) if isinstance(state, End))

    replay_simulator = BattleSimulator(
        main_a=initial_state.main_a,
        main_b=initial_state.main_b,
        terrain=initial_state.terrain,
        random_seed=initial_state.random_seed,
    )

    replay_simulator.run_battle()

    # Check battle ended correctly, that we're in the correct state
    assert replay_simulator.current_state is not None
    assert isinstance(replay_simulator.current_state, End)

    # Check results
    assert replay_simulator.current_state.round_count == final_state.round_count
    assert replay_simulator.current_state.combatant_a.armor == final_state.combatant_a.armor
    assert replay_simulator.current_state.combatant_a.shields == final_state.combatant_a.shields
    assert replay_simulator.current_state.combatant_b.armor == final_state.combatant_b.armor
    assert replay_simulator.current_state.combatant_b.shields == final_state.combatant_b.shields

    # Compare all saved states
    replay_saved_states = replay_simulator.current_state.saved_states
    assert len(replay_saved_states) == len(saved_states)

    for original_state, replay_state in zip(saved_states, replay_saved_states):
        assert type(original_state) is type(replay_state)
        assert original_state.round_count == replay_state.round_count
        assert original_state.combatant_a.armor == replay_state.combatant_a.armor
        assert original_state.combatant_a.shields == replay_state.combatant_a.shields
        assert original_state.combatant_b.armor == replay_state.combatant_b.armor
        assert original_state.combatant_b.shields == replay_state.combatant_b.shields
