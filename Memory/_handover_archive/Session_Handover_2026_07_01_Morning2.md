# Handover — July 1, 2026 Morning2

## State
- **research.db UNTRACKED + gitignored** (task 203 done). Hit 675MB after run_id 18 (8yr FOB ingest) > GitHub 100MB cap. Now local-only at `research/db/research.db`; rebuild path documented in `.gitignore`.
- **Committed + pushed** `db3fad0` (HEAD == origin/master). The last tracked DB blob (78d8f12, 88MB) pushed fine; new commit drops the DB from tracking.
- **run_id 18 now backed up off-disk** — emit CSV (403MB / 422,278,440 bytes) copied byte-exact to `G:\My Drive\baysix_backups\fob_emit\` (Drive for Desktop, upload confirmed by Syafiq).
- **.git reclaimed 1.7GB → 160MB** via `git gc --prune=now` (dropped dangling 135/125MB loose blobs + unreachable DB revisions; reachable history + push state untouched).
- No code/strategy change this session — pure infra/DB-git resolution.

## Next
1. **(task 204 P1)** Interrogate flipped alignment result (result_id 19): full-stack `full_cont=0.06` is extreme — confirm the ~4.5% aligned cohort isn't a degenerate/mechanical subset (htf_state snapshot at a turning point) before trusting "aligned = fade/exhaustion".
2. **(task 202 P2)** ingest_fob phase-2b: add `mfe_r`/`mae_r` excursion (signed R) + `is_primary`/`superseded_by`/`zone_key` supersede logic to Tier-C (realized_r is still a ±label, not true exit-R).

## Blockers
- None. DB-push blocker resolved (untracked); off-disk backup done.

## Why
- **Chose untrack+gitignore over Git-LFS** (task 203). LFS-migrate would force a history rewrite + force-push of shared master AND blow GitHub's free 1GB LFS quota (675MB + revisions). The DB is **derived/rebuildable from the emit CSV via ingest_fob**, so it doesn't belong in git. Untrack costs nothing reversible and unblocks push permanently.
- **Backup target = the CSV, not the DB.** The 403MB emit CSV is the source of truth; the DB reconstitutes from it. So backing the CSV off-disk (Google Drive) is the real data-loss fix — the DB itself never needs to leave this disk.
- **Drive synced-folder over the MCP plugin** — the Google Drive MCP is built for Docs/small files; a 403MB binary through it = base64 bloat + timeouts. `G:\My Drive` (Drive for Desktop) mounts a local folder → plain `cp` + background sync is the correct path.
- **gc was safe** — `git gc --prune=now` only drops UNREACHABLE objects; the 1.7GB→160MB collapse means most weight was dangling blobs (loose 135/125MB + amended/reset DB versions), not reachable history. Push history unchanged.
- **The committed DB never actually exceeded 100MB** — HEAD's tracked blob was 88MB; the 675MB was the *uncommitted working tree*. The original "push BLOCKED" would only have triggered on committing the 675MB blob. Corrected the prior handover's framing.

## Ruled-Out
- **Git-LFS for the DB** — rejected: force-push of shared master + 1GB free-LFS quota trap. Do not revive unless the DB must be remote-shareable AND a paid LFS plan exists.
- **Google Drive MCP plugin for the 403MB upload** — rejected: wrong tool for large binaries. Use the Drive for Desktop synced folder (`G:\My Drive`).
- **History rewrite to purge old DB blobs** — unnecessary: all committed DB blobs ≤88MB (under cap, already pushed); gc reclaimed the dangling space without touching refs.

## Live-Threads
- **full_cont = 0.06 still un-interrogated** (folded into task 204) — could be a genuine exhaustion/reversal edge OR a mechanical artifact (htf_state captured at a turning point). Not trusted/tradeable until the cohort sanity-check is done.
- **CSV backup is one-shot** — only `v1.25.0_20160614_0000.csv` is in Drive. Any future re-emit (new version) needs its own copy to `G:\My Drive\baysix_backups\fob_emit\`; no auto-sync of the MT5 Files folder is set up.
