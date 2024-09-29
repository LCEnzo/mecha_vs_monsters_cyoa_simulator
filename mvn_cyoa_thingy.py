#!python
# Mechs vs Monsters CYOA	https://docs.google.com/spreadsheets/d/1EtHtPwQyUKCrR4irR_aebse2ZSU6UZWsZOiLbhThnsY/edit?gid=0#gid=0

import enum
import logging
import traceback
from pathlib import Path
from random import randint
from typing import Union

import tomli
import tomli_w
from pydantic import BaseModel, Field


## LOGGING SETUP
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


logger = setup_logging()

## NORMAL CODE


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
    trigger_count: int = 0

    def apply(self, combatant: "Combatant") -> None:
        try:
            if eval(self.trigger_condition):
                eval(f"combatant.{self.effect_func}")
                self.triggered = True
                self.trigger_count += 1
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Effect {self.name} borked, exception {e}")


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
            self.shields = max(0, self.shields - damage)
        else:
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
    current_round: int = 1

    class Config:
        arbitrary_types_allowed = True

    def simulate_round(self) -> None:
        total_velocity_a = self.combatant_a.velocity + randint(1, 1000)
        total_velocity_b = self.combatant_b.velocity + randint(1, 1000)

        logger.info(
            f"Round {self.current_round}: {self.combatant_a.name} has total velocity {total_velocity_a} vs "
            f"{self.combatant_b.name} has {total_velocity_b}"
        )

        if total_velocity_a >= total_velocity_b:
            first, second = (self.combatant_a, self.combatant_b)
        else:
            first, second = (self.combatant_b, self.combatant_a)

        self.process_turn(first, second)
        if not second.is_dead():
            self.process_turn(second, first)

        self.current_round += 1

    def process_turn(self, attacker: Combatant, defender: Combatant):
        for attack_type in AttackType:
            if defender.is_dead():
                break
            self.process_attack(attacker, defender, attack_type)

    def process_attack(self, attacker: Combatant, defender: Combatant, att_type: AttackType):
        hit_roll = self.calculate_hit(attacker, defender, att_type)
        if hit_roll:
            damage = self.calculate_damage(attacker, defender, att_type)
            applied_damage = defender.apply_damage(damage, att_type)
            logger.info(f"{attacker.name} hits {defender.name} with {att_type.value} for {applied_damage} damage")
        else:
            logger.info(f"{attacker.name} misses {defender.name} with {att_type.value}")

    def calculate_hit(self, attacker: Combatant, defender: Combatant, att_type: AttackType) -> bool:
        """Calculate whether an attack hits, taking into account modifiers."""
        base_hit = randint(0, 1000)
        hit_chance = (attacker.velocity - defender.velocity) // 2

        att_mod = attacker.modifiers.get("attack_hit_chance_mod", {}).get(att_type.value, 0)
        def_mod = defender.modifiers.get("defense_hit_chance_mod", {}).get(att_type.value, 0)

        hit_roll = base_hit + att_mod - def_mod >= 500 - hit_chance
        logger.debug(
            f"Attack ({attacker.name}) calc hit: {(base_hit, hit_chance, att_mod, def_mod) = } -> {hit_roll = }"
        )

        return hit_roll

    def calculate_damage(self, attacker: Combatant, defender: Combatant, att_type: AttackType) -> int:
        return attacker.get_damage(att_type)

    def get_battle_status(self) -> str:
        return (
            f"{self.combatant_a.name} - Armor: {self.combatant_a.armor}, Shields: {self.combatant_a.shields}\n"
            f"{self.combatant_b.name} - Armor: {self.combatant_b.armor}, Shields: {self.combatant_b.shields}"
        )


class BattleSimulator(BaseModel):
    combatant_a: Combatant | None = None
    combatant_b: Combatant | None = None
    combat_engine: CombatEngine | None = None

    def load_combatants(self, file_path_a: str, file_path_b: str):
        try:
            self.combatant_a = load_combatant(file_path_a)
            self.combatant_b = load_combatant(file_path_b)
            logger.info(f"Loaded {self.combatant_a.name} as combatant A")
            logger.info(f"Loaded {self.combatant_b.name} as combatant B")
        except Exception as e:
            logger.error(f"Error loading combatants: {e}")

    def view_combatants(self):
        if not self.combatant_a or not self.combatant_b:
            print("Please load both combatants first.")
            return

        print(
            f"--- Combatant A: {self.combatant_a.name} ---\n"
            f"{self._format_combatant_stats(self.combatant_a)}\n\n"
            f"--- Combatant B: {self.combatant_b.name} ---\n"
            f"{self._format_combatant_stats(self.combatant_b)}"
        )

    def _format_combatant_stats(self, combatant: Combatant) -> str:
        return (
            f"Armor: {combatant.armor}\n"
            f"Shields: {combatant.shields}\n"
            f"Ballistics: {combatant.ballistics}\n"
            f"Chemical: {combatant.chemical}\n"
            f"Firepower: {combatant.firepower}\n"
            f"Velocity: {combatant.velocity}\n"
            f"Effects: {', '.join(effect.name for effect in combatant.effects)}"
        )

    def modify_combatant(self, side: str, attribute: str, new_value: int):
        combatant = self.combatant_a if side.lower() == "a" else self.combatant_b
        if not combatant:
            logger.warning(f"Combatant {side.upper()} not loaded.")

        if attribute not in ["armor", "shields", "ballistics", "chemical", "firepower", "velocity"]:
            logger.warning("Invalid attribute.")

        setattr(combatant, attribute, new_value)
        logger.info(f"Updated {attribute} to {new_value} for {combatant.name}")

    def start_battle(self):
        if not self.combatant_a or not self.combatant_b:
            logger.warning("Please load both combatants before starting a battle.")

        self.combat_engine = CombatEngine(
            combatant_a=self.combatant_a, combatant_b=self.combatant_b, logger=logger
        )
        logger.info("Battle started. Use 'simulate_round' to progress the battle.")

    def simulate_round(self):
        if not self.combat_engine:
            logger.warning("Please start the battle first.")

        self.combat_engine.simulate_round()
        logger.info(self.combat_engine.get_battle_status())

    def get_battle_result(self) -> str:
        if not self.combat_engine:
            return "No battle in progress."

        if self.combat_engine.combatant_a.is_dead():
            return f"Battle ended. Winner: {self.combat_engine.combatant_b.name}"
        elif self.combat_engine.combatant_b.is_dead():
            return f"Battle ended. Winner: {self.combat_engine.combatant_a.name}"
        else:
            return "Battle is still ongoing."


def load_combatant(file_path: Union[str, Path]) -> Combatant:
    with open(file_path, "rb") as f:
        data = tomli.load(f)
    return Combatant.parse_obj(data)


def save_combatant(combatant: Combatant, file_path: Union[str, Path]) -> None:
    with open(file_path, "wb") as f:
        tomli_w.dump(combatant.dict(), f)


def main():
    simulator = BattleSimulator()

    while True:
        print("\n--- Mech vs Monster Battle Simulator ---")
        print("1. Load combatants")
        print("2. View combatants")
        print("3. Modify combatant")
        print("4. Start battle")
        print("5. Simulate round")
        print("6. Get battle result")
        print("7. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            file_a = input("Enter file path for combatant A: ")
            if not file_a:
                file_a = "combatant_a.toml"
            file_b = input("Enter file path for combatant B: ")
            if not file_b:
                file_b = "combatant_b.toml"
            simulator.load_combatants(file_a, file_b)
        elif choice == "2":
            simulator.view_combatants()
        elif choice == "3":
            side = input("Which combatant to modify? (A/B): ")
            attribute = input("Enter attribute to modify: ")
            new_value = int(input(f"Enter new value for {attribute}: "))
            print(simulator.modify_combatant(side, attribute, new_value))
        elif choice == "4":
            simulator.start_battle()
        elif choice == "5":
            simulator.simulate_round()
        elif choice == "6":
            print(simulator.get_battle_result())
        elif choice == "7":
            print("Exiting the Battle Simulator. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
    print("Exiting")
