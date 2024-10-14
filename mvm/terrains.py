from mvm.core import AttackState, AttackType, BattleState, DamageData, HitRollData, Signal, SignalType, Terrain
from utils.log_util import logger  # noqa: F401
from utils.settings import settings  # noqa: F401


# Universal
def at_start_cond(self: Terrain, state: BattleState, signal: Signal) -> bool:
    return signal.type == SignalType.BATTLE_START


# Hela
def hela_cond(self: Terrain, state: BattleState, signal: Signal) -> bool:
    if signal.type != SignalType.POST_DMG_APPLICATION:
        return False

    if signal.data is None:
        logger.warning(f"Wrong data for signal type in hela_effect terrain {self}\nstate {state}\nsignal {signal}\n")
        if settings.is_debug():
            assert isinstance(signal.data, DamageData)
        return False

    return True


def hela_effect(self: Terrain, state: BattleState, signal: Signal):
    assert signal.type == SignalType.POST_DMG_APPLICATION
    assert isinstance(signal.data, DamageData)

    defender = state.combatant_b if signal.data.attacker_is_a else state.combatant_a
    damage = signal.data.damage

    if damage * 10 >= defender.original_armor:
        defender.apply_damage(40, AttackType.BALLISTIC)


hela = Terrain(
    name="Hela",
    description=(
        "When a combatant loses 10% or more of their maximum Armor in a single attack, they take an "
        "additional 40 Ballistics damage."
    ),
    effect=hela_effect,
    condition=hela_cond,
)


# Lake Tampua
def lake_tampua_cond(self: Terrain, state: BattleState, signal: Signal) -> bool:
    if signal.type != SignalType.POST_HIT_ROLL:
        return False

    if signal.data is None:
        logger.warning(
            f"Wrong data for signal type in lake_tampua_effect terrain {self}\nstate {state}\nsignal {signal}\n"
        )
        if settings.is_debug():
            assert isinstance(signal.data, HitRollData)
        return False

    return True


def lake_tampua_effect(self: Terrain, state: BattleState, signal: Signal):
    assert signal.type == SignalType.POST_HIT_ROLL
    assert isinstance(signal.data, HitRollData)
    assert isinstance(state, AttackState)

    attacker = state.combatant_a if state.a_is_attacking else state.combatant_b

    if signal.data.base_roll < 100:
        attacker.apply_damage(100, AttackType.BALLISTIC)
        attacker.velocity = max(0, attacker.velocity - 50)


lake_tampua = Terrain(
    name="Lake Tampua",
    description=(
        "When a combatant rolls below 100 on a hit roll, they take 100 Ballistics damage and lose up to 50 Velocity."
    ),
    effect=lake_tampua_effect,
    condition=lake_tampua_cond,
)


# Malvinas
def malvinas_cond(self: Terrain, state: BattleState, signal: Signal) -> bool:
    return (
        signal.type in [SignalType.POST_HIT_ROLL, SignalType.POST_DMG_CALC]
        and isinstance(state, AttackState)
        and state.att_type == AttackType.BALLISTIC
    )


def malvinas_effect(self: Terrain, state: BattleState, signal: Signal):
    assert signal.type in [SignalType.POST_HIT_ROLL, SignalType.POST_DMG_CALC]
    assert isinstance(state, AttackState)
    assert state.att_type == AttackType.BALLISTIC

    if signal.type == SignalType.POST_HIT_ROLL:
        assert isinstance(signal.data, HitRollData)
        signal.data.base_roll += 20
    elif signal.type == SignalType.POST_DMG_CALC:
        assert isinstance(signal.data, DamageData)
        signal.data.damage += 20


malvinas = Terrain(
    name="Malvinas",
    description="Increase all Ballistics hit rolls and damage by 20.",
    effect=malvinas_effect,
    condition=malvinas_cond,
)


# Okavango
# TODO: Make the effect temp
# def okavango_cond(self: Terrain, state: BattleState, signal: Signal) -> bool:
#     return signal.type == SignalType.POST_ATTACK


# def okavango_effect(self: Terrain, state: BattleState, signal: Signal):
#     assert signal.type == SignalType.POST_ATTACK
#     assert isinstance(state, AttackState)

#     attacker = state.combatant_a if state.a_is_attacking else state.combatant_b

#     if not signal.data.does_hit:
#         attacker.velocity = max(0, attacker.velocity - 11)


# okavango = Terrain(
#     name="Okavango",
#     description=(
#         "Whenever a combatant misses an attack, reduce their Velocity by up to 11 until the start of their next turn."
#     ),
#     effect=okavango_effect,
#     condition=okavango_cond,
# )


# Ruthenian Grasses
def ruthenian_grasses_effect(self: Terrain, state: BattleState, signal: Signal):
    assert signal.type == SignalType.POST_HIT_ROLL
    assert isinstance(signal.data, HitRollData)

    for att_type in list(AttackType):
        a_mod = state.combatant_a.modifiers.get("attack_hit_chance_mod", {}).get(att_type, 0) - 20
        state.combatant_a.modifiers["attack_hit_chance_mod"][att_type] = a_mod

        b_mod = state.combatant_b.modifiers.get("attack_hit_chance_mod", {}).get(att_type, 0) - 20
        state.combatant_b.modifiers["attack_hit_chance_mod"][att_type] = b_mod


ruthenian_grasses = Terrain(
    name="Ruthenian Grasses",
    description="Reduce both combatants' hit rolls by up to 20.",
    effect=ruthenian_grasses_effect,
    condition=at_start_cond,
)


# Badaxsan
def badaxsan_cond(self: Terrain, state: BattleState, signal: Signal) -> bool:
    if signal.type != SignalType.POST_DMG_APPLICATION:
        return False

    if signal.data is None:
        logger.warning(f"Wrong Signal type in badaxsan_effect terrain {self}\nstate {state}\nsignal {signal}\n")
        if settings.is_debug():
            assert isinstance(signal.data, DamageData)
        return False

    return isinstance(state, AttackState) and state.att_type == AttackType.BALLISTIC


def badaxsan_effect(self: Terrain, state: BattleState, signal: Signal):
    assert signal.type == SignalType.POST_DMG_APPLICATION
    assert isinstance(signal.data, DamageData)
    assert isinstance(state, AttackState)
    assert state.att_type == AttackType.BALLISTIC

    defender = state.combatant_b if signal.data.attacker_is_a else state.combatant_a

    if signal.data.damage > 0:
        defender.velocity = max(0, defender.velocity - 4)


badaxsan = Terrain(
    name="Badaxsan",
    description="Whenever a combatant takes Ballistics damage, reduce their Velocity by up to 4.",
    effect=badaxsan_effect,
    condition=badaxsan_cond,
)


terrains: dict[str, Terrain] = {
    "Hela": hela,
    "Lake Tampua": lake_tampua,
    # "Malvinas": malvinas,
    # "Okavango": okavango,
    "Ruthenian Grasses": ruthenian_grasses,
    "Badaxsan": badaxsan,
    # Add more terrains to this dictionary...
}
