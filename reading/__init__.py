"""Reading engine — how the day gets its sentence.

Mirrors the framework's own module split (FOUR · READING ENGINE):

    detect.py     chart + pañcāṅga + gocara -> weighted condition hits
    select.py     rank by weight, seeded pick per slot
    compose.py    fragments -> statement, with the emphasis span marked
    fragments.py  the authored library

No network, no model, no randomness that isn't reproducible: the same person
on the same day gets the same sentence forever.
"""
from .compose import Reading, read_day
from .detect import Conditions, Hit, detect
from .fragments import FRAGMENTS, Fragment
from .select import rank, pick_variant

__all__ = ["Reading", "read_day", "Conditions", "Hit", "detect",
           "FRAGMENTS", "Fragment", "rank", "pick_variant"]
