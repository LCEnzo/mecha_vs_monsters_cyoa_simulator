#!python
# Mechs vs Monsters CYOA	https://docs.google.com/spreadsheets/d/1EtHtPwQyUKCrR4irR_aebse2ZSU6UZWsZOiLbhThnsY/edit?gid=0#gid=0

from random import randint
from pprint import pprint
from pydantic import BaseModel
from typing import Any, List, Dict, Callable, Union, LiteralString
import enum


class AttackType(enum.Enum):
    FIREPOWER = "Firepower"
    CHEMICAL = "Chemical"
    BALLISTIC = "Ballistic"


class Effect(BaseModel):
    name: str
    trigger_condition: str
    effect_func: Callable

    def apply(self, combatant: "Combatant"):
        """Apply the effect to a combatant"""
        self.effect_func(combatant)


class Combatant(BaseModel):
    name: str
    armor: int
    shields: int
    ballistics: int
    chemical: int
    firepower: int
    velocity: int
    effects: list["Effect"]
    armor_modifiers: Dict[AttackType, int]
    shield_modifiers: Dict[AttackType, int]
    modifiers: Dict[str, Any]

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
        if damage_type in self.armor_modifiers:
            damage += self.armor_modifiers[damage_type]
        return max(0, damage)


class CombatEngine(BaseModel):
    combatant_a: Combatant
    combatant_b: Combatant
    # Logs yet to be printed
    new_logs: list[str]
    # Logs printed already
    old_logs: list[str]
    current_turn: int = 1

    def simulate_round(self):
        # Determine order of attacks based on velocity
        total_velocity_a = self.combatant_a.velocity + randint(1, 1000)
        total_velocity_b = self.combatant_b.velocity + randint(1, 1000)

        if total_velocity_a >= total_velocity_b:
            attacker, defender = self.combatant_a, self.combatant_b
        else:
            attacker, defender = self.combatant_b, self.combatant_a

        # Process turn
        self.process_turn(attacker, defender, AttackType.FIREPOWER)
        self.log_round()

        self.process_turn(attacker, defender, AttackType.BALLISTIC)
        self.log_round()

        self.process_turn(attacker, defender, AttackType.CHEMICAL)
        self.log_round()

        # Offer feedback option to user
        if self.get_user_feedback():
            self.modify_round()

        self.current_turn += 1

    def process_turn(self, attacker: Combatant, defender: Combatant, att_type):
        # Roll for hit success based on velocity and apply damage
        hit_roll = self.calculate_hit(attacker, defender, att_type)
        if hit_roll:
            damage = self.calculate_damage(attacker, defender)
            defender.apply_damage(damage, att_type)

    def calculate_hit(self, attacker: Combatant, defender: Combatant, att_type: AttackType) -> bool:
        """Calculate whether an attack hits, taking into account modifiers."""
        base_hit = randint(0, 1000)
        hit_chance = (attacker.velocity - defender.velocity) // 2

        hit_chance += attacker.modifiers.get("attack_hit_chance_mod", {}).get(att_type, 0)
        hit_chance -= defender.modifiers.get("defense_hit_chance_mod", {}).get(att_type, 0)

        hit_roll: bool = base_hit >= 500 - hit_chance
        return hit_roll

    def calculate_damage(self, attacker: Combatant, defender: Combatant) -> int:
        """Calculate base damage and any modifiers."""
        base_damage = attacker.firepower
        return base_damage

    def log_round(self):
        """Log results for each round."""
        for log in self.new_logs:
            print(log)
            self.old_logs.append(log)

        self.new_logs.clear()

    def add_log(self, msg: str):
        prefix = f"Turn {self.current_turn:3d}: "
        self.new_logs.append(prefix + msg)

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


def main():
    raise NotImplementedError()


if __name__ == "__main__":
    main()
    print("Exiting")
