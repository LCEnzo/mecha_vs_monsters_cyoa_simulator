import pytest

from mvm.core import AttackType
from mvm.sim_interface import BattleSimulator
from tests.utils import create_combatant


def test_battle_simulation_benchmark(benchmark):
    # Setup common test data
    c = create_combatant(50, 50, 10, 10, 10)
    simulator = BattleSimulator(main_a=c.model_copy(deep=True), main_b=c.model_copy(deep=True))

    # Benchmark the battle simulation
    def run_battle():
        simulator.run_battle()

    benchmark(run_battle)


def test_multiple_battles_benchmark(benchmark):
    c = create_combatant(50, 50, 10, 10, 10)
    simulator = BattleSimulator(main_a=c.model_copy(deep=True), main_b=c.model_copy(deep=True))

    def run_multiple():
        simulator.run_multiple_battles(20)

    benchmark(run_multiple)


def test_damage_calculation_benchmark(benchmark):
    c = create_combatant(1000_000, 1000_000)

    def apply_damages():
        for _ in range(100):
            c.apply_damage(30, AttackType.BALLISTIC)
            c.apply_damage(30, AttackType.CHEMICAL)
            c.apply_damage(30, AttackType.FIREPOWER)

    benchmark(apply_damages)


@pytest.mark.parametrize("combatant_count", [1, 10, 100])
def test_state_save_benchmark(benchmark, combatant_count):
    """Test how state saving scales with different numbers of combatants"""
    combatants = [create_combatant(50, 50, 10, 10, 10) for _ in range(combatant_count)]
    simulator = BattleSimulator(
        main_a=combatants[0],
        main_b=combatants[1] if len(combatants) > 1 else combatants[0].model_copy(deep=True),
        adds_a=combatants[2 : combatant_count // 2] if combatant_count > 2 else [],
        adds_b=combatants[combatant_count // 2 :] if combatant_count > 2 else [],
    )

    def save_state():
        assert simulator.current_state is not None
        simulator.current_state.save_state()

    simulator.start_battle()

    benchmark(save_state)


@pytest.mark.parametrize("combatant_count", [1, 10, 100])
def test_state_save_after_battle_benchmark(benchmark, combatant_count):
    """Test how state saving scales with different numbers of combatants"""
    combatants = [create_combatant(50, 50, 10, 10, 10) for _ in range(combatant_count)]
    simulator = BattleSimulator(
        main_a=combatants[0],
        main_b=combatants[1] if len(combatants) > 1 else combatants[0].model_copy(deep=True),
        adds_a=combatants[2 : combatant_count // 2] if combatant_count > 2 else [],
        adds_b=combatants[combatant_count // 2 :] if combatant_count > 2 else [],
    )

    def save_state():
        assert simulator.current_state is not None
        simulator.current_state.save_state()

    simulator.run_battle()

    benchmark(save_state)
