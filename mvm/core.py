from __future__ import annotations

import enum
import logging  # noqa: F401
import random
import time
import traceback  # noqa: F401
from abc import ABC, abstractmethod
from dataclasses import fields as dataclasses_fields
from enum import Enum
from functools import wraps
from typing import Any, Callable, Literal, Self, TypeIs, TypeVarTuple, Unpack

# from line_profiler import profile  # noqa: F401
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.dataclasses import dataclass
from pydantic.fields import FieldInfo
from termcolor import colored

from utils.log_util import logger  # noqa: F401
from utils.settings import settings  # noqa: F401


class AttackType(enum.StrEnum):
    FIREPOWER = "Firepower"
    CHEMICAL = "Chemical"
    BALLISTIC = "Ballistics"


class SignalType(Enum):
    BATTLE_START = "battle_start"
    ROUND_START = "round_start"
    PRE_VELOCITY_ROLL = "pre_velocity_roll"
    POST_VELOCITY_ROLL = "post_velocity_roll"
    TURN_START = "turn_start"
    PRE_ATTACK = "pre_attack"
    POST_HIT_ROLL = "post_hit_roll"
    POST_DMG_CALC = "post_dmg_calc"
    POST_DMG_APPLICATION = "post_dmg_application"
    POST_ATTACK = "post_attack"
    TURN_END = "turn_end"
    ROUND_END = "round_end"
    BATTLE_END = "battle_end"


@dataclass
class PostVelocityRollData:
    roll_a: int
    roll_b: int
    total_velocity_a: int
    total_velocity_b: int
    a_is_attacking: bool


@dataclass
class HitRollData:
    base_roll: int
    hit_chance: int
    att_mod: int
    def_mod: int
    does_hit: bool


@dataclass
class DamageData:
    attacker_is_a: bool
    pre_damage_armor: int
    pre_damage_shields: int
    damage: int


SignalData = PostVelocityRollData | HitRollData | DamageData


@dataclass
class Signal:
    type: SignalType
    # Data is unfortunately both input and output
    data: SignalData | None = None


Ts = TypeVarTuple("Ts")  # for *args


class Effect(BaseModel):
    name: str
    trigger_condition: Callable[[Self | Effect, BattleState, Signal, bool, Unpack[Ts]], bool]
    effect_func: Callable[[Self | Effect, BattleState, Signal, bool, Unpack[Ts]], None]
    trigger_count: int = Field(default=0, ge=0)
    target_state: type[BattleState] | None = Field(default=None, frozen=True)

    # profile
    def apply(
        self,
        curr_state: BattleState,
        signal: Signal,
        effect_from_a: bool,
        *args,
        **kwargs,
    ) -> None:
        if self.target_state is not None and not isinstance(curr_state, self.target_state):
            return None

        try:
            if self.trigger_condition(self, curr_state, signal, effect_from_a, *args, **kwargs):
                self.effect_func(self, curr_state, signal, effect_from_a, *args, **kwargs)
                self.trigger_count += 1

                name_color: Literal["green"] | Literal["red"] = "green" if effect_from_a else "red"
                name = curr_state.combatant_a.name if effect_from_a else curr_state.combatant_b.name
                name = colored(name, name_color)
                logger.info(f"Executed effect {colored(self.name, 'light_cyan')} for {name}")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Effect {self.name} borked, exception {e}")

            if settings.is_debug():
                raise e


class Combatant(BaseModel):
    name: str
    armor: int = Field(..., ge=0)
    shields: int = Field(..., ge=0)
    ballistics: int = Field(..., ge=0)
    chemical: int = Field(..., ge=0)
    firepower: int = Field(..., ge=0)
    velocity: int = Field(..., ge=0)
    effects: list[Effect] = Field(default_factory=list)
    armor_modifiers: dict[AttackType, int] = Field(default_factory=dict)
    shield_modifiers: dict[AttackType, int] = Field(default_factory=dict)
    modifiers: dict[str, dict[str, int]] = Field(default_factory=dict)

    original_armor: int = 0
    original_shields: int = 0
    original_ballistics: int = 0
    original_chemical: int = 0
    original_firepower: int = 0
    original_velocity: int = 0

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)  # slots=True ??

    @field_validator("armor", "shields", "ballistics", "chemical", "firepower", "velocity")
    @classmethod
    def check_positive(cls, v):
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    # profile
    def merge(self, other: Combatant) -> Combatant:
        c = self.model_copy(deep=True)
        c.merge_inplace(other)
        return c

    # profile
    def merge_inplace(self, other: Combatant) -> None:
        self.armor += other.armor
        self.shields += other.shields
        self.ballistics += other.ballistics
        self.chemical += other.chemical
        self.firepower += other.firepower
        self.velocity += other.velocity
        self.effects.extend(other.effects)

    def __init__(self, **data):
        super().__init__(**data)
        self.original_armor = self.armor
        self.original_shields = self.shields
        self.original_ballistics = self.ballistics
        self.original_chemical = self.chemical
        self.original_firepower = self.firepower
        self.original_velocity = self.velocity

    def __setattr__(self, name, value):
        if name in self.model_fields:
            super().__setattr__(name, value)
        else:
            object.__setattr__(self, name, value)

    # profile
    def apply_damage(self, damage: int, damage_type: AttackType) -> int:
        """Apply damage based on shields/armor and return the actual applied damage"""
        effective_hp = self.armor + self.shields
        pre_dmg_armor = self.armor
        pre_dmg_shields = self.shields
        damage = self.modify_damage(damage, damage_type)

        if self.shields > 0:
            self.shields = max(0, self.shields - damage)
        else:
            self.armor = max(0, self.armor - damage)

        applied_damage = effective_hp - (self.shields + self.armor)
        return max(0, applied_damage)

    # profile
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


class Terrain(BaseModel):
    name: str
    description: str
    effect: Callable[[Self | Terrain, BattleState, Signal], None]
    condition: Callable[[Self | Terrain, BattleState, Signal], bool] = lambda self, state, signal: True
    triggered: bool = False

    model_config = ConfigDict(extra="forbid")  # slots=True ??

    # profile
    def apply_effect(self, state: BattleState, signal: Signal, *args, **kwargs):
        if self.condition(self, state, signal, *args, **kwargs):
            self.effect(self, state, signal, *args, **kwargs)
            self.triggered = True
            logger.info(f"Executed terrain {colored(self.name, 'yellow')}")


# TODO: Consider where history should be stored (as part of the BattleState,
#       as a concern for higher level structs, just dumped into a DB, or w/e)
@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid", arbitrary_types_allowed=True))
class BattleState(ABC):
    # When adding new fields, check `dump_for_transition`
    combatant_a: Combatant
    combatant_b: Combatant
    main_a: Combatant  # = Field()
    main_b: Combatant  # = Field()
    rng: random.Random = Field(exclude=True, repr=False)
    adds_a: list[Combatant] = Field(default_factory=list)
    adds_b: list[Combatant] = Field(default_factory=list)
    terrain: Terrain | None = Field(default=None)
    round_count: int = Field(default=0)
    random_seed: int = Field(default_factory=lambda: random.randint(0, 2**32 - 1))

    saved_states: list[BattleState] = Field(default_factory=lambda: [], exclude=True, repr=False)

    # profile
    def apply_effects(self, signal: Signal, *args, **kwargs):
        if self.terrain:
            self.terrain.apply_effect(self, signal, *args, **kwargs)
        for effect_a in self.combatant_a.effects:
            effect_a.apply(self, signal, True, *args, **kwargs)
        for effect_b in self.combatant_b.effects:
            effect_b.apply(self, signal, False, *args, **kwargs)

    @abstractmethod
    def _transition(self) -> BattleState:
        pass

    # profile
    def transition(self) -> BattleState:
        self.save_state()
        return self._transition()

    # profile
    def save_state(self) -> None:
        dump: dict = self.dump_for_transition(honor_exclude=False)
        dump.pop("saved_states", None)
        dump.pop("archived_copy", None)

        if isinstance(self, End):
            dump["archived_copy"] = True
        archived = self.__class__(**dump)
        self.saved_states.append(archived)
        # TODO: Save to DB ?

    def had_someone_died(self) -> bool:
        return self.combatant_a.is_dead() or self.combatant_b.is_dead()

    # profile
    def dump_for_transition(self, honor_exclude: bool = True) -> dict[str, Any]:
        """
        Dynamically creates a dictionary of all fields in the dataclass,
        excluding those marked with exclude=True in their Field definition.

        Meant for use in transition() and _transition() methods.
        """
        fields = dataclasses_fields(self)
        fields_dict = {
            field.name: getattr(self, field.name)
            for field in fields
            if not honor_exclude
            or not (
                (
                    hasattr(field, "default")
                    and isinstance(field.default, FieldInfo)
                    or (callable(field.default) and getattr(field.default, "exclude", False))
                )
                or (
                    hasattr(field, "default_factory")
                    and isinstance(field.default_factory, FieldInfo)
                    or (callable(field.default_factory) and getattr(field.default_factory, "exclude", False))
                )
            )
        }
        return fields_dict

    @staticmethod
    def save_before_transition(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.save_state()
            return func(self, *args, **kwargs)

        return wrapper

    def set_new_rng(self, random_seed: int | None = None) -> None:
        if random_seed is None:
            random_seed = int(time.time_ns())
            if self.random_seed >= random_seed:
                random_seed += self.random_seed + 1

        # https://stackoverflow.com/questions/53756788/how-to-set-the-value-of-dataclass-field-in-post-init-when-frozen-true
        object.__setattr__(self, "random_seed", random_seed)
        object.__setattr__(self, "rng", random.Random(random_seed))


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class Start(BattleState):
    @classmethod
    def initialize(
        cls,
        main_a: Combatant,
        main_b: Combatant,
        adds_a: list[Combatant],
        adds_b: list[Combatant],
        terrain: Terrain | None = None,
        random_seed: int | None = None,
    ) -> Start:
        if random_seed is None:
            random_seed = int(time.time_ns())
        rng = random.Random(random_seed)

        combatant_a = main_a.model_copy(deep=True)
        for ca in adds_a:
            combatant_a.merge_inplace(ca)

        combatant_b = main_b.model_copy(deep=True)
        for cb in adds_b:
            combatant_b.merge_inplace(cb)

        logger.info(f"{random_seed = }, {rng = }")

        return cls(
            combatant_a=combatant_a,
            main_a=main_a,
            adds_a=adds_a,
            combatant_b=combatant_b,
            main_b=main_b,
            adds_b=adds_b,
            terrain=terrain,
            random_seed=random_seed,
            rng=rng,
        )

    def _transition(self) -> RoundStart:
        self.apply_effects(Signal(SignalType.BATTLE_START))
        return RoundStart(**self.dump_for_transition(honor_exclude=False))


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class RoundStart(BattleState):
    # profile
    def _transition(self) -> VelocityRoll:
        rc = self.round_count
        # https://stackoverflow.com/questions/53756788/how-to-set-the-value-of-dataclass-field-in-post-init-when-frozen-true
        object.__setattr__(self, "round_count", self.round_count + 1)
        self.apply_effects(Signal(SignalType.ROUND_START))
        assert rc == self.round_count - 1
        return VelocityRoll(**self.dump_for_transition(honor_exclude=False))


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class VelocityRoll(BattleState):
    # profile
    def _transition(self) -> TurnStart:
        self.apply_effects(Signal(SignalType.PRE_VELOCITY_ROLL))

        roll_a = self.rng.randint(1, 1000)
        roll_b = self.rng.randint(1, 1000)
        total_velocity_a = self.combatant_a.velocity + roll_a
        total_velocity_b = self.combatant_b.velocity + roll_b
        a_is_attacking = total_velocity_a >= total_velocity_b

        ctx = PostVelocityRollData(
            roll_a=roll_a,
            roll_b=roll_b,
            total_velocity_a=total_velocity_a,
            total_velocity_b=total_velocity_b,
            a_is_attacking=a_is_attacking,
        )
        self.apply_effects(Signal(SignalType.POST_VELOCITY_ROLL, ctx))

        roll_a = ctx.roll_a
        roll_b = ctx.roll_b
        total_velocity_a = ctx.total_velocity_a
        total_velocity_b = ctx.total_velocity_b
        a_is_attacking = ctx.a_is_attacking

        logger.info(
            f"Round {self.round_count}: {colored(self.combatant_a.name, 'green')} has total velocity "
            f"{total_velocity_a}, AR: {self.combatant_a.armor} SH: {self.combatant_a.shields} vs "
            f"{colored(self.combatant_b.name, 'red')} has {total_velocity_b}, "
            f"AR: {self.combatant_b.armor} SH: {self.combatant_b.shields} "
            f"on Terrain {colored(self.terrain.name, 'yellow')}"
            if self.terrain
            else "without Terrain"
        )

        return TurnStart(
            **self.dump_for_transition(honor_exclude=False),
            a_is_attacking=a_is_attacking,
            has_a_finished_their_turn=False,
            has_b_finished_their_turn=False,
        )


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class TurnState(BattleState, ABC):
    a_is_attacking: bool = Field(default=False)
    has_a_finished_their_turn: bool = Field(default=False)
    has_b_finished_their_turn: bool = Field(default=False)


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class AttackState(TurnState, ABC):
    att_type: AttackType = Field(default=AttackType.FIREPOWER)

    # profile
    def process_attack(self) -> None:
        att_type = self.att_type

        if settings.is_debug():
            assert att_type is not None

        if not self.is_att_type(att_type):
            logger.warning(
                f"Trying to calculate_hit with state ({type(self)}) and att_type ({att_type}). Whole state: {self}"
            )
            return None

        self.apply_effects(Signal(SignalType.PRE_ATTACK))

        attacker = self.combatant_a if self.a_is_attacking else self.combatant_b
        defender = self.combatant_b if self.a_is_attacking else self.combatant_a

        does_hit: bool = self.calculate_hit(attacker, defender)
        if does_hit:
            damage = self.get_damage(attacker, defender)

            pre_damage_armor = defender.armor
            pre_damage_shields = defender.shields
            damage_data = DamageData(self.a_is_attacking, pre_damage_armor, pre_damage_shields, damage)
            self.apply_effects(Signal(SignalType.POST_DMG_CALC, damage_data))
            damage = damage_data.damage

            applied_damage = defender.apply_damage(damage, att_type)
            damage_data = DamageData(self.a_is_attacking, pre_damage_armor, pre_damage_shields, damage)
            self.apply_effects(Signal(SignalType.POST_DMG_APPLICATION, damage_data))
            # For debugging
            if settings.is_debug():
                assert not (applied_damage == 0 and self.get_damage(attacker, defender) != 0)
            logger.info(f"{attacker.name} hits {defender.name} with {att_type.value} for {applied_damage} damage")
        else:
            logger.info(f"{attacker.name} misses {defender.name} with {att_type.value}")

    # profile
    def calculate_hit(self, attacker: Combatant, defender: Combatant) -> bool:
        """Calculate whether an attack hits, taking into account modifiers."""
        att_type = self.att_type

        if settings.is_debug():
            assert att_type is not None

        if not self.is_att_type(att_type):
            logger.warning(
                f"Trying to calculate_hit with state ({type(self)}) and att_type ({att_type}). Whole state: {self}"
            )
            return False

        base_hit = self.rng.randint(0, 1000)
        # TODO ????
        # attacker.on_hit_roll(base_hit, self.att_type)
        hit_chance = (attacker.velocity - defender.velocity) // 2

        att_mod = attacker.modifiers.get("attack_hit_chance_mod", {}).get(att_type.value, 0)
        def_mod = defender.modifiers.get("defense_hit_chance_mod", {}).get(att_type.value, 0)

        does_hit = base_hit + att_mod - def_mod >= 500 - hit_chance
        ctx = HitRollData(
            base_roll=base_hit, hit_chance=hit_chance, att_mod=att_mod, def_mod=def_mod, does_hit=does_hit
        )
        self.apply_effects(Signal(SignalType.POST_HIT_ROLL, data=ctx))
        # TODO: This needs fixing, it's a mess
        does_hit = base_hit + att_mod - def_mod >= 500 - hit_chance
        does_hit = ctx.does_hit

        logger.debug(
            f"Attack ({attacker.name}) calc hit: {(base_hit, hit_chance, att_mod, def_mod) = } -> {does_hit = }"
        )
        self.apply_effects(Signal(SignalType.POST_ATTACK))

        return does_hit

    def get_damage(self, attacker: Combatant, defender: Combatant) -> int:
        return attacker.get_damage(self.att_type)

    def is_att_type(self, val: object) -> TypeIs[AttackType]:
        return isinstance(val, AttackType)


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class TurnStart(TurnState):
    def _transition(self) -> FirepowerAttack:
        self.apply_effects(Signal(SignalType.TURN_START))
        return FirepowerAttack(**self.dump_for_transition(honor_exclude=False))


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class FirepowerAttack(AttackState):
    att_type: AttackType = Field(default=AttackType.FIREPOWER, frozen=True)

    # profile
    def _transition(self) -> BallisticsAttack | TurnEnd:
        assert self.att_type == AttackType.FIREPOWER
        self.process_attack()

        dump = self.dump_for_transition(honor_exclude=False)
        dump.pop("att_type", None)

        if self.had_someone_died():
            return TurnEnd(**dump)
        return BallisticsAttack(**dump)


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class BallisticsAttack(AttackState):
    att_type: AttackType = Field(default=AttackType.BALLISTIC, frozen=True)

    # profile
    def _transition(self) -> ChemicalAttack | TurnEnd:
        assert self.att_type == AttackType.BALLISTIC
        self.process_attack()

        dump = self.dump_for_transition(honor_exclude=False)
        dump.pop("att_type", None)

        if self.had_someone_died():
            return TurnEnd(**dump)
        return ChemicalAttack(**dump)


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class ChemicalAttack(AttackState):
    att_type: AttackType = Field(default=AttackType.CHEMICAL, frozen=True)

    # profile
    def _transition(self) -> TurnEnd:
        assert self.att_type == AttackType.CHEMICAL
        self.process_attack()

        dump = self.dump_for_transition(honor_exclude=False)
        dump.pop("att_type", None)
        return TurnEnd(**dump)


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class TurnEnd(TurnState):
    # profile
    def _transition(self) -> RoundEnd | TurnStart:
        a_finished = self.has_a_finished_their_turn
        b_finished = self.has_b_finished_their_turn

        if self.a_is_attacking:
            a_finished = True
            object.__setattr__(self, "has_a_finished_their_turn", a_finished)
        else:
            b_finished = True
            object.__setattr__(self, "has_b_finished_their_turn", b_finished)

        self.apply_effects(Signal(SignalType.TURN_END))

        if self.had_someone_died():
            # This is fine, we don't need to update the state, as RoundEnd does not track who finished their turn
            return RoundEnd(**self.dump_for_transition(honor_exclude=False))

        if a_finished and b_finished:
            # This is fine, we don't need to update the state, as RoundEnd does not track who finished their turn
            return RoundEnd(**self.dump_for_transition(honor_exclude=False))

        object.__setattr__(self, "a_is_attacking", not self.a_is_attacking)
        return TurnStart(**self.dump_for_transition(honor_exclude=False))


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class RoundEnd(BattleState):
    # profile
    def _transition(self) -> End | RoundStart:
        self.apply_effects(Signal(SignalType.ROUND_END))

        if self.had_someone_died():
            self.apply_effects(Signal(SignalType.BATTLE_END))
            return End(**self.dump_for_transition(honor_exclude=False))

        return RoundStart(**self.dump_for_transition(honor_exclude=False))


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="ignore", arbitrary_types_allowed=True))
class End(BattleState):
    archived_copy: bool = Field(default=False)

    def __post_init__(self):
        if not self.archived_copy:
            self.save_state()
        return None

    def transition(self) -> End:
        raise Exception("Can't transition from End state")

    def _transition(self) -> End:
        raise Exception("Can't transition from End state")
