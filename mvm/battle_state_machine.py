from __future__ import annotations

import enum
import random
import traceback  # noqa: F401
from abc import ABC, abstractmethod
from copy import replace
from pathlib import Path
from random import randint
from typing import Callable, Self, TypeVarTuple, Unpack

import tomli
import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator
from termcolor import colored

from mvm.core import Combatant, Terrain
from utils.log_util import logger
from utils.settings import settings


class EffectManager[T: BattleState]:
    effects: dict[type[BattleState], list[Callable[[T], None]]] = {}

    @classmethod
    def register_effect(cls, state_type: type[T], effect: Callable[[T], None]):
        if state_type not in cls.effects:
            cls.effects[state_type] = []
        cls.effects[state_type].append(effect)

    @classmethod
    def get_effects(cls, state: T) -> list[Callable[[T], None]]:
        return cls.effects.get(type(state), [])


# TODO: Consider how state could be frozen, and the implications on inheritance
# TODO: Consider where history should be stored (as part of the BattleState, 
#       as a concern for higher level structs, just dumped into a DB, or w/e)
class BattleState(ABC, BaseModel):
    # TODO: Consider storing the random seed as part of the state
    combatant_a: Combatant
    adds_a: list
    combatant_b: Combatant
    adds_b: list
    round_count: int = 0
    terrain: Terrain | None = None
    random_seed: int = Field(default_factory=lambda: random.randint(0, 2**32 - 1))
    rng: random.Random = Field(default=None, exclude=True)

    def __init__(self, **data):
        super().__init__(**data)
        self.rng = random.Random(self.random_seed)

    effects: dict[type[child_of(BattleState)], Callable] = {}

    @abstractmethod
    def transition(self: Self) -> BattleState:
        pass

    def save_state(self: Self):
        raise NotImplementedError()


class Start(BattleState):
    def transition(self: Self) -> VelocityRoll:
        self.save_state()
        # call effects
        return VelocityRoll(self)

class RoundStart(BattleState):
    def transition(self: Self) -> VelocityRoll:
        self.save_state()
        # call effects

        return VelocityRoll(replace(self, round_count=self.round_count + 1))

class VelocityRoll(BattleState):
    def transition(self: Self) -> TurnStart:
        self.save_state()
        # call preroll effects
        # roll combatants
        raise NotImplementedError()

class TurnStart(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def transition(self: Self) -> FirepowerAttack:
        self.save_state()
        raise NotImplementedError()

class FirepowerAttack(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def transition(self: Self) -> BallisticsAttack | TurnEnd:
        self.save_state()
        raise NotImplementedError()

class BallisticsAttack(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def transition(self: Self) -> ChemicalAttack | TurnEnd:
        self.save_state()
        raise NotImplementedError()

class ChemicalAttack(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def transition(self: Self) -> TurnEnd:
        self.save_state()
        raise NotImplementedError()

class TurnEnd(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def transition(self: Self) -> RoundEnd | TurnStart:
        self.save_state()
        # call turn end effects
        if (self.combatant_a.is_dead() or self.combatant_b.is_dead()):
            return RoundEnd(self)
        
        if (self.has_a_finished_their_turn and self.has_b_finished_their_turn):
            return RoundEnd(self)

        raise NotImplementedError()

class RoundEnd(BattleState):
    def transition(self: Self) -> End | RoundStart:
        self.save_state()
        # call post round effects
        if (self.combatant_a.is_dead() or self.combatant_b.is_dead()):
            return End(self)
        
        raise NotImplementedError()
        
class End(BattleState):
    def transition(self: Self) -> End:
        return self
