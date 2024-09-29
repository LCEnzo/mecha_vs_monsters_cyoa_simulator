#!python

from combat_logging import logger
from combatants import combatants
from core import BattleConfig, BattleSimulator
from terrains import terrains


def run_config_battles(battle_config: BattleConfig, simulator: BattleSimulator):
    for battle in battle_config.battles:
        combatant_a = combatants[battle.combatant_a]
        combatant_b = combatants[battle.combatant_b]
        terrain = terrains[battle.terrain]

        simulator.load_combatants(combatant_a, combatant_b)
        simulator.load_terrain(terrain)

        logger.info(f"Starting {battle.name}")
        simulator.start_battle()
        print("")


def main():
    simulator = BattleSimulator()
    battle_config = BattleConfig.load_battle_config("battle_config.toml")

    if battle_config.battles:
        run_config_battles(battle_config, simulator)

    # file_a = "combatant_a.toml"
    # file_b = "combatant_b.toml"
    # terrain_file = "terrain.toml"
    # simulator.load_combatants_via_file(file_a, file_b)
    # simulator.load_terrain_via_file(terrain_file)

    while True:
        print("\n--- Mech vs Monster Battle Simulator ---")
        print("1. Load combatants")
        print("2. Load terrain")
        print("3. View combatants")
        print("4. View terrain")
        print("5. Modify combatant")
        print("6. Start battle")
        print("7. Simulate round")
        print("8. Get battle result")
        print("9. Run multiple battles")
        print("10. Exit")

        choice = input("Enter your choice: ").strip()
        print("")

        if choice == "1":
            file_a = input("Enter file path for combatant A: ")
            if not file_a:
                file_a = "combatant_a.toml"
            file_b = input("Enter file path for combatant B: ")
            if not file_b:
                file_b = "combatant_b.toml"
            simulator.load_combatants_via_file(file_a, file_b)
        elif choice == "2":
            terrain_file = input("Enter file path for terrain: ")
            if not terrain_file:
                terrain_file = "terrain.toml"
            simulator.load_terrain_via_file(terrain_file)
        elif choice == "3":
            simulator.view_combatants()
        elif choice == "4":
            if simulator.terrain:
                print(f"Terrain: {simulator.terrain.name}")
                print(f"Description: {simulator.terrain.description}")
            else:
                print("No terrain loaded.")
        elif choice == "5":
            side = input("Which combatant to modify? (A/B): ")
            attribute = input("Enter attribute to modify: ")
            new_value = int(input(f"Enter new value for {attribute}: "))
            print(simulator.modify_combatant(side, attribute, new_value))
        elif choice == "6":
            simulator.start_battle()
        elif choice == "7":
            simulator.simulate_round()
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
