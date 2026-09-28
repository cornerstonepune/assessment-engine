"""What a person has checked on a paper: the answers they signed off or corrected. A reading never overwrites them.

A re-read that superseded the capture this work hangs from would take it out of every screen and the graph, which
read only live captures — the first guard counted sign-offs only, and a re-read took six of Nimish's corrections on a
paper he had not yet signed off. So a paper a person has worked on is read again into the same capture, and only the
answers nobody has touched take the new reading (Nimish, 2026-09-28: "yes, go ahead with the partial re-read").
"""

# appended to the reading's upsert: an answer a person signed off or corrected keeps its row exactly as they left it
UNTOUCHED = (
    " where item_result.state <> 'confirmed'"
    " and not exists (select 1 from read_correction rc where rc.item_result_id = item_result.id)"
)


def worked_on(conn, capture_id):
    """How many answers on this capture a person has signed off or corrected."""
    return conn.execute(
        "select (select count(*) from item_result where capture_id = %s and state = 'confirmed')"
        " + (select count(*) from read_correction where capture_id = %s) as n",
        (capture_id, capture_id),
    ).fetchone()["n"]
