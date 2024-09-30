from mvm.core import AttackType, Combatant, CombatEngine, Terrain
from utils.combat_logging import logger  # noqa: F401


# Universal
def at_start_cond(self: Terrain, engine: CombatEngine) -> bool:
    return self.triggered


# Hela
def hela_effect(self: Terrain, engine: CombatEngine):
    def check_armor_loss(self: Combatant, damage: int, armor_dmg: int, shields_dmg: int, damage_type: AttackType):
        if damage * 10 >= self.original_armor:
            self.apply_damage(40, AttackType.BALLISTIC)

    for combatant in [engine.combatant_a, engine.combatant_b]:
        if check_armor_loss not in combatant.on_damage_taken_effects:
            combatant.on_damage_taken_effects.append(check_armor_loss)


hela = Terrain(
    name="Hela",
    description=(
        "When a combatant loses 10% or more of their maximum Armor in a single attack, they take an "
        + "additional 40 Ballistics damage."
    ),
    effect=hela_effect,
    condition=at_start_cond,
)


# Lake Tampua
def lake_tampua_effect(self: Terrain, engine: CombatEngine):
    def check_low_roll(self: Combatant, roll: int, attack_type: AttackType):
        if roll < 100:
            self.apply_damage(100, AttackType.BALLISTIC)
            self.velocity = max(0, self.velocity - 50)

    for combatant in [engine.combatant_a, engine.combatant_b]:
        combatant.on_hit_roll_effects.append(check_low_roll)


lake_tampua = Terrain(
    name="Lake Tampua",
    description=(
        "When a combatant rolls below 100 on a hit roll, they take 100 Ballistics damage and lose up to 50 Velocity."
    ),
    effect=lake_tampua_effect,
    condition=at_start_cond,
)

# Malvinas
# def malvinas_effect(self: Terrain, engine: CombatEngine):
#     old_calculate_hit = engine.calculate_hit
#     def new_calculate_hit(attacker: Combatant, defender: Combatant, att_type: AttackType):
#         if att_type == AttackType.BALLISTIC:
#             attacker.modifiers.setdefault("attack_hit_chance_mod", {})
#             attacker.modifiers["attack_hit_chance_mod"][AttackType.BALLISTIC] = (
#                 attacker.modifiers.get("attack_hit_chance_mod", {}).get(AttackType.BALLISTIC, 0) + 20
#             )
#         result = old_calculate_hit(attacker, defender, att_type)
#         if att_type == AttackType.BALLISTIC:
#             attacker.modifiers["attack_hit_chance_mod"][AttackType.BALLISTIC] -= 20
#         return result
#     engine.calculate_hit = new_calculate_hit

#     for combatant in [engine.combatant_a, engine.combatant_b]:
#         old_get_damage = combatant.get_damage
#         def new_get_damage(damage_type: AttackType):
#             damage = old_get_damage(damage_type)
#             if damage_type == AttackType.BALLISTIC:
#                 damage += 20
#             return damage
#         combatant.get_damage = new_get_damage

# malvinas = Terrain(
#     name="Malvinas",
#     description="Increase all Ballistics hit rolls and damage by 20.",
#     effect=malvinas_effect,
#     condition=at_start_cond
# )


# Okavango
def okavango_effect(self: Terrain, engine: CombatEngine):
    def reduce_velocity_on_miss(self: Combatant, hit: bool, attack_type: AttackType):
        if not hit:
            self.velocity = max(0, self.velocity - 11)

    for combatant in [engine.combatant_a, engine.combatant_b]:
        combatant.on_attack_result_effects.append(reduce_velocity_on_miss)


okavango = Terrain(
    name="Okavango",
    description=(
        "Whenever a combatant misses an attack, reduce their Velocity by up to 11 until the start of their next turn."
    ),
    effect=okavango_effect,
    condition=at_start_cond,
)


# Ruthenian Grasses
def ruthenian_grasses_effect(self: Terrain, engine: CombatEngine):
    # TODO: Implement

    # old_calculate_hit = engine.calculate_hit
    # def new_calculate_hit(attacker: Combatant, defender: Combatant, att_type: AttackType):
    #     attacker.modifiers.setdefault("attack_hit_chance_mod", {})
    #     attacker.modifiers["attack_hit_chance_mod"][att_type] = (
    #          attacker.modifiers.get("attack_hit_chance_mod", {}).get(att_type, 0) - 20
    #     )
    #     result = old_calculate_hit(attacker, defender, att_type)
    #     attacker.modifiers["attack_hit_chance_mod"][att_type] += 20
    #     return result
    # engine.calculate_hit = new_calculate_hit
    raise NotImplementedError()


ruthenian_grasses = Terrain(
    name="Ruthenian Grasses",
    description="Reduce both combatants' hit rolls by up to 20.",
    effect=ruthenian_grasses_effect,
    condition=at_start_cond,
)


# Badaxsan
def badaxsan_effect(self: Terrain, engine: CombatEngine):
    def check_attack_dmg(
        self: Combatant, damage: int, armor_dmg: int, shields_dmg: int, damage_type: AttackType
    ) -> None:
        if damage >= 40 and damage_type == AttackType.BALLISTIC:
            self.velocity -= 4

    for combatant in [engine.combatant_a, engine.combatant_b]:
        combatant.on_damage_taken_effects.append(check_attack_dmg)


badaxsan = Terrain(
    name="Badaxsan",
    description=("Whenever a combatant takes Ballistics damage, reduce their Velocity by up to 4."),
    effect=badaxsan_effect,
    condition=at_start_cond,
)


terrains: dict[str, Terrain] = {
    "Hela": hela,
    "Lake Tampua": lake_tampua,
    # "Malvinas": malvinas,
    "Okavango": okavango,
    "Ruthenian Grasses": ruthenian_grasses,
    "Badaxsan": badaxsan,
    # Add more terrains to this dictionary...
}
