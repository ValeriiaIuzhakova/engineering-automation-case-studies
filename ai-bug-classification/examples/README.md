# Illustrative examples (non-production)

> **Not production code.** These files were written from scratch for this portfolio to show the
> design ideas. They use synthetic tickets, a fictional taxonomy, a scripted fake model and
> illustrative thresholds. They are not the production workflow and do not reproduce its code,
> prompts, configuration or data.

Requires Python 3.9+, standard library only.

```bash
python3 pipeline.py --reset    # classify the synthetic tickets
python3 pipeline.py            # run again: every ticket is skipped, 0 model calls
python3 calibration.py         # is confidence actually informative?
python3 -m unittest test_pipeline -v
```

| File | What it demonstrates |
|---|---|
| `pipeline.py` | Two-stage classification (area, then type); strict validation against a versioned taxonomy; one retry on malformed output; three outcomes; write gate; a comment on every outcome; eligibility rule that protects existing values; content-hash idempotency; append-only audit log |
| `calibration.py` | Checking whether self-reported confidence tracks real accuracy *before* choosing thresholds |
| `fake_llm.py` | Scripted model responses, including broken JSON, values outside the taxonomy and non-numeric confidence |
| `test_pipeline.py` | 13 tests covering the behaviours above |
| `taxonomy.json`, `bugs.json` | Synthetic inputs for a fictional project-management app |

Expected first run:

```
Ticket     Outcome                     Area               Type
DEMO-101   auto_apply                  Boards & Cards     Regression
DEMO-102   auto_apply                  Calendar Sync      Integration    (after one retry)
DEMO-103   not_classified              None               None           (too vague)
DEMO-104   needs_review                None               None           (off-taxonomy, then 0.78)
DEMO-105   skipped_human_classified    Billing            None
DEMO-106   not_classified              None               None           (confidence "high")
```

The retry and the content-hash idempotency key are design extensions for this demo. They are not
claims about how the production system was built. To keep the demo short, it also gates both
fields together, using the lower of the two confidences. The design described in the case study
gates each field independently.
