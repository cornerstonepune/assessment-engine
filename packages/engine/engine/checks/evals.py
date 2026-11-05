"""The evals `engine eval` runs that take only the prompt version they score, and every eval's verdict against its
bars (goals/p1-done-means-every-check.yaml). Out of `cli.py`, which was at its ceiling, when the curriculum mapping
agents' eval joined them (goals/m1-05-mapping-agents.yaml)."""

import json
from pathlib import Path

import typer

from engine.adapters.llm import LLMError
from engine.checks import bars
from engine.core import db
from engine.w1_bank import cli_map, generate, story_eval, story_shape
from engine.w1_bank.k2_upload import curriculum_app
from engine.w1_bank.map_agents import model_ask, recorded_ask
from engine.w2_print import materials_read_eval


def unanswered(r, n):
    """A Jev eval Jev did not answer fails and says why: with no key it used to score as nothing chosen, and pass."""
    if r["unanswered"]:
        typer.echo(f"JEV  not answered on {r['unanswered']} of {n}: {r['error']}", err=True)
        raise typer.Exit(1)


def of(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def held(purpose: str, scores: dict[str, float]) -> None:
    """An eval's scores against its bars, rows in `threshold` (`checks.bars`): it exits 1 below any bar, or with none
    on record (goals/p1-done-means-every-check.yaml)."""
    with db.connect() as conn:
        missed = bars.short(scores, bars.bars(conn, purpose))
    for m in missed:
        typer.echo(f"  BELOW  {purpose}: {m}", err=True)
    if missed:
        raise typer.Exit(1)
    typer.echo(f"  {purpose}: every bar met")


def _eval_english_generate(version: int, *_: object) -> None:
    """english_generate: the share of the questions written for the fixed samples that pass every check."""
    with db.connect() as conn:
        try:
            r = generate.evaluate(conn, version or None)
        except LLMError as e:
            conn.commit()
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
        conn.commit()  # the flow_run rows: what the eval spent; nothing else is written
    typer.echo(json.dumps(r, indent=2, ensure_ascii=False))
    typer.echo(f"english_generate v{version or 'active'}: {r['kept']}/{r['returned']} passed every check")
    return held(generate.PURPOSE, {"kept": of(r["kept"], r["returned"])})


def _eval_story_shape(version: int, *_: object) -> None:
    """story_shape: stories placed in the right case, and one-step answers computed right."""
    with db.connect() as conn:
        r = story_eval.evaluate(conn, version=version or None)
        conn.commit()
    for m in r["misses"]:
        typer.echo(
            f"  {'LEFT' if m['got'] is None else 'MISS':<5} {m['text'][:60]}  wanted {m['want']}, {m['got'] or m['why']}"
            + "".join(f"\n          Jev: {o} {p:.2f}" for o, p in m.get("ranked") or [])
        )
    typer.echo(
        f"  {story_shape.PURPOSE}: named {r['named']}/{r['n']}, the shape right on {r['right']} · one-step answers computed"
        f" {r['keyed']}, wrong {r['wrong_answer']} · left for a person {r['left']}"
    )
    unanswered(r, r["n"])
    return held(
        story_shape.PURPOSE, {"shape_right": of(r["right"], r["n"]), "wrong_answers": r["wrong_answer"]}
    )


def _curriculum_map(r: dict[str, float]) -> None:
    typer.echo(
        f"  {cli_map.PURPOSE}: {int(r['n'])} held out · every skill right {r['skill_all_right']:.3f} · people's"
        f" skills found {r['skill_found']:.3f} · passed on their own {r['auto_passed']:.3f}"
    )
    held(cli_map.PURPOSE, r)


def _kept(conn, ask):
    """Each call's flow_run row (cost, prompt version, the reply and why it was refused) is committed as it is made, so
    a run that dies afterwards still has what it spent and what it was told."""

    def keep(*a, **k):
        try:
            return ask(*a, **k)
        finally:
            conn.commit()

    return keep


def _eval_curriculum_map(version: int, dev: bool = False, validate_version: int = 0) -> None:
    """curriculum_map: the agents map the held-out share of what people mapped, blind (or, with `dev`, the dev set);
    the model's replies (on the box, where the key is). `version` is the proposer's, `validate_version` the checker's.
    The calls spend from the campaign's `dev_eval` or `held_out` stage."""
    stage = "dev_eval" if dev else "held_out"
    with db.connect() as conn:
        try:
            ask = _kept(conn, model_ask(conn, version or None, validate_version or None, stage, typer.echo))
            r = cli_map.evaluate(conn, ask, dev=dev)
        except LLMError as e:
            conn.commit()
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
        conn.commit()  # the flow_run rows: what the eval spent; nothing else is written
    _curriculum_map(r)


@curriculum_app.command("eval")
def curriculum_eval(
    recorded: Path = typer.Option(..., "--recorded", help="A recorded run's replies"),
) -> None:
    """Score a recorded run of the mapping agents on the held-out share; exits 1 below any bar."""
    with db.connect() as conn:
        conn.read_only = True
        r = cli_map.evaluate(conn, recorded_ask(recorded))
    _curriculum_map(r)


def _eval_materials_read(version: int, *_: object) -> None:
    """materials_read: what code let through from the model's readings of marked requests (M1-16)."""
    with db.connect() as conn:
        try:
            scores = materials_read_eval.evaluate(conn, version or None)
        except materials_read_eval.NoGold as e:
            typer.echo(f"NO GOLD  {e}", err=True)
            raise typer.Exit(1)
        except LLMError as e:
            conn.commit()
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
        conn.commit()  # the flow_run rows: what the eval spent; nothing else is written
    typer.echo("  " + " · ".join(f"{k} {v:.3f}" for k, v in scores.items()))
    held("materials_read", scores)


# the scorers `engine eval` hands (version, dev, validate_version); most use only the version they score
BY_VERSION = {
    generate.PURPOSE: _eval_english_generate,
    story_shape.PURPOSE: _eval_story_shape,
    cli_map.PURPOSE: _eval_curriculum_map,
    materials_read_eval.PURPOSE: _eval_materials_read,
}
