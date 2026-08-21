# Does a stance change how someone reacts to a real ad? — PRE-REGISTERED

**2026-08-22. `$3.64`. Written and committed BEFORE the run.**

⚠⚠ **THIS TEST EXISTS BECAUSE THE USER CAUGHT ME OVERCLAIMING.** In `#73` I reported *"eight
people, eight different reasons to reject the same ad."* **NO AD WAS RUN.** That table was **my
inference from reading the eight `l4_stance` lines**, and I presented it as a result. The
pre-registration was honest (*"would PLAUSIBLY react differently... judged on `l4_stance`"*); my
write-up to the user was not.

⭐⭐ **AND THE DEEPER FLAW: I wrote the pack, I wrote the criterion, and then I marked the output
against an ad I imagined.** Three layers of self-marking. This test replaces the middle layer with
measurement — **and locks my predictions below so the inference itself is falsifiable.**

## THE RIG

```
.venv/bin/python batch_run.py \
  --asset assets/twt_protein_bar.png --asset-label "The Whole Truth protein bar" \
  --audience-spec specs/fnb_probe_afternoon.json --category fnb_world \
  --brand-profile fnb_probe_v1 --library-id fnb_probe_v1_lib --account demo
```

**Panel 64 across 24 segments = 8 agents per stance.** The eight probe types from `#73`, installed
into a **fresh library** (`fnb_probe_v1`) — ⚠ **not appended to the snacking-era population**; two
packs in one library is a market that does not exist, and the pack-mismatch guard exists for it.
⚠ The install's saved audience carries only **3 of 8** types (stratified selection); the run
resolves the **AudienceSpec against the LIBRARY**, so the explicit 8-label spec seats all eight.
**Verified by preflight: `resolved 8 dispositions`.**

## THE AD, AND WHY THIS ONE

**The Whole Truth energy bar.** *"100% Clean Energy. for your body!"* — mocha almond fudge,
**5g protein**, vegan / no added sugar / gluten-free / dairy-free, *"made with cashews, almonds,
dates, cocoa and coffee. That's all!"*

⭐⭐ **It is a clean-INGREDIENT ad, not a protein ad, and 5g is a low protein number.** That is why
it is the right stimulus: it gives each stance a *different* thing to object to rather than one
shared price objection. The Whole Truth is in `fnb_world` (`d2c-disruptor`, subscribed to
`afternoon_dip`), so a persona can name it without being flagged as inventing a brand.

## ⭐⭐ CAN THIS SAMPLE PHYSICALLY EXHIBIT WHAT I AM MEASURING?

| measuring | can it? |
|---|---|
| **do different stances react differently to ONE ad** | ✅ **YES — all 8 stances present, 8 agents each.** The exact inverse of the 2026-08-19 probe, which was 8 loyalists sharing one opinion |
| whether my `#73` inference was right | ✅ yes — predictions locked below |
| whether the reactions read concrete or aphoristic | ✅ yes, qualitatively |
| the other 20 moments | ❌ **NO.** Everyone here is an `afternoon_dip` person |
| panel seating at 176-cell scale | ❌ **NO** |
| how common any reaction is | ❌ **NO. 64 agents is not a rate.** |

## ⚠⚠ MY PREDICTIONS, LOCKED BEFORE THE RUN

**This is the falsifiable half.** From `#73`, reading only the `l4_stance` lines:

| stance | I predict | on this reason |
|---|---|---|
| `loyalist_tapri_chai_break` | **rejects** | ritual — the break is the product, not the snack |
| `switcher_whatever_is_cold` | **rejects** | price ceiling — under ₹20; a Whole Truth bar is ₹78-104 |
| `upgrader_desk_afternoon_protein` | ⭐ **ACCEPTS** | the target — already buys boxes of bars on Zepto |
| `aspirant_cafe_chair_afternoon` | **indifferent** | irrelevance — he is buying a chair, not a snack |
| `skeptic_protein_on_everything` | **rejects** | disillusionment — burned once, distrusts the claim |
| `purist_home_food_only_afternoon` | **rejects** | a categorical rule — nothing with a long shelf life |
| `pragmatist_whatever_fills_till_dinner` | **rejects** | satiety — it will not stop hunger till six |
| `gifter_office_round_afternoon` | **rejects** | format — a single bar cannot be shared round a table |

⚠ **The upgrader is the ONLY predicted acceptor. If everyone accepts, or everyone rejects, my
reading was wrong.**

## THE FOUR PRE-REGISTERED CRITERIA

⚠ **Thresholds fixed now. Do not move them after reading the output.**

### 1. ⭐⭐ PRIMARY — DO THE STANCES DISCRIMINATE?
⭐ **Read on the PROBLEM MAP, not the buy-intent headline** — `panel_discrimination_measured` found
the headline does **not** separate ads (signal-to-noise 1.0) while the problem map does (0.231 vs
0.148). **PASS: ≥5 of 8 stances show a DISTINCT dominant objection** — distinct meaning it would
lead to a different fix (change the price / change the format / change the claim / change nothing).
**FAIL: ≤4**, i.e. the stances collapse into one or two shared objections.

⚠⚠ **A FAIL HERE IS THE MOST VALUABLE OUTCOME AVAILABLE.** It would mean the `l4_stance` lines read
as different but do not *behave* as different — and that defect is in **every cell equally**, so it
must be fixed BEFORE spending `$5-8` on 168 more of them.

### 2. ⭐ WAS MY `#73` INFERENCE RIGHT? *(the self-marking check)*
Score my eight locked predictions against measured direction (accept / reject / indifferent).
**≥6 of 8 → my reading was sound and `#73`'s table stands as inference.**
⚠ **≤4 of 8 → `#73`'s headline table is RETRACTED to the user, not merely caveated.**
5 of 8 → reported as "partly right", no claim either way.

### 3. THE UPGRADER SEPARATION
**PASS: the upgrader's response differs measurably from the panel mean** on the run's own
buy-intent / action measure. ⚠ If the one person designed to want this product does not separate,
the instrument is not reading the stance at all.

### 4. APHORISM CHECK *(qualitative, reported, does not gate)*
Do the reactions name **things** (a price, a format, a place, a product) or **qualities**
(*"food that is food"*, *"not a round"*)? ⭐ This is the defect the user identified in the
`l4_stance` spec. Counted, not scored.

## COST AND CONTAINMENT

**`$3.64`** — preflight: target_id `$0.150` + 46 cold persona renders `$0.230` + commit L1-L4
`$3.03`. ⚠ Nothing else is installed and **`health_wellness_demo` and `hw_generated_v1` are
untouched**. ⚠ **This does NOT authorise the `$5-8` region.**
