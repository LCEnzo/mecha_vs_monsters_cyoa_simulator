#! python

from typing import Generic, TypeVar

from pydantic import BaseModel

from mvm.combatants import combatants
from mvm.sim_interface import BattleConfig, BattleSimulator, Combatant, Terrain
from mvm.terrains import terrains
from utils.log_util import logger
from utils.settings import settings  # noqa: F401

T = TypeVar("T", bound=BaseModel)


class NamedItem(BaseModel, Generic[T]):
    name: str
    item: T


def select_from_list(items: dict[str, T], item_type: str) -> T:
    named_items: list[NamedItem] = [NamedItem(name=name, item=item) for name, item in items.items()]

    print(f"\nAvailable {item_type}s:")
    for i, item in enumerate(named_items):
        print(f"{i+1}. {item.name}")

    while True:
        choice = input(f"\nSelect a {item_type} (enter name or number): ").strip()
        if choice in items:
            return items[choice]
        elif choice.isdigit() and 1 <= int(choice) <= len(named_items):
            return named_items[int(choice) - 1].item
        else:
            print("Invalid selection. Please try again.")


def run_config_battles(battle_config: BattleConfig, simulator: BattleSimulator) -> None:
    for battle in battle_config.battles:
        combatant_a = combatants[battle.combatant_a]
        combatant_b = combatants[battle.combatant_b]
        terrain = terrains[battle.terrain]

        simulator.load_combatants(combatant_a, combatant_b)
        simulator.load_terrain(terrain)

        logger.info(f"Starting {battle.name}")
        simulator.run_battle()
        print("")


def main() -> None:
    battle_config = BattleConfig.load_battle_config("tomls/battle_config.toml")
    simulator = BattleSimulator(
        main_a=battle_config.battles[0].combatant_a, main_b=battle_config.battles[0].combatant_b
    )

    if battle_config.battles:
        run_config_battles(battle_config, simulator)

    while True:
        print("\n--- Mecha vs Monster Battle Simulator ---")
        print("1. Load combatants")
        print("2. Load terrain")
        print("3. View combatants")
        print("4. /")
        print("5. Modify combatant")
        print("6. Start battle")
        print("7. Simulate round")
        print("8. Get battle result")
        print("9. Run multiple battles")
        print("10. Exit")

        choice = input("Enter your choice: ").strip()
        print("")

        if choice == "1":
            combatant_a: Combatant = select_from_list(combatants, "combatant")
            combatant_b: Combatant = select_from_list(combatants, "combatant")
            simulator.load_combatants(combatant_a, combatant_b)
        elif choice == "2":
            terrain: Terrain = select_from_list(terrains, "terrain")
            simulator.load_terrain(terrain)
        elif choice == "3":
            simulator.view_combatants_and_terrain()
        elif choice == "5":
            side = input("Which combatant to modify? (A/B): ")
            attribute = input("Enter attribute to modify: ")
            new_value = int(input(f"Enter new value for {attribute}: "))
            print(simulator.modify_combatant(side, attribute, new_value))
        elif choice == "6":
            simulator.start_battle()
        elif choice == "7":
            simulator.run_round()
        elif choice == "8":
            print(simulator.get_battle_result())
        elif choice == "9":
            num_battles = int(input("Enter the number of battles to simulate: "))
            simulator.run_multiple_battles(num_battles)
        elif choice == "10":
            print("Exiting the Battle Simulator. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
    print("")
