from __future__ import annotations

import random
import traceback  # noqa: F401
from abc import ABC, abstractmethod
from copy import replace  # type: ignore
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Callable, TypeIs

from pydantic import BaseModel, ConfigDict, Field
from termcolor import colored

from mvm.core import AttackType, Combatant, Terrain
from utils.log_util import logger  # noqa: F401
from utils.settings import settings  # noqa: F401


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
    DAMAGE_CALCULATION = "damage_calculation"
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
    damage: int


SignalData = PostVelocityRollData | HitRollData | DamageData


@dataclass
class Signal:
    type: SignalType
    # Data is unfortunately both input and output
    data: SignalData | None = None


# TODO: Consider where history should be stored (as part of the BattleState,
#       as a concern for higher level structs, just dumped into a DB, or w/e)
class BattleState(ABC, BaseModel):
    combatant_a: Combatant = Field(exclude=True)
    combatant_b: Combatant = Field(exclude=True)

    main_a: Combatant
    adds_a: list[Combatant]
    main_b: Combatant
    adds_b: list[Combatant]

    terrain: Terrain | None = None

    round_count: int = 0
    random_seed: int = Field(default_factory=lambda: random.randint(0, 2**32 - 1))
    rng: random.Random = Field(exclude=True)

    model_config = ConfigDict(frozen=True)

    def apply_effects(self, signal: Signal, *args, **kwargs):
        if self.terrain:
            self.terrain.effect(self.terrain, self, signal, *args, **kwargs)
        for effect_a in self.combatant_a.effects:
            effect_a.apply(self, signal, True, *args, **kwargs)
        for effect_b in self.combatant_b.effects:
            effect_b.apply(self, signal, False, *args, **kwargs)

    @abstractmethod
    def _transition(self) -> BattleState:
        pass

    def transition(self) -> BattleState:
        self.save_state()
        return self._transition()

    def save_state(self):
        raise NotImplementedError()

    def had_someone_died(self) -> bool:
        return self.combatant_a.is_dead() or self.combatant_b.is_dead()

    @staticmethod
    def save_before_transition(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.save_state()
            return func(self, *args, **kwargs)

        return wrapper


class Start(BattleState):
    def __init__(self, **data):
        super().__init__(**data)

        # https://stackoverflow.com/questions/53756788/how-to-set-the-value-of-dataclass-field-in-post-init-when-frozen-true
        object.__setattr__(self, "rng", random.Random(self.random_seed))

        combatant_a = self.main_a.model_copy(deep=True)
        for ca in self.adds_a:
            combatant_a.merge_inplace(ca)

        combatant_b = self.main_b.model_copy(deep=True)
        for cb in self.adds_b:
            combatant_b.merge_inplace(cb)

        object.__setattr__(self, "combatant_a", combatant_a)
        object.__setattr__(self, "combatant_b", combatant_b)

    def _transition(self) -> RoundStart:
        self.apply_effects(Signal(SignalType.BATTLE_START))
        return RoundStart(**self.model_dump())


class RoundStart(BattleState):
    def _transition(self) -> VelocityRoll:
        new_state = replace(self, round_count=self.round_count + 1)
        new_state.apply_effects(Signal(SignalType.ROUND_START))
        return VelocityRoll(**new_state.model_dump())


class VelocityRoll(BattleState):
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
            **self.model_dump(),
            a_is_attacking=a_is_attacking,
            has_a_finished_their_turn=False,
            has_b_finished_their_turn=False,
        )


class TurnState(BattleState, ABC):
    a_is_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool


class AttackState(TurnState, ABC):
    att_type: AttackType

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
            self.apply_effects(Signal(SignalType.POST_DMG_CALC, DamageData(damage)))
            damage = DamageData.damage

            applied_damage = defender.apply_damage(damage, att_type)
            self.apply_effects(Signal(SignalType.POST_DMG_APPLICATION, DamageData(applied_damage)))
            logger.info(f"{attacker.name} hits {defender.name} with {att_type.value} for {applied_damage} damage")
        else:
            logger.info(f"{attacker.name} misses {defender.name} with {att_type.value}")

    def calculate_hit(self, attacker: Combatant, defender: Combatant) -> bool:
        """Calculate whether an attack hits, taking into account modifiers."""
        att_type = self.att_type

        if settings.is_debug():
            assert att_type is not None

        if not self.is_att_type(att_type):
            logger.warning(
                f"Trying to calculate_hit with state ({type(self)}) and att_type ({att_type})." f" Whole state: {self}"
            )
            return False

        base_hit = self.rng.randint(0, 1000)
        attacker.on_hit_roll(base_hit, self.att_type)
        hit_chance = (attacker.velocity - defender.velocity) // 2

        att_mod = attacker.modifiers.get("attack_hit_chance_mod", {}).get(att_type.value, 0)
        def_mod = defender.modifiers.get("defense_hit_chance_mod", {}).get(att_type.value, 0)

        does_hit = base_hit + att_mod - def_mod >= 500 - hit_chance
        ctx = HitRollData(
            base_roll=base_hit, hit_chance=hit_chance, att_mod=att_mod, def_mod=def_mod, does_hit=does_hit
        )
        self.apply_effects(Signal(SignalType.POST_HIT_ROLL, data=ctx))
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


class TurnStart(TurnState):
    def _transition(self) -> FirepowerAttack:
        self.apply_effects(Signal(SignalType.TURN_START))
        return FirepowerAttack(**self.model_dump())


class FirepowerAttack(AttackState):
    att_type: AttackType = Field(default=AttackType.FIREPOWER, frozen=True)

    def _transition(self) -> BallisticsAttack | TurnEnd:
        self.process_attack()
        if self.had_someone_died():
            return TurnEnd(**self.model_dump())
        return BallisticsAttack(**self.model_dump())


class BallisticsAttack(AttackState):
    att_type: AttackType = Field(default=AttackType.BALLISTIC, frozen=True)

    def _transition(self) -> ChemicalAttack | TurnEnd:
        self.process_attack()
        if self.had_someone_died():
            return TurnEnd(**self.model_dump())
        return ChemicalAttack(**self.model_dump())


class ChemicalAttack(AttackState):
    att_type: AttackType = Field(default=AttackType.CHEMICAL, frozen=True)

    def _transition(self) -> TurnEnd:
        self.process_attack()
        return TurnEnd(**self.model_dump())


class TurnEnd(TurnState):
    def _transition(self) -> RoundEnd | TurnStart:
        a_finished = self.has_a_finished_their_turn
        b_finished = self.has_b_finished_their_turn

        if self.a_is_attacking:
            a_finished = True
        else:
            b_finished = True

        self.apply_effects(Signal(SignalType.TURN_END))

        if self.had_someone_died():
            # This is fine, we don't need to update the state, as RoundEnd does not track who finished their turn
            return RoundEnd(**self.model_dump())

        if a_finished and b_finished:
            # This is fine, we don't need to update the state, as RoundEnd does not track who finished their turn
            return RoundEnd(**self.model_dump())

        new_state = replace(self, a_is_attacking=not self.a_is_attacking)
        return TurnStart(**new_state.model_dump())


class RoundEnd(BattleState):
    def _transition(self) -> End | RoundStart:
        self.apply_effects(Signal(SignalType.ROUND_END))

        if self.had_someone_died():
            self.apply_effects(Signal(SignalType.BATTLE_END))
            return End(**self.model_dump())

        return RoundStart(**self.model_dump())


class End(BattleState):
    def __post_init__(self):
        ret = None
        # ret = super().__post_init__()
        self.save_state()
        return ret

    def transition(self) -> End:
        raise Exception("Can't transition from End state")

    def _transition(self) -> End:
        return self
