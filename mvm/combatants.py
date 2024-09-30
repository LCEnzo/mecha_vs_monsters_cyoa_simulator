from mvm.core import AttackType, Combatant, Effect
from utils.combat_logging import logger  # noqa: F401


# Shinigami
def switcharoo_condition(
    effect_info: Effect, self: Combatant, other: Combatant, hit_roll: bool, att_type: AttackType | None
) -> bool:
    return other.shields == 0 and effect_info.trigger_count == 0


def switcharoo_effect(effect_info: Effect, self: Combatant, other: Combatant):
    self.chemical, self.firepower = self.firepower, self.chemical


shinigami = Combatant(
    name="Shinigami",
    armor=2500,
    shields=2500,
    ballistics=800,
    chemical=0,
    firepower=1800,
    velocity=200,
    effects=[Effect(name="Switcharoo", trigger_condition=switcharoo_condition, effect_func=switcharoo_effect)],
)


# Suit
def suit_extra_condition(
    effect_info: Effect, self: Combatant, other: Combatant, hit_roll: bool, att_type: AttackType | None
) -> bool:
    return hit_roll and att_type == AttackType.BALLISTIC


def suit_extra_effect(effect_info: Effect, self: Combatant, other: Combatant):
    self.chemical += 60


suit = Combatant(
    name="Suit",
    armor=1360,
    shields=1130,
    ballistics=356,
    chemical=657,
    firepower=0,
    velocity=124,
    effects=[Effect(name="Extra", trigger_condition=suit_extra_condition, effect_func=suit_extra_effect)],
)


# LCEnzo player
def last_stand_condition(effect_info: Effect, self: Combatant, other: Combatant, hit_roll, att_type):
    return self.armor == 0 and effect_info.trigger_count == 0


def last_stand_effect(effect_info: Effect, self: Combatant, other: Combatant):
    self.armor = 1


def shield_plates_condition(effect_info: Effect, self: Combatant, other: Combatant, hit_roll, att_type):
    return self.shields == 0 and effect_info.trigger_count == 0


def shield_plates_effect(effect_info: Effect, self: Combatant, other: Combatant):
    self.shields = 1


def flare_knives_condition(effect_info: Effect, self: Combatant, other: Combatant, hit_roll, att_type, *args, **kwargs):
    return effect_info.trigger_count < 10 and hit_roll is None  # Assuming hit_roll is None indicates start of round


def flare_knives_effect(effect_info: Effect, self: Combatant, other: Combatant):
    other.apply_damage(15, AttackType.FIREPOWER)


# TODO: Implement this, though it would be a good idea to not just pass parameters ad hoc, but actually store
# current and previous states (engine, combatants) to compare, for this and other effects
def tandem_demo(effect_info: Effect, self: Combatant, other: Combatant, hit_roll, att_type, *args, **kwargs) -> bool:
    # if you break your enemy's shield with a firepower attack,
    raise NotImplementedError()


def tandem_demo_effect(effect_info: Effect, self: Combatant, other: Combatant):
    other.apply_damage(200, AttackType.FIREPOWER)


def riposta_condition(effect_info: Effect, self: Combatant, other: Combatant, hit_roll, att_type):
    return att_type and att_type == AttackType.FIREPOWER


def riposta_effect(effect_info: Effect, self: Combatant, other: Combatant):
    self.armor += 25
    self.shields += 25


# fmt: off
lcenzo = Combatant(
    name="LCEnzo",
    armor=890,
    shields=1030,
    ballistics=352,
    chemical=71,
    firepower=858,
    velocity=357,
    effects=[
        Effect(name="Last Stand",    trigger_condition=last_stand_condition,    effect_func=last_stand_effect),
        Effect(name="Shield Plates", trigger_condition=shield_plates_condition, effect_func=shield_plates_effect),
        Effect(name="Flare Knives",  trigger_condition=flare_knives_condition,  effect_func=flare_knives_effect)
    ],
    modifiers={
        "attack_hit_chance_mod": {
            AttackType.FIREPOWER: 56,
            AttackType.CHEMICAL: 56,
            AttackType.BALLISTIC: 56
        },
        "defense_hit_chance_mod": {
            AttackType.FIREPOWER: -19,
            AttackType.CHEMICAL: -19,
            AttackType.BALLISTIC: -19
        }
    },
    armor_modifiers={
        AttackType.BALLISTIC: -60,
        AttackType.CHEMICAL: -65,  # 60 from armor, 5 from drones
        AttackType.FIREPOWER: -60,
    },
)
# fmt: on

combatants = {
    "LCEnzo": lcenzo,
    "Shinigami": shinigami,
    "Suit": suit,
    # Add more combatants to this dictionary...
}
