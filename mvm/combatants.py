from mvm.core import (
    AttackState,
    AttackType,
    BattleState,
    Combatant,
    DamageData,
    Effect,
    HitRollData,
    Signal,
    SignalType,
)
from utils.log_util import logger  # noqa: F401
from utils.settings import settings  # noqa: F401


# Shinigami
def switcharoo_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
    other = state.combatant_b if effect_from_a else state.combatant_a
    return other.shields == 0 and effect.trigger_count == 0


def switcharoo_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
    self = state.combatant_a if effect_from_a else state.combatant_b
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
def suit_extra_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
    if signal.type != SignalType.POST_HIT_ROLL:
        return False

    assert isinstance(state, AttackState)
    assert isinstance(signal.data, HitRollData)

    return signal.data.does_hit and state.att_type == AttackType.BALLISTIC


def suit_extra_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
    self = state.combatant_a if effect_from_a else state.combatant_b
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
def last_stand_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
    # TODO: some kind of take damage condition or signal
    self = state.combatant_a if effect_from_a else state.combatant_b
    return self.armor == 0 and effect.trigger_count == 0


def last_stand_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
    self = state.combatant_a if effect_from_a else state.combatant_b
    self.armor = 1


def shield_plates_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
    # TODO: some kind of take damage condition or signal
    self = state.combatant_a if effect_from_a else state.combatant_b
    return self.shields == 0 and effect.trigger_count == 0


def shield_plates_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
    self = state.combatant_a if effect_from_a else state.combatant_b
    self.shields = 1


def flare_knives_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
    return signal.type == SignalType.ROUND_START and effect.trigger_count < 10


def flare_knives_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
    other = state.combatant_b if effect_from_a else state.combatant_a
    other.apply_damage(15, AttackType.FIREPOWER)


def tandem_demo_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
    if signal.type != SignalType.POST_DMG_APPLICATION:
        return False

    assert isinstance(signal.data, DamageData)

    other = state.combatant_b if effect_from_a else state.combatant_a
    return (
        isinstance(state, AttackState)
        and state.att_type == AttackType.FIREPOWER
        and signal.data.pre_damage_shields > 0
        and other.shields <= 0
    )


def tandem_demo_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
    other = state.combatant_b if effect_from_a else state.combatant_a
    other.apply_damage(200, AttackType.FIREPOWER)


# def riposta_condition(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool) -> bool:
#     return (
#         signal.type == SignalType.POST_DMG_APPLICATION
#         and isinstance(state, AttackState)
#         and state.att_type == AttackType.FIREPOWER
#         and signal.data.a_is_attacking
#     )


# def riposta_effect(effect: Effect, state: BattleState, signal: Signal, effect_from_a: bool):
#     self = state.combatant_a if effect_from_a else state.combatant_b
#     self.armor += 25
#     self.shields += 25


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
        Effect(name="Flare Knives",  trigger_condition=flare_knives_condition,  effect_func=flare_knives_effect),
        Effect(name="Tandem Demo",   trigger_condition=tandem_demo_condition,   effect_func=tandem_demo_effect),
        # Effect(name="Riposta",       trigger_condition=riposta_condition,       effect_func=riposta_effect),
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
