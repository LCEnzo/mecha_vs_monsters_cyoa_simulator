from __future__ import annotations

import random
import traceback  # noqa: F401
from abc import ABC, abstractmethod
from copy import replace
from functools import wraps
from typing import Callable, Self

from pydantic import BaseModel, ConfigDict, Field

from mvm.core import Combatant, Terrain
from utils.log_util import logger  # noqa: F401
from utils.settings import settings  # noqa: F401


class EffectManager[T: BattleState]:
    effects: dict[type[BattleState], list[Callable[[T], None]]] = {}

    def register_effect(self, state_type: type[T], effect: Callable[[T], None]) -> None:
        if state_type not in self.effects:
            self.effects[state_type] = []
        self.effects[state_type].append(effect)

    def get_effects(self, state: T) -> list[Callable[[T], None]]:
        return self.effects.get(type(state), [])


# TODO: move this somehow into BattleState
def save_before_transition[T: Callable](func: T) -> T:
    @wraps
    def wrapper(self, *args, **kwargs):
        self.save_state()
        return func(self, *args, **kwargs)

    return wrapper


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
    rng: random.Random = Field(exclude=True)
    effect_manager: EffectManager = EffectManager()

    model_config = ConfigDict(frozen=True)

    def __init__(self, **data):
        super().__init__(**data)

        # TODO:
        # for effect in self.combatant_a.effects + self.combatant_b.effects:
        #     self.effect_manager.register_effect(effect)

    def __post_init__(self):
        # https://stackoverflow.com/questions/53756788/how-to-set-the-value-of-dataclass-field-in-post-init-when-frozen-true
        object.__setattr__(self, "rng", random.Random(self.random_seed))

    @abstractmethod
    def _transition(self) -> BattleState:
        pass

    def transition(self) -> BattleState:
        self.save_state()
        return self._transition()

    def save_state(self: Self):
        raise NotImplementedError()

    def apply_effects(self):
        for effect in self.effect_manager.get_effects(self):
            effect(self)


class Start(BattleState):
    def _transition(self: Self) -> VelocityRoll:
        # call effects
        return VelocityRoll(**self.model_dump())


class RoundStart(BattleState):
    def _transition(self: Self) -> VelocityRoll:
        # call effects

        return VelocityRoll(replace(self, round_count=self.round_count + 1).model_dump())


class VelocityRoll(BattleState):
    def _transition(self: Self) -> TurnStart:
        # call preroll effects
        # roll combatants
        raise NotImplementedError()


class TurnStart(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def _transition(self: Self) -> FirepowerAttack:
        raise NotImplementedError()


class FirepowerAttack(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def _transition(self: Self) -> BallisticsAttack | TurnEnd:
        raise NotImplementedError()


class BallisticsAttack(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def _transition(self: Self) -> ChemicalAttack | TurnEnd:
        raise NotImplementedError()


class ChemicalAttack(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def _transition(self: Self) -> TurnEnd:
        raise NotImplementedError()


class TurnEnd(BattleState):
    is_a_attacking: bool
    has_a_finished_their_turn: bool
    has_b_finished_their_turn: bool

    def _transition(self: Self) -> RoundEnd | TurnStart:
        # call turn end effects
        if self.combatant_a.is_dead() or self.combatant_b.is_dead():
            return RoundEnd(**self.model_dump())

        if self.has_a_finished_their_turn and self.has_b_finished_their_turn:
            return RoundEnd(**self.model_dump())

        raise NotImplementedError()


class RoundEnd(BattleState):
    def _transition(self: Self) -> End | RoundStart:
        # call post round effects
        if self.combatant_a.is_dead() or self.combatant_b.is_dead():
            return End(**self.model_dump())

        raise NotImplementedError()


class End(BattleState):
    def _transition(self: Self) -> End:
        return self
