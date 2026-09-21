"""How much working space each kind of question is printed with, in lines.

Every generator in `items.py` and `words.py` gives its own kind exactly this. A question read back
from the bank has no generator to ask, so `bank.item_from_row` asks here. Before this table it asked
`verify.FORMATS`, which knows four kinds, and eight of the twelve kinds in the bank could not be
printed at all. `test_items` fails the moment a generator and this table disagree.
"""

WORKING_LINES = {
    "column_grid": 0,
    "bare_sum": 3,
    "missing_number": 1,
    "word_1step": 3,
    "word_2step": 4,
    "balance_scale": 1,
    "number_wall": 0,
    "number_line_jumps": 0,
    "estimate_then_calc": 2,
    "efficient_method": 3,
    "explain_claim": 3,
    "find_mistake": 2,
    "missing_digit": 2,
    "digit_cards": 3,
    "partition_scaffold": 0,
    "sort_into_table": 0,
    "partial_worked": 0,
}
