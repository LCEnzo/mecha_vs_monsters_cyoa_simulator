from __future__ import annotations

import enum
import logging
import traceback
from pathlib import Path
from typing import Callable, Literal, Self, TypeVarTuple, Unpack

import tomli
import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator
from termcolor import colored

from mvm.battle_state_machine import BattleState, Signal, SignalType, Start
from utils.log_util import logger
from utils.settings import settings


class AttackType(str, enum.Enum):
    FIREPOWER = "Firepower"
    CHEMICAL = "Chemical"
    BALLISTIC = "Ballistics"


Ts = TypeVarTuple("Ts")  # for *args


class Effect[StateT: BattleState](BaseModel):
    name: str
    trigger_condition: Callable[[Self | Effect, StateT, Signal, bool, Unpack[Ts]], bool]
    effect_func: Callable[[Self | Effect, StateT, Signal, bool, Unpack[Ts]], None]
    trigger_count: int = Field(default=0, ge=0)
    target_state: type[StateT] | None = Field(default=None, frozen=True)

    def apply(
        self,
        curr_state: StateT,
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

    @field_validator("armor", "shields", "ballistics", "chemical", "firepower", "velocity")
    @classmethod
    def check_positive(cls, v):
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    def merge(self, other: Combatant) -> Combatant:
        c = self.model_copy(deep=True)
        c.merge_inplace(other)
        return c

    def merge_inplace(self, other: Combatant) -> None:
        self.armor += other.armor
        self.shields += other.shields
        self.ballistics += other.ballistics
        self.chemical += other.chemical
        self.firepower += other.firepower
        self.velocity += other.velocity
        self.effects.extend(other.effects)

    model_config = ConfigDict(arbitrary_types_allowed=True)

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

    def apply_effect(self, state: BattleState, signal: Signal, *args, **kwargs):
        if self.condition(self, state, signal, *args, **kwargs):
            self.effect(self, state, signal, *args, **kwargs)
            self.triggered = True
            logger.info(f"Executed terrain {colored(self.name, 'yellow')}")


class BattleSimulator(BaseModel):
    main_a: Combatant
    adds_a: list[Combatant] = Field(default_factory=list)
    main_b: Combatant
    adds_b: list[Combatant] = Field(default_factory=list)
    terrain: Terrain | None = None
    current_state: BattleState | None = None

    def start_battle(self):
        if not self.main_a or not self.main_b:
            logger.warning("Please load both combatants before starting a battle.")
            if settings.is_debug():
                raise Exception()
            return

        logger.info("Battle started.")
        self.current_state = Start(
            main_a=self.main_a.model_copy(deep=True),
            adds_a=[m.model_copy(deep=True) for m in self.adds_a],
            main_b=self.main_b.model_copy(deep=True),
            adds_b=[m.model_copy(deep=True) for m in self.adds_b],
            terrain=self.terrain.model_copy(deep=True) if self.terrain else None,
        )
        while self.current_state is not None:
            self.current_state = self.current_state.transition()
        logger.info(self.get_battle_result())

    def get_battle_result(self) -> str:
        if self.current_state is None:
            return "Battle has not started or has ended unexpectedly."
        if self.current_state.combatant_a.is_dead():
            return (
                f"Battle ended. Winner: {colored(self.current_state.combatant_b.name, 'red')} with "
                f"AR {self.current_state.combatant_b.armor} & SH {self.current_state.combatant_b.shields}"
            )
        if self.current_state.combatant_b.is_dead():
            return (
                f"Battle ended. Winner: {colored(self.current_state.combatant_a.name, 'green')} with "
                f"AR {self.current_state.combatant_a.armor} & SH {self.current_state.combatant_a.shields}"
            )
        return "Battle is still ongoing."

    def get_battle_status(self) -> str:
        if self.current_state is None:
            return "Battle has not started or has ended."
        return (
            f"{colored(self.current_state.combatant_a.name, 'green')} - Armor: {self.current_state.combatant_a.armor}, "
            f"Shields: {self.current_state.combatant_a.shields}\n"
            f"{colored(self.current_state.combatant_b.name, 'red')} - Armor: {self.current_state.combatant_b.armor}, "
            f"Shields: {self.current_state.combatant_b.shields}"
        )

    def print_multiple_battle_results(self, total_rounds: int, num_battles: int, results: dict[str, int]):
        if self.main_a is None or self.main_b is None:
            logger.warning("Please load both combatants before running `print_multiple_battle_results`.")
            if settings.is_debug():
                raise BaseException("Trying to access a combatant which is not set in BattleSimulator")
            return None

        avg_rounds = total_rounds / num_battles
        logger.info(f"Battle simulation results after {num_battles} battles:")
        logger.info(
            f"{self.main_a.name} won {results['combatant_a']} times " f"({results['combatant_a']/num_battles*100:.2f}%)"
        )
        logger.info(
            f"{self.main_b.name} won {results['combatant_b']} times " f"({results['combatant_b']/num_battles*100:.2f}%)"
        )
        logger.info(f"Average number of rounds per battle: {avg_rounds:.2f}")

    def run_multiple_battles(self, num_battles: int) -> tuple[dict[str, int], float]:
        results: dict[str, int] = {"combatant_a": 0, "combatant_b": 0}
        total_rounds = 0

        if not self.main_a or not self.main_b:
            logger.warning("Please load both combatants before running multiple battles.")
            if settings.is_debug():
                raise Exception("Expected to have combatants not be None in run_multiple_battles")
            return results, 0

        # Store the original log level of the console handler
        handlers = [
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.StreamHandler) and handler.name == "stdout_stream_log"
        ]
        console_handler = handlers[0] if handlers else None
        original_level = console_handler.level if console_handler else None

        # Temporarily set the console handler to only show WARNING and above
        # console_handler.setLevel(logging.WARNING)

        try:
            for _ in range(num_battles):
                self.start_battle()
                if self.current_state:
                    total_rounds += self.current_state.round_count
                    if self.current_state.combatant_a.is_dead() and not self.current_state.combatant_b.is_dead():
                        results["combatant_b"] += 1
                    if not self.current_state.combatant_a.is_dead() and self.current_state.combatant_b.is_dead():
                        results["combatant_a"] += 1

                print(self.get_battle_result())
                print("")

            console_handler.setLevel(original_level) if console_handler and original_level else None

            self.print_multiple_battle_results(total_rounds, num_battles, results)
        except Exception as e:
            self.print_multiple_battle_results(total_rounds, num_battles, results)

            traceback.print_exc()
            logger.error(f"Error trying to run multiple battles, ran {num_battles} battles")

            if settings.is_debug():
                raise e
        finally:
            console_handler.setLevel(original_level) if console_handler and original_level else None

        return results, total_rounds / num_battles

    def load_combatants_via_file(self, file_path_a: str, file_path_b: str):
        try:
            if not file_path_a:
                file_path_a = "tomls\\combatant_a.toml"
            self.combatant_a = load_combatant(file_path_a)

            if not file_path_b:
                file_path_b = "tomls\\combatant_b.toml"
            self.combatant_b = load_combatant(file_path_b)

            logger.info(f"Loaded {self.combatant_a.name} as combatant A")
            logger.info(f"Loaded {self.combatant_b.name} as combatant B")
        except Exception as e:
            logger.error(f"Error loading combatants: {e}")

    def load_combatants(self, combatant_a: Combatant, combatant_b: Combatant):
        self.combatant_a = combatant_a.model_copy(deep=True)
        self.combatant_b = combatant_b.model_copy(deep=True)

    def load_terrain(self, terrain: Terrain):
        self.terrain = terrain.model_copy(deep=True)

    def view_combatants_and_terrain(self):
        if not self.combatant_a or not self.combatant_b:
            print("Please load both combatants first.")
            return

        terrain_txt = "No terrain loaded."
        if self.terrain:
            # fmt: off
            terrain_txt = (
                f"--- Terrain: {self.terrain.name} ---\n"
                f"{self.terrain.description}"
            )
            # fmt: on

        print(
            f"--- Combatant A: {self.combatant_a.name} ---\n"
            f"{self._format_combatant_stats(self.combatant_a)}\n\n"
            f"--- Combatant B: {self.combatant_b.name} ---\n"
            f"{self._format_combatant_stats(self.combatant_b)}\n\n"
            f"{terrain_txt}"
        )

    def _format_combatant_stats(self, combatant: Combatant) -> str:
        return (
            f"Armor: {combatant.armor}\n"
            f"Shields: {combatant.shields}\n"
            f"Ballistics: {combatant.ballistics}\n"
            f"Chemical: {combatant.chemical}\n"
            f"Firepower: {combatant.firepower}\n"
            f"Velocity: {combatant.velocity}\n"
            f"Effects: {', '.join(effect.name for effect in combatant.effects)}"
        )

    def modify_combatant(self, side: str, attribute: str, new_value: int):
        combatant = self.combatant_a if side.lower() == "a" else self.combatant_b
        if not combatant:
            logger.warning(f"Combatant {side.upper()} not loaded.")
            return

        if attribute not in ["armor", "shields", "ballistics", "chemical", "firepower", "velocity"]:
            logger.warning("Invalid attribute.")

        setattr(combatant, attribute, new_value)
        logger.info(f"Updated {attribute} to {new_value} for {combatant.name}")

    def load_terrain_via_file(self, file_path: str):
        try:
            self.terrain = load_terrain(file_path)
            logger.info(f"Loaded terrain: {self.terrain.name}")
        except Exception as e:
            logger.error(f"Error loading terrain: {e}")


class Battle(BaseModel):
    name: str
    terrain: str
    combatant_a: str
    combatant_b: str


class BattleConfig(BaseModel):
    battles: list[Battle]

    @staticmethod
    def load_battle_config(file_path: str = "tomls\\battle_config.toml") -> BattleConfig:
        with open(file_path, "rb") as f:
            data = tomli.load(f)
        cc = BattleConfig.model_validate(data)
        return cc


def load_combatant(file_path: str | Path) -> Combatant:
    with open(file_path, "rb") as f:
        data = tomli.load(f)
    c = Combatant.parse_obj(data)
    return c


def save_combatant(combatant: Combatant, file_path: str | Path) -> None:
    with open(file_path, "wb") as f:
        tomli_w.dump(combatant.dict(), f)


def load_terrain(file_path: str | Path) -> Terrain:
    with open(file_path, "rb") as f:
        data = tomli.load(f)
    return Terrain.parse_obj(data)


def save_terrain(terrain: Terrain, file_path: str | Path) -> None:
    with open(file_path, "wb") as f:
        tomli_w.dump(terrain.dict(), f)
