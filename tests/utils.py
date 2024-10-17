from mvm.core import Combatant


def create_combatant(
    armor: int = 50,
    shields: int = 50,
    ballistics: int = 10,
    chemical: int = 10,
    firepower: int = 10,
    velocity: int = 5,
    name: str = "Test Combatant",
) -> Combatant:
    c = Combatant(
        name=name,
        armor=armor,
        shields=shields,
        ballistics=ballistics,
        chemical=chemical,
        firepower=firepower,
        velocity=velocity,
    )
    return c
