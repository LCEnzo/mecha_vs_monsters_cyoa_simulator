from mvm.core import Combatant


def create_combatant(
    armor: int = 50, shields: int = 50, ballistics: int = 10, chemical: int = 10, firepower: int = 10, velocity: int = 5
) -> Combatant:
    c = Combatant(
        name="Test Combatant",
        armor=armor,
        shields=shields,
        ballistics=ballistics,
        chemical=chemical,
        firepower=firepower,
        velocity=velocity,
    )
    return c
