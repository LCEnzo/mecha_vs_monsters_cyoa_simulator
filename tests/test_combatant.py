from mvm.core import AttackType
from tests.utils import create_combatant


def test_combatant_creation():
    c = create_combatant(111, 55)
    assert c.name == "Test Combatant"
    assert c.armor == 111
    assert c.shields == 55


def test_combatant_damage():
    c = create_combatant(100, 50)
    c.apply_damage(30, AttackType.BALLISTIC)
    assert c.shields == 20
    assert c.armor == 100

    # Checks shield overdamage, so that we don't have negative values
    c.apply_damage(30, AttackType.BALLISTIC)
    assert c.shields == 0
    assert c.armor == 100

    c.apply_damage(30, AttackType.BALLISTIC)
    assert c.shields == 0
    assert c.armor == 70

    # Checks armor overdamage, so that we don't have negative values
    c.apply_damage(9999, AttackType.BALLISTIC)
    assert c.shields == 0
    assert c.armor == 0


def test_chemical_damage():
    c = create_combatant(100, 100)
    c.apply_damage(100, AttackType.CHEMICAL)
    assert c.shields == 50
    assert c.armor == 100

    c.apply_damage(100, AttackType.CHEMICAL)
    assert c.shields == 0
    assert c.armor == 100

    c.apply_damage(25, AttackType.CHEMICAL)
    assert c.shields == 0
    assert c.armor == 50

    c.apply_damage(25, AttackType.CHEMICAL)
    assert c.shields == 0
    assert c.armor == 0


def test_firepower_damage():
    c = create_combatant(100, 100)
    c.apply_damage(25, AttackType.FIREPOWER)
    assert c.shields == 50
    assert c.armor == 100

    c.apply_damage(25, AttackType.FIREPOWER)
    assert c.shields == 0
    assert c.armor == 100

    c.apply_damage(100, AttackType.FIREPOWER)
    assert c.shields == 0
    assert c.armor == 50

    c.apply_damage(50, AttackType.FIREPOWER)
    assert c.shields == 0
    assert c.armor == 25
