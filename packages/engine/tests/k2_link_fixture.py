"""Two links for the browser test of M1-17 (apps/web/tests/m1-17-k2-picture-and-child.spec.ts): `after` follows `before`
and is CONFIRMED by a member of staff; `proposed` follows `before` and is only PROPOSED. Run from packages/engine as
`python tests/k2_link_fixture.py <before> <after> <proposed>`. It lives here, not in the browser spec, because no web code
may name the raw link tables (tests/test_skill_links_confirmed.py): the web only ever reads the confirmed view. Placeholder
rows for a test database; a second run changes nothing."""

import sys

from engine.core import db


def main(before: str, after: str, proposed: str) -> None:
    with db.connect() as conn:
        t = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        staff = conn.execute("select staff_id from pii.staff order by created_at limit 1").fetchone()[
            "staff_id"
        ]
        for skill, status in ((after, "confirmed"), (proposed, "proposed")):
            conn.execute(
                "insert into skill_link (tenant_id, skill_code, before_code, strength, reason, source, status,"
                " confirmed_by, confirmed_at) values (%s, %s, %s, 'hard', 'a test reason', 'm1-17 test', %s, %s,"
                " case when %s = 'confirmed' then now() end) on conflict (tenant_id, skill_code, before_code) do nothing",
                (t, skill, before, status, staff if status == "confirmed" else None, status),
            )
        conn.commit()


if __name__ == "__main__":
    main(*sys.argv[1:4])
