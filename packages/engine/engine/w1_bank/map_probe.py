"""One question to the proposer, to see the vendor take its request (goals/m1-11j-map-probe.yaml).

The proposer's reply shape is handed to the vendor (M1-11e, `llm.structured`). Whether the vendor accepts that request is
only known by asking. One activity, one call, asked exactly as the eval asks it, answers two things: the HTTP status, and
whether the reply passes the local check. It returns one line of those two facts and nothing the call carried: the log of
the run is public, and neither a school's words nor a reply may reach it.
"""

import re

from engine.adapters import llm
from engine.w1_bank.map_agents import PROPOSE, Ask, Band, _context

LABEL = "probe:"  # on the row's `about`: the replay of a dev run reads past these (map_replay.stored)
STATUS = re.compile(r"\bHTTP (\d{3})\b")


def probe(band: Band, code: str, examples: int, ask: Ask) -> str:
    """Ask the proposer about `code` alone (its links hidden in `band`, as in the eval) and say what came back."""
    try:
        ask(PROPOSE, LABEL + code, _context(band, code, ["skill"], examples))
    except llm.LLMSchemaError:
        return "HTTP 200; the reply broke the local check"
    except llm.LLMError as e:
        found = STATUS.search(str(e))
        if found:
            return f"HTTP {found[1]}; no reply"
        return f"no HTTP status; the call was not made or did not arrive ({type(e).__name__})"
    return "HTTP 200; the reply passed the local check"
