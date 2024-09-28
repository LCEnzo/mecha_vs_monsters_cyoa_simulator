#!python
# Mechs vs Monsters CYOA	https://docs.google.com/spreadsheets/d/1EtHtPwQyUKCrR4irR_aebse2ZSU6UZWsZOiLbhThnsY/edit?gid=0#gid=0

import enum
import logging
from pathlib import Path
from random import randint
from typing import Callable, Dict, List, Union

import tomli
import tomli_w
from pydantic import BaseModel, Field


class AttackType(str, enum.Enum):
    FIREPOWER = "Firepower"
    CHEMICAL = "Chemical"
    BALLISTIC = "Ballistics"


class Effect(BaseModel):
    name: str
    trigger_condition: str
    effect_func: str  # This will be a string representation of a function
    duration: int = -1  # -1 for permanent effects
    triggered: bool = False

    def apply(self, combatant: "Combatant") -> None:
        # In a real implementation, you'd need a safe way to evaluate the effect_func string
        # For now, we'll just print what would happen
        print(f"Applying effect {self.name} to {combatant.name}: {self.effect_func}")
        self.triggered = True


class Combatant(BaseModel):
    name: str
    armor: int
    shields: int
    ballistics: int
    chemical: int
    firepower: int
    velocity: int
    effects: list[Effect] = Field(default_factory=list)
    armor_modifiers: dict[AttackType, int] = Field(default_factory=dict)
    shield_modifiers: dict[AttackType, int] = Field(default_factory=dict)
    modifiers: dict[str, dict[str, int]] = Field(default_factory=dict)

    def apply_damage(self, damage: int, damage_type: AttackType) -> int:
        """Apply damage based on shields/armor and return the actual applied damage"""
        damage = self.modify_damage(damage, damage_type)

        if self.shields > 0:
            if damage >= self.shields:
                damage -= self.shields
                self.shields = 0
            else:
                self.shields -= damage
                damage = 0

        if damage > 0:
            self.armor = max(0, self.armor - damage)

        return damage

    def modify_damage(self, damage: int, damage_type: AttackType) -> int:
        """Apply armor/shield reductions or buffs."""
        if damage_type == AttackType.FIREPOWER:
            if self.shields > 0:
                damage *= 2
            else:
                damage = damage // 2
        elif damage_type == AttackType.CHEMICAL:
            if self.shields > 0:
                damage = damage // 2
            else:
                damage *= 2

        if self.shields > 0 and damage_type in self.shield_modifiers:
            damage += self.shield_modifiers[damage_type]
        elif self.shields == 0 and damage_type in self.armor_modifiers:
            damage += self.armor_modifiers[damage_type]

        return max(0, damage)

    def get_damage(self, damage_type: AttackType) -> int:
        return getattr(self, damage_type.value.lower())

    def is_dead(self) -> bool:
        return self.armor <= 0


class CombatEngine(BaseModel):
    combatant_a: Combatant
    combatant_b: Combatant
    current_turn: int = 1
    logger: logging.Logger = Field(default_factory=lambda: logging.getLogger(__name__))

    class Config:
        arbitrary_types_allowed = True

    def simulate_round(self) -> None:
        total_velocity_a = self.combatant_a.velocity + randint(1, 1000)
        total_velocity_b = self.combatant_b.velocity + randint(1, 1000)

        self.logger.info(
            f"{self.combatant_a.name} has total velocity {total_velocity_a} vs "
            f"{self.combatant_b.name} has {total_velocity_b}"
        )

        if total_velocity_a >= total_velocity_b:
            attacker, defender = self.combatant_a, self.combatant_b
        else:
            attacker, defender = self.combatant_b, self.combatant_a

        for attack_type in AttackType:
            self.process_turn(attacker, defender, attack_type)

        self.current_turn += 1

    def process_turn(self, attacker: Combatant, defender: Combatant, att_type: AttackType):
        # Roll for hit success based on velocity and apply damage
        hit_roll = self.calculate_hit(attacker, defender, att_type)
        if hit_roll:
            damage = self.calculate_damage(attacker, defender, att_type)
            applied_damage = defender.apply_damage(damage, att_type)
            self.logger.info(f"{attacker.name} hits {defender.name} with {att_type.value} for {applied_damage} damage")
        else:
            self.logger.info(f"{attacker.name} misses {defender.name} with {att_type.value}")

    def calculate_hit(self, attacker: Combatant, defender: Combatant, att_type: AttackType) -> bool:
        """Calculate whether an attack hits, taking into account modifiers."""
        base_hit = randint(0, 1000)
        hit_chance = (attacker.velocity - defender.velocity) // 2

        att_mod = attacker.modifiers.get("attack_hit_chance_mod", {}).get(att_type.value, 0)
        def_mod = defender.modifiers.get("defense_hit_chance_mod", {}).get(att_type.value, 0)

        hit_roll = base_hit + att_mod - def_mod >= 500 - hit_chance
        self.logger.debug(
            f"Attack ({attacker.name}) calc hit: {(base_hit, hit_chance, att_mod, def_mod) = } -> {hit_roll = }"
        )

        return hit_roll

    def calculate_damage(self, attacker: Combatant, defender: Combatant, att_type: AttackType) -> int:
        """Calculate base damage and any modifiers."""
        base_damage = attacker.get_damage(att_type)
        return base_damage

    def get_user_feedback(self) -> bool:
        """Ask if user wants to modify the result."""
        return input("Modify results? (y/n) ").strip().lower() == "y"

    def modify_round(self):
        """Allow user to modify combat results."""
        combatant = input("Which combatant to modify? (A/B) ").strip().lower()
        stat = input("Which stat? (shields/armor/firepower) ").strip().lower()
        new_value = int(input(f"New value for {stat}? "))

        if combatant == "a":
            setattr(self.combatant_a, stat, new_value)
        else:
            setattr(self.combatant_b, stat, new_value)


def load_combatant(file_path: Union[str, Path]) -> Combatant:
    with open(file_path, "rb") as f:
        data = tomli.load(f)
    return Combatant.parse_obj(data)


def save_combatant(combatant: Combatant, file_path: Union[str, Path]) -> None:
    with open(file_path, "w") as f:
        tomli_w.dump(combatant.dict(), f)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("combat.log")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class BattleSimulator:
    def __init__(self):
        self.logger = setup_logging()
        self.combatants: Dict[str, Combatant] = {}
        self.combat_engine: Union[CombatEngine, None] = None

    def run(self):
        while True:
            self.display_main_menu()
            choice = input("Enter your choice: ").strip().lower()
            if choice == '1':
                self.load_combatants()
            elif choice == '2':
                self.view_combatants()
            elif choice == '3':
                self.modify_combatant()
            elif choice == '4':
                self.start_battle()
            elif choice == '5':
                print("Exiting the Battle Simulator. Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")

    def display_main_menu(self):
        print("\n--- Mech vs Monster Battle Simulator ---")
        print("1. Load combatants")
        print("2. View combatants")
        print("3. Modify combatant")
        print("4. Start battle")
        print("5. Exit")

    def load_combatants(self):
        for side in ['a', 'b']:
            file_path = input(f"Enter the file path for combatant {side.upper()}: ").strip()
            if not file_path:
                file_path = f"combatant_{side}.toml"
            try:
                combatant = load_combatant(file_path)
                self.combatants[side] = combatant
                print(f"Loaded {combatant.name} as combatant {side.upper()}")
            except Exception as e:
                print(f"Error loading combatant {side.upper()}: {e}")

    def view_combatants(self):
        for side, combatant in self.combatants.items():
            print(f"\n--- Combatant {side.upper()}: {combatant.name} ---")
            print(f"Armor: {combatant.armor}")
            print(f"Shields: {combatant.shields}")
            print(f"Ballistics: {combatant.ballistics}")
            print(f"Chemical: {combatant.chemical}")
            print(f"Firepower: {combatant.firepower}")
            print(f"Velocity: {combatant.velocity}")
            print("Effects:")
            for effect in combatant.effects:
                print(f"  - {effect.name}")

    def modify_combatant(self):
        side = input("Which combatant to modify? (A/B): ").strip().lower()
        if side not in self.combatants:
            print(f"Combatant {side.upper()} not loaded.")
            return

        combatant = self.combatants[side]
        print(f"\nModifying {combatant.name}")
        attribute = input("Enter attribute to modify (armor/shields/ballistics/chemical/firepower/velocity): ").strip().lower()
        if attribute not in ['armor', 'shields', 'ballistics', 'chemical', 'firepower', 'velocity']:
            print("Invalid attribute.")
            return

        try:
            new_value = int(input(f"Enter new value for {attribute}: "))
            setattr(combatant, attribute, new_value)
            print(f"Updated {attribute} to {new_value} for {combatant.name}")
        except ValueError:
            print("Invalid input. Please enter a number.")

    def start_battle(self):
        if len(self.combatants) != 2:
            print("Please load both combatants before starting a battle.")
            return

        self.combat_engine = CombatEngine(
            combatant_a=self.combatants['a'],
            combatant_b=self.combatants['b'],
            logger=self.logger
        )

        round_number = 1
        while not self.combatants['a'].is_dead() and not self.combatants['b'].is_dead():
            print(f"\n--- Round {round_number} ---")
            self.combat_engine.simulate_round()
            self.display_battle_status()
            
            if self.get_user_feedback():
                self.modify_round()
            
            round_number += 1

        winner = self.combatants['b'] if self.combatants['a'].is_dead() else self.combatants['a']
        print(f"\nBattle ended. Winner: {winner.name}")

    def display_battle_status(self):
        for side, combatant in self.combatants.items():
            print(f"{combatant.name} - Armor: {combatant.armor}, Shields: {combatant.shields}")

    def get_user_feedback(self) -> bool:
        return input("Modify results? (y/n) ").strip().lower() == "y"

    def modify_round(self):
        self.modify_combatant()

if __name__ == "__main__":
    simulator = BattleSimulator()
    simulator.run()
    print("Exiting")
