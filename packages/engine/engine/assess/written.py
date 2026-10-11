"""Every written method by its name, multiplication's (`written_methods`, ADR 0055) and division's (`divide_methods`,
ADR 0063): the kind of question that prints it, whether it can set out two numbers, and the question it makes. The
drawer, the bank's stale keys and the placing read the methods here, so a method is one name whatever it divides or
multiplies. Partitioning prints either operation's: 23 × 4 and 72 ÷ 4 are both a line for each part, then the total.
Pure, no I/O."""

from . import divide_methods as DVM
from . import written_methods as WM
from .items import Item

KINDS = {**WM.KINDS, **DVM.KINDS}  # the method → the kind of question that prints it


def prints(method: str, a: int, b: int) -> bool:
    """Whether the method can set out these two numbers: a multiplication's needs no zero, a division's its own rule."""
    return WM.prints(a, b) if method in WM.WORK else DVM.prints(method, a, b)


def make(method: str, a: int, b: int, rung: str) -> Item:
    """The question `a` and `b` make in the method, a box for every step."""
    return (WM.make if method in WM.WORK else DVM.make)(method, a, b, rung)
