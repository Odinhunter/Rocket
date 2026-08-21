# Letting people act out of character — a proposal, nothing built

**2026-08-22. `$0`. Written after the user's three challenges to `#75`, which were all correct.**
⚠ **This is a design put to the user for a decision, exactly like decisions 3 and 4. Nothing is
implemented and no default here is a fact.**

## THE PROBLEM IN ONE LINE

**The panel produces a step function — 0% for seven kinds of person and 87.5% for one — and real
markets have tails.** If a hundred people buy a protein bar, a couple of them are the person who
normally only buys shareable packs. Our model says that person buys one **never**.

## WHY THE THING BUILT TO FIX THAT CANNOT

There is already a "chaos vector" meant to supply variety — impulsive / moderate / deliberate.
⚠⚠ **It cannot work, because it is written into the person's life story.**

The vector is baked into the cached biography, so "impulsive" becomes *"you didn't calculate
anything"* — **a fact about who they are.** That makes it a second description of the same person,
sitting next to the disposition, which is also a description of who they are. ⭐ **Two descriptions
of a person cannot create day-to-day variation. They just agree with each other.**

**Measured, in the one stance that actually acted:** impulsive, moderate **and** deliberate all
bought. The chaos band predicted nothing.

## THE MOVE: FROM WHO THEY ARE TO WHAT KIND OF DAY IT IS

⭐⭐ **The right shape already exists in this codebase.** `cycle_position` (just bought / mid-cycle /
running low) is:

- **sampled fresh for every exposure**, not written into the person
- kept **out of the cached life story** and out of the panel's segment keys
- **declared in the spec** with a stated default mix (25 / 50 / 25)
- **always reported next to the headline**, so the assumption can never hide inside a number

**Chaos should be rebuilt to look exactly like that** — and its content should change from
**temperament** to **circumstance**.

⭐ **Why circumstance rather than a personality dial:** temperament is already covered by the
disposition (price orientation, decision driver, involvement). What actually varies between a
person's Tuesday and their Thursday is not their character — it is **what happened to them that
day.** And this project has that in real data:

> **`#68` finding 4:** four of five real people ate substantial food they did **not** choose or pay
> for — a boss, a mother, a wife, a host. One man chose **2 of his 14 items**.
> **`#68` finding 1:** the same coffee replaces food at 11am and accompanies it at 4pm.

**Circumstance beating disposition is the strongest measured finding we hold.** This makes the
instrument able to represent it.

## HOW IT AVOIDS THE OBVIOUS TRAP

⚠⚠ **The danger:** tell a language model *"you may act out of character"* and it will do it far too
often. We have measured this failure before — instructions get over-obeyed and examples get copied.

⭐⭐ **The answer: the model never sees a probability, and never sees permission. It sees a fact.**

The harness samples the circumstance and states it flatly — *"you were paid yesterday"*, *"you are
at a station with twenty minutes"*, *"you have not eaten since one o'clock"*. **The rate is
controlled entirely by how often we sample it. A model cannot over-comply with a number it is never
shown.**

⚠ And one rule carried straight from `#69`: **a circumstance may WIDEN what is plausible; it must
never SCRIPT the outcome.** *"Payday was yesterday"* widens. *"Your colleague asked you to grab her
one"* is a purchase wearing a costume — banned.

## THE CANDIDATE AXES, ALL GROUNDED IN THE FIVE REAL DAYS

| axis | values | where it comes from |
|---|---|---|
| ⭐⭐ **who is providing this** | self · employer · family · host | **finding 4** — the biggest gap in both maps |
| **pocket state** | just paid · ordinary · stretched | ⚠ *not directly observed — the weakest of the four, and the one most worth cutting* |
| **who they are with** | alone · with peers · with family | P2 always with fellow labourers; P4 alone at 4pm, with a friend at 9pm |
| **how long since they ate** | recently · a while · a long gap | P2's six-hour gap; the user's 11am coffee |

⚠ **Four is already probably too many** — each one multiplies the combinations. **Two would be a
defensible start**, and *who is providing this* is the one with real evidence behind it.

## THE PART THAT MUST STAY HARD

⚠⚠ **Do not soften the dispositions.** The blunt refusals are what makes the panel discriminate at
all, and the standing law is that *a panel that likes everything measures nothing.* The trait keeps
the base rate near zero; the **circumstance supplies the licensed exception, with a reason.** ⭐ That
is how real tails work — the gifter who buys one bar has a reason that day, he has not changed
personality.

## ⚠⚠ THE HONEST LIMIT, WHICH MUST BE SAID OUT LOUD

**This change makes tails POSSIBLE. It does not make the rates TRUE.**

Whatever mix we choose is a declared assumption, exactly like the 25/50/25 cycle mix — *"a documented
best-guess, fail-conservative, recalibrate later."* ⚠ **And we must not tune it until the output
"looks realistic" — that is manufacturing credibility.** Only the backtest against real behaviour in
`v3_one_month_plan` can make a rate true, and the instrument has still never touched reality.

## THE SEPARATE FIX THE SAME EVIDENCE FORCES

⭐ **`buy_at_restock` must stop counting as a win for someone who already buys the brand.**
`decision.py:120` scores it as buy-intent; two of our seven "buyers" had **just bought a box**, and
the upgrader's own life story names the advertised brand and its price. **That is retention, not
conversion.** ⚠ Everything needed to re-report it is already on disk — `$0`.

## THE ONE FORK FOR THE USER

| | |
|---|---|
| **A. Add circumstance, keep temperament** | Safer, no cached renders invalidated. ⚠ Leaves a layer that we measured doing nothing, and it keeps fragmenting the render cache — paying for extra renders with no behavioural return |
| **B. Add circumstance, retire temperament** | Cleaner and cheaper per run. ⚠ Invalidates all **598 warm renders** — that is what the render version bump exists for, but it is a real cost and should be a deliberate step, not a side effect |

⭐ **Recommendation: A now, B as a separate decision once circumstance is proven to move anything.**
⚠ Do not do both in one change — if it fails you will not know which half failed.

## SEQUENCING

1. ⚠ **The category rename comes FIRST and blocks the region** — `fnb_world` renders to personas as
   *"international food and drink"*. The slug bakes into the generated file, the render hashes and
   the install guard.
2. The `buy_at_restock` re-report — `$0`, uses data already on disk.
3. This proposal, if the user takes it.
4. ⭐ **Re-run the same 8-type rig (~`$4`) under a fresh pre-registration** — transcripts as the
   surface this time, never the pain map — testing *"the upgrader still beats every other stance"*
   and *"tails exist but stay a minority at the declared mix."* **That is the falsifiable version of
   the user's own intuition.**
