# Third-party material in the Athena harness

Vendored on 10 Oct 2026 with Nimish's written approval. Each file was screened before vendoring: no network calls beyond git and localhost, and no instruction overrides. Licences are in `licenses/`.

| What | Where it lives here | Source (commit) | Licence |
| --- | --- | --- | --- |
| constraint-driven-development, documentation-and-adrs, security-and-hardening skills; definition-of-done (from `references/`) | `.claude/skills/<name>/` | addyosmani/agent-skills (`1be8e34187e34647bb83adc3a1323b26ae6f6abe`) | MIT |
| thinking-out-loud, scope-creep-detector, first-reader skills | `.claude/skills/<name>/` | Shubhamsaboo/awesome-llm-apps, `agent_skills/` (`4bf51ab704fb2c5b3803cd5191b30d7dcdb51dc2`) | Apache-2.0 |
| strategic-compact skill and its `suggest-compact.js` hook with four library files | `.claude/skills/strategic-compact/` | affaan-m/everything-claude-code (`4eb71d92a39cab44ad40ac9d8a6a5ccb4029d6c2`) | MIT |
| constitution and converge, adapted from commands to skills with an Athena name map | `.claude/skills/constitution/`, `.claude/skills/converge/` | github/spec-kit, `templates/` (`0443760542e7e5269724744a2ac55c4bd386d095`) | MIT |
| reality-checker, software-architect and appsec-engineer reviewer personas | `.claude/agents/<name>.md` | msitarzewski/agency-agents (`f99f6aa910a442b0197b768ce0ea7751e35e2060`) | MIT |
| Superpowers skills (planning, test-first building, debugging, review) | `.claude/skills/<name>/` | obra/superpowers v7 (see `SUPERPOWERS-NOTICE.md`) | MIT |
| archify skill, without its 13MB of rendered example pages (the example inputs it needs to run are kept) | `.claude/skills/archify/` | tt-a1i/archify, `archify/` (`b25142deac4b19b293e45b6bf6d69351d3c8f3b6`) | MIT |
| pentest skill: Athena's own instructions for running Strix; no Strix code is vendored | `.claude/skills/pentest/` | usestrix/strix (installed per machine with `pipx install strix-agent`) | Apache-2.0 |
| "Four rules for every change" in `CLAUDE.md`: paraphrased from the Karpathy-inspired guidelines, no text vendored | `.claude/athena/CLAUDE.md` | multica-ai/andrej-karpathy-skills, `CLAUDE.md` (`2c606141936f1eeef17fa3043a72095b4765b9c2`) | MIT |
| autoharness plugin | `.claude/plugins/autoharness/` | tigerless-labs/autoharness (`9eec6232587ff2c4deeded00ac467de19532d763`) | MIT |
| spending-effort-with-jev plugin (Jev effort advisor) | `.claude/plugins/spending-effort-with-jev/` | Yaxin9Luo/spending-effort-with-jev, `plugins/spending-effort-with-jev/` (`8aef59d72e932d362d5b404ed839290f04db3bb0`) | MIT |
| toolgate plugin (its CLI is installed per machine, `@riskaverse/toolgate@0.16.0`) | `.claude/plugins/toolgate/` | RiskAverseTech/toolgate, `plugin/` (`31e8a2a72e4d05594be78d4588b170744020253d`) | MIT |
| winnow plugin | `.claude/plugins/winnow/` | GhalebDweikat/winnow (`4547a81b88ac59a902bad7b0006137c7d4147aeb`) | MIT |
| fast-jev-compaction plugin | `.claude/plugins/fast-jev-compaction/` | tamaratran/fast-jev-compaction (`e3f262a7f4d42bd8dd32ced30d26176f7cb545b0`) | MIT |
| jev plugin (jevwire) | `.claude/plugins/jev/` | Brainwires/jevwire, `plugin/` (`757468d6743f55225b9635e1d5f24524da79c2bc`) | MIT |
| ponytail plugin | `.claude/plugins/ponytail/` | DietrichGebert/ponytail (`9b58c1ffb790c075ca32e70a89cf1d80588f4abf`) | MIT |

The seven plugins above were vendored on 7 Nov 2026 (ATH-16) by `athena-ops/harness/vendor_plugins.py`, at the commits pinned in `athena-ops/.claude-plugin/marketplace.json` and recorded in `.claude/plugins/plugins.lock.json`. Each folder is the plugin's own, unchanged, without its tests, docs, images, demos and CI files; each keeps its LICENSE (jevwire's and toolgate's come from their repository root). Canny and rtk are installed on each machine by `mac-setup.sh` or `cloud-setup.sh`.
