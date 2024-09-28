#!python
# Mechs vs Monsters CYOA	https://docs.google.com/spreadsheets/d/1EtHtPwQyUKCrR4irR_aebse2ZSU6UZWsZOiLbhThnsY/edit?gid=0#gid=0

from random import randint
from pprint import pprint
from pydantic import BaseModel
from typing import List, Dict, Callable

class Effect(BaseModel):
    name: str
    trigger_condition: str
    effect_func: Callable

    def apply(self, combatant: 'Combatant'):
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
    effects: list['Effect']
    armor_modifiers: Dict[str, int]
    shield_modifiers: Dict[str, int]

    def apply_damage(self, damage: int, damage_type: str) -> int:
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

    def modify_damage(self, damage: int, damage_type: str) -> int:
        """Apply armor/shield reductions or buffs."""
        if damage_type in self.armor_modifiers:
            damage += self.armor_modifiers[damage_type]
        return max(0, damage)

class CombatEngine(BaseModel):
    combatant_a: Combatant
    combatant_b: Combatant
    round_log: list

    def simulate_round(self):
        # Determine order of attacks based on velocity
        total_velocity_a = self.combatant_a.velocity + randint(1, 1000)
        total_velocity_b = self.combatant_b.velocity + randint(1, 1000)

        if total_velocity_a >= total_velocity_b:
            attacker, defender = self.combatant_a, self.combatant_b
        else:
            attacker, defender = self.combatant_b, self.combatant_a

        # Process turn
        self.process_turn(attacker, defender)
        self.process_turn(defender, attacker)

        self.log_round()

        # Offer feedback option to user
        if self.get_user_feedback():
            self.modify_round()

    def process_turn(self, attacker: Combatant, defender: Combatant):
        # Roll for hit success based on velocity and apply damage
        hit_roll = self.calculate_hit(attacker, defender)
        if hit_roll:
            damage = self.calculate_damage(attacker, defender)
            defender.apply_damage(damage, "Firepower")  # This is just for firepower, similar logic for others

    def calculate_hit(self, attacker: Combatant, defender: Combatant) -> bool:
        """Calculate whether an attack hits, taking into account modifiers."""
        base_hit = randint(0, 1000)
        hit_chance = (attacker.velocity - defender.velocity) // 2  # Base formula
        # Apply hit modifiers (e.g., Pixelation, Steam Vents)
        hit_chance += sum([56])  # Placeholder for E-1337 etc.
        hit_roll = base_hit >= 500 - hit_chance
        return hit_roll

    def calculate_damage(self, attacker: Combatant, defender: Combatant) -> int:
        """Calculate base damage and any modifiers."""
        base_damage = attacker.firepower
        return base_damage

    def log_round(self):
        """Log results for each round."""
        # For simplicity, this just prints but can be written to a log file.
        print(f"{self.combatant_a.name} - Shields: {self.combatant_a.shields}, Armor: {self.combatant_a.armor}")
        print(f"{self.combatant_b.name} - Shields: {self.combatant_b.shields}, Armor: {self.combatant_b.armor}")

    def get_user_feedback(self) -> bool:
        """Ask if user wants to modify the result."""
        return input("Modify results? (y/n) ").strip().lower() == 'y'

    def modify_round(self):
        """Allow user to modify combat results."""
        combatant = input("Which combatant to modify? (A/B) ").strip().lower()
        stat = input("Which stat? (shields/armor/firepower) ").strip().lower()
        new_value = int(input(f"New value for {stat}? "))

        if combatant == "a":
            setattr(self.combatant_a, stat, new_value)
        else:
            setattr(self.combatant_b, stat, new_value)

def do_combat_round(a: Combatant, b: Combatant) -> tuple[Combatant, Combatant]:
    velocity_a = a.velocity + randint(1, 1000)
    velocity_b = a.velocity + randint(1, 1000)

    # 3 attacks, in order: firepower, ballistics, chemical
    for i in range(3):
        

    return a, b

def main()

if __name__ == '__main__':
    main()
    print("Exiting")