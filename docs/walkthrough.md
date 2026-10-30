# 3-minute walkthrough: Marketing Mix Model & Attribution on GA4 Data

A timed script for a Loom recording of about 3 minutes (screen plus camera bubble, 1080p). Say it in your own words; the lines are a guide, not a teleprompter.

**Open these tabs before you press record:** README, `dbt/models/intermediate/int_ga4__sessions.sql`, `dbt/models/marts/rpt_attribution_rules.sql`, `attribution/markov.py`, `results/attribution_revenue_share.csv`, `mmm/simulate.py`, `results/mmm_roi_vs_truth.csv`, `results/mmm_holdout.png`, GitHub Actions.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | Portfolio card, then the README title | Marketing asks two questions: which channels drive sales, and where should next quarter's budget go. This project answers both, and checks whether the answers can be trusted. |
| 0:20–0:40 | README Data section | Attribution uses Google's real GA4 sample from its Merchandise Store: 4.3 million events. The mix model uses simulated spend, because no public data pairs real spend with a known true return, so here I can score the model against the truth. |
| 0:40–1:05 | `int_ga4__sessions.sql` | This export doesn't put the source on session start, so each session takes it from its first tagged event, and the store referring to itself counts as Direct. Google obfuscates some sources; those are Unknown, 42% of sessions, and I say so rather than guess. |
| 1:05–1:35 | `rpt_attribution_rules.sql`, then the attribution table | Five rule-based models in SQL, plus a Markov model that credits each channel by how many sales would be lost without it. Direct gets 39% of revenue under last click and 14% under last non-direct. The model you pick decides what you fund. A test proves every model hands out exactly the $340,647. |
| 1:35–2:00 | `mmm/simulate.py` and the ROI table | The mix model: three years of weekly revenue, four channels with carry-over and diminishing returns, and known true returns. Fitted on spend alone, it gets search right but gives online video three times its true ROI. Add one lift experiment and video lands at 1.14 against a true 1.10. |
| 2:00–2:25 | `mmm_holdout.png`, then the budget table | Both models forecast unseen weeks within 3.6%, so fit can't separate them. But when I score their budget plans on the true curves, neither beats today's allocation: they promise gains and lose money, because budget moves depend on marginal returns, which the data doesn't pin down. |
| 2:25–2:45 | README: the social lift test | And one experiment came in unlucky, more than two standard errors low. I kept the seed and showed it. That's the case for repeating tests, not trusting one. |
| 2:45–3:00 | Back to the README top | For a marketing team: compare attribution models before funding decisions, and use the mix model to choose the next experiment, not to move budget on its own. Links are under the video. |

## Recording checklist
- Close email, chat and notifications. Zoom the browser to 125% so code is readable.
- Don't run the pipeline live: the GA4 download is 1.8 GB and the MMM takes minutes. Show the CI run and the results files.
- Keep to one take per section; Loom lets you trim. Aim for 2:45 to 3:10.
- Show real numbers on screen as you say them; never estimate on camera.
- Say "real" for the GA4 part and "simulated" for the mix-model part, every time.

## After recording
1. Copy the Loom share link.
2. In `README.md`, replace the walkthrough line with `- [x] [3-minute Loom walkthrough](<your Loom link>)` and add the link under the title.
3. Add the link to this project's card on saigwe.github.io.
