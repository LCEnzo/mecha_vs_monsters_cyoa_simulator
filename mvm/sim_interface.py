from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import TypedDict

import tomli
import tomli_w
from pydantic import BaseModel, Field
from termcolor import colored

from mvm.core import BattleState, Combatant, End, RoundEnd, Start, Terrain
from utils.log_util import logger
from utils.settings import settings


class BattleResults(TypedDict):
    combatant_a: int
    combatant_b: int


class BattleSimulator(BaseModel):
    main_a: Combatant | None = None
    adds_a: list[Combatant] = Field(default_factory=list)
    main_b: Combatant | None = None
    adds_b: list[Combatant] = Field(default_factory=list)
    terrain: Terrain | None = None
    current_state: BattleState | None = None
    random_seed: int | None = None

    def start_battle(self) -> None:
        if not self.main_a or not self.main_b:
            logger.warning("Please load both combatants before starting a battle.")
            if settings.is_debug():
                raise Exception()
            return

        logger.info("Battle started.")

        kwargs = {}
        if settings.is_debug() and self.random_seed is None:
            kwargs["random_seed"] = 0
        else:
            kwargs["random_seed"] = self.random_seed

        self.current_state = Start.initialize(
            main_a=self.main_a.model_copy(deep=True),
            adds_a=[m.model_copy(deep=True) for m in self.adds_a],
            main_b=self.main_b.model_copy(deep=True),
            adds_b=[m.model_copy(deep=True) for m in self.adds_b],
            terrain=self.terrain.model_copy(deep=True) if self.terrain else None,
            **kwargs,
        )

    def run_battle(self) -> None:
        if self.current_state is None or isinstance(self.current_state, End):
            self.start_battle()
        while self.current_state is not None and not isinstance(self.current_state, End):
            self.current_state = self.current_state.transition()
            assert self.current_state.round_count != 300
        logger.info(self.get_battle_result())

    def run_round(self, until: type[BattleState] = RoundEnd) -> None:
        assert until is not BattleState

        if self.current_state is None or self.current_state == End:
            self.start_battle()
        while self.current_state is not None and not isinstance(self.current_state, (until, RoundEnd)):
            self.current_state = self.current_state.transition()
        if self.current_state is not None and isinstance(self.current_state, (until, RoundEnd)):
            self.current_state.transition()
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

    def print_multiple_battle_results(self, total_rounds: int, num_battles: int, results: BattleResults):
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

    def run_multiple_battles(self, num_battles: int) -> tuple[BattleResults, float]:
        results: BattleResults = {"combatant_a": 0, "combatant_b": 0}
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
                self.run_battle()
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

    def load_combatants_via_file(self, file_path_a: str, file_path_b: str) -> None:
        try:
            if not file_path_a:
                file_path_a = "tomls\\combatant_a.toml"
            self.main_a = load_combatant(file_path_a)

            if not file_path_b:
                file_path_b = "tomls\\combatant_b.toml"
            self.main_b = load_combatant(file_path_b)

            logger.info(f"Loaded {self.main_a.name} as combatant A")
            logger.info(f"Loaded {self.main_b.name} as combatant B")
        except Exception as e:
            logger.error(f"Error loading combatants: {e}")

    def load_combatants(self, main_a: Combatant, main_b: Combatant) -> None:
        self.main_a = main_a.model_copy(deep=True)
        self.main_b = main_b.model_copy(deep=True)

    def load_terrain(self, terrain: Terrain) -> None:
        self.terrain = terrain.model_copy(deep=True)

    def view_combatants_and_terrain(self) -> None:
        if not self.main_a or not self.main_b:
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
            f"--- Combatant A: {self.main_a.name} ---\n"
            f"{self._format_combatant_stats(self.main_a)}\n\n"
            f"--- Combatant B: {self.main_b.name} ---\n"
            f"{self._format_combatant_stats(self.main_b)}\n\n"
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

    def modify_combatant(self, side: str, attribute: str, new_value: int) -> None:
        combatant = self.main_a if side.lower() == "a" else self.main_b
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

    def get_round_count(self) -> int | None:
        return self.current_state.round_count if self.current_state else None

    def is_battle_over(self) -> bool:
        # TODO: Consider what to do with current_state == None
        return self.current_state is None or isinstance(self.current_state, End)


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
