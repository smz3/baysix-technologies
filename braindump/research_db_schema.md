# research.db — Final Schema
_Last updated: 2026-05-29_

---

## Tables

---

### step1_ideas
| Column | Type | Note |
|--------|------|------|
| idea_id | TEXT | PK (e.g. "HMM-001") |
| name | TEXT | NOT NULL |
| description | TEXT | |
| category | TEXT | regime / signal / execution / risk |
| parent_idea_id | TEXT | FK → step1_ideas, CHECK(parent_idea_id != idea_id) |
| status | TEXT | ideation / gate_0 / gate_1 / ... / graduated / killed |
| kill_gate | INTEGER | which gate killed it (null if alive) |
| kill_reason | TEXT | the falsifying finding |
| killed_at | DATETIME | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

---

### step2_papers
| Column | Type | Note |
|--------|------|------|
| paper_id | INTEGER | PK AUTOINCREMENT |
| idea_id | TEXT | FK → step1_ideas |
| title | TEXT | NOT NULL |
| authors | TEXT | |
| year | INTEGER | |
| source | TEXT | arXiv / SSRN / Journal of Finance / etc. |
| url | TEXT | direct link |
| doi | TEXT | permanent identifier |
| local_path | TEXT | path to saved PDF |
| dissected | INTEGER | DEFAULT 0 (0=no, 1=yes) |
| key_equations | TEXT | |
| empirical_findings | TEXT | |
| context_fit | TEXT | does this apply to XAUUSD + our timeframe? |
| limitations | TEXT | |
| added_at | DATETIME | |
| dissected_at | DATETIME | |

---

### step3_gates
| Column | Type | Note |
|--------|------|------|
| gate_id | INTEGER | PK AUTOINCREMENT |
| idea_id | TEXT | FK → step1_ideas |
| gate_number | INTEGER | 0–6 |
| attempt | INTEGER | DEFAULT 1, UNIQUE(idea_id, gate_number, attempt) |
| gate_question | TEXT | what must be answered |
| gate_answer | TEXT | the actual answer |
| pass_criteria | TEXT | what pass looks like |
| status | TEXT | open / passed / blocked / killed |
| answered_by | TEXT | human / agent |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| answered_at | DATETIME | |

---

### step4_results
| Column | Type | Note |
|--------|------|------|
| result_id | INTEGER | PK AUTOINCREMENT |
| idea_id | TEXT | FK → step1_ideas |
| gate_number | INTEGER | which gate produced this |
| stage | TEXT | IS / walkforward / montecarlo / OOS |
| metric_key | TEXT | sharpe / t_stat / win_rate / net_edge / etc. |
| metric_value | REAL | |
| cost_adjusted | INTEGER | 0=raw, 1=net |
| period | TEXT | per_trade / daily / annualised |
| n_obs | INTEGER | observation count |
| n_trials | INTEGER | for PSR / deflated Sharpe |
| trial_family_id | TEXT | group of trials compared together |
| instrument | TEXT | DEFAULT 'XAUUSD' |
| data_start | DATE | |
| data_end | DATE | |
| parameters | TEXT | JSON string |
| git_sha | TEXT | code version that produced this result |
| data_hash | TEXT | proves no data leakage |
| seed | INTEGER | for montecarlo reproducibility |
| code_path | TEXT | path to script that ran this |
| notes | TEXT | |
| logged_at | DATETIME | |

---

### step5_agent_log
| Column | Type | Note |
|--------|------|------|
| call_id | INTEGER | PK AUTOINCREMENT |
| idea_id | TEXT | FK → step1_ideas |
| gate_number | INTEGER | which gate this belongs to |
| gear | TEXT | GENERATE / DISSECT / VALIDATE |
| model | TEXT | sonnet / opus / NULL (null when source='human') |
| source | TEXT | agent / human — replaces old generate_calls table |
| task_summary | TEXT | |
| output_summary | TEXT | |
| paper_id | INTEGER | FK → step2_papers (DISSECT calls only, else null) |
| result_id | INTEGER | FK → step4_results (VALIDATE calls only, else null) |
| created_at | DATETIME | |

---

## Views — Command Centre

---

### VIEW: idea_lifecycle
One row per idea. Full overview of where every idea stands.

```sql
CREATE VIEW idea_lifecycle AS
SELECT
    i.idea_id,
    i.name,
    i.category,
    i.parent_idea_id,
    i.status,
    COALESCE(p.papers_total, 0)     AS papers_total,
    COALESCE(p.papers_dissected, 0) AS papers_dissected,
    g.highest_gate_passed,
    i.kill_gate,
    i.kill_reason,
    i.created_at,
    i.updated_at
FROM step1_ideas i
LEFT JOIN (
    SELECT idea_id,
           COUNT(*)        AS papers_total,
           SUM(dissected)  AS papers_dissected
    FROM step2_papers
    GROUP BY idea_id
) p ON p.idea_id = i.idea_id
LEFT JOIN (
    SELECT idea_id,
           MAX(gate_number) AS highest_gate_passed
    FROM step3_gates
    WHERE status = 'passed'
    GROUP BY idea_id
) g ON g.idea_id = i.idea_id
```

---

### VIEW: gate_pipeline
Ideas stuck at open or blocked gates, ordered by days since last activity.

```sql
CREATE VIEW gate_pipeline AS
SELECT
    i.idea_id,
    i.name,
    g.gate_number,
    g.attempt,
    g.status        AS gate_status,
    g.gate_question,
    CAST((julianday('now') - julianday(g.updated_at)) AS INTEGER) AS days_since_activity
FROM step1_ideas i
JOIN step3_gates g ON g.idea_id = i.idea_id
WHERE g.status IN ('open', 'blocked')
  AND i.status NOT IN ('killed', 'graduated')
ORDER BY days_since_activity DESC
```

---

### VIEW: papers_queue
Undissected papers blocking Gate 0. Reading list for next session.

```sql
CREATE VIEW papers_queue AS
SELECT
    p.paper_id,
    p.idea_id,
    i.name  AS idea_name,
    p.title,
    p.authors,
    p.year,
    p.source,
    p.url,
    p.added_at
FROM step2_papers p
JOIN step1_ideas i ON i.idea_id = p.idea_id
WHERE p.dissected = 0
  AND i.status NOT IN ('killed', 'graduated')
ORDER BY p.added_at ASC
```

---

## Full Connection Map

```
step1_ideas (spine)
  ├── step2_papers     idea_id → papers read per idea
  ├── step3_gates      idea_id → protocol gates 0–6
  ├── step4_results    idea_id → all quantitative output
  └── step5_agent_log  idea_id → every agent call
                          ├── paper_id  → ties DISSECT to paper
                          └── result_id → ties VALIDATE to result

Views:
  idea_lifecycle   ← one row per idea, full overview
  gate_pipeline    ← ideas stuck at open/blocked gates
  papers_queue     ← undissected papers blocking Gate 0
```

---

## Gate Reference (fixed in protocol)

| Gate | Name | Question to answer |
|------|------|--------------------|
| 0 | Understand | Do we know the model's mathematical truth from literature? |
| 1 | Frame | What is the simple human-readable rule + null hypothesis? |
| 2 | Foundation | Does the simplest possible version produce sane output? |
| 3 | Baseline | Does the dumb rule have any edge (raw + after costs)? |
| 4 | Model | Does the sophisticated model confirm or challenge the baseline? |
| 5 | Signal | Is there a tradeable signal with positive net edge (t-stat, PSR)? |
| 6 | Validate | Does the edge survive walk-forward and OOS? |

---

## Design Rules

1. Everything traces back to `idea_id` — no orphan rows.
2. Gate N cannot pass unless Gate N-1 is passed — enforced in code layer.
3. Results without `git_sha`, `data_hash`, `n_obs` are not valid results.
4. Kill reason is mandatory when `status = killed` — research IP is why ideas die.
5. `cost_adjusted = 0` (raw) and `cost_adjusted = 1` (net) must both be logged for Gate 3 and Gate 5.
6. `period` must be explicit on every metric — never ambiguous between per_trade / daily / annualised.
