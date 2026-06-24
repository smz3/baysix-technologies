# FOB Breakout System — Full Dissection

> **Source:** *FOB Breakout System — A Personal Trading Manual*, compiled by SIGMA Trading, © 2024 (PRIVATE & CONFIDENTIAL).
> Adapted from Turtle Trading + classic Breakout concepts + mentor notes ("Sir B" / "Bonker" video series, July 2024). Contact: sigmatrading.ai@gmail.com.
> **This file** merges the full manual text with a transcription of **every figure**. Source artifacts: [FOB Breakout system Complete.pdf](FOB%20Breakout%20system%20Complete.pdf) (70 pp, 91 images — the complete source) and the `.docx` (text + 30 Phase-3 screenshots only; its 61 Phase-1/2 concept sketches were blank placeholders, recovered here from the PDF).
> **Figure convention:** 🖼️ = a hand-drawn sketch on a black canvas (Phase 1–2 concepts) or an annotated MT5 mobile screenshot (Phase 3). Colours: **green** = buy-side / up-leg, **red** = sell-side / down-leg, **purple** = zones / marked levels.

---

## Terminology

| Abbr | Meaning |
|------|---------|
| VR | Valid Retracement |
| CF | Confirmation |
| CMP | Current Market Price |
| CONTI | Continuation |
| BO | Breakout |
| FM | Full Margin |
| MC | Margin Call |
| TP | Take Profit |
| SL | Stop Loss |

**Topics covered:** MTF · Market Flow · Direction–Bias · Confirmation · How to ride a trend · Market cycle.

**The core SOP (repeated throughout):** **CMP → BO → VR → CF** — find the current price action, wait for a breakout, wait for a *valid retracement* (one opposite breakout, one TF below), then wait for *confirmation* before entry. Never enter on the first BO.

---

# PHASE ONE — SEQUENCE

## CMP — Current Market Price

*"The foundation of this overall system."*

- **Don't look to the left** on CMP — focus on the *current* price.
- CMP is how you draw your zone. Get it wrong and your entry, TP, and SL are all wrong.
- **Do not enter on the first BO** — you must follow SOP first.
- Works on **any timeframe**.

### CMP — Breakout (Images 1.1–1.10)

- 🖼️ **Image 1.1** — Sell case. Three **red** dashed horizontal levels stair-stepping, "**SELL**" labelled top-right. Price prints successive levels as it breaks; the sequence of levels *is* the CMP read for a sell.
- 🖼️ **Image 1.2** — Buy case (mirror). Three **green** dashed ascending levels, "**BUY**" top-right.
- 🖼️ **Image 1.3** — A red level above, two green levels below, a **green candle** breaking up through them. Labels "**BUY**" / "**ABOVE**" — buy is valid when price breaks *above* the level.
- 🖼️ **Image 1.4** — Mirror of 1.3: green levels above, red levels below, a **red candle** breaking down. Labels "**SELL**" / "**BELOW**".
- 🖼️ **Image 1.5** — Descending sequence of green→red dashed levels, a red candle, and a **circled level** bottom-left (the reference level). Labels "**SELL**" / "**BELOW**", with note *"Shadow / Wick does not count"* — the candle **body** must clear the level, not just a wick.
- 🖼️ **Image 1.6** — Mirror of 1.5: ascending levels, a **circled green candle** top-left, "**BUY**" / "**ABOVE**", same *"Shadow / Wick does not count"* note.
- 🖼️ **Image 1.7** — *Example of a CMP situation.* Black zig-zag price (a large M/W swing) with **Zone 1** (upper purple box) and **Zone 2** (lower purple box); two circled retests; a green up-leg into Zone 1 and red down-legs. **In-image annotation:** *"PAY ATTENTION ON THIS! — Overall direction is still a **SELL** as shown on the graph. **UNLESS** price breaks **ABOVE Zone 1**, then it becomes a **BUY**. Zone 2 is supposed to be a continue-sell, which it could be — **HOWEVER you MUST follow CMP SOP** (covered later). As shown, price breaks Zone 2 and goes to Zone 1. **Both zones must follow CMP SOP; the BO-buy on Zone 2 DOES NOT COUNT as a buy."***
- 🖼️ **Image 1.8** — Black zig-zag price path descending to a small circle bottom-right. **In-image annotation:** *"Quiz: Where is your CMP???"* (a reader exercise — identify the current reference price on the swing).
- 🖼️ **Image 1.9** — *Example of a CMP situation.* A **red circle** and a **purple circle** marking two points along a horizontal line — the two reference points (CMP markers / zone edges) you compare.
- 🖼️ **Image 1.10** — Simple range: a **green resistance line** at top, a **red support line** at bottom — the bounding levels of a CMP range.

*End of CMP — extracted from Bonker Video July 2024, Sequence Phase 1.*

---

## MTF — Multi Time Frame Confirmation

*"MTF is linked closely with confirmation."* Once you understand MTF you will know: **Direction**, **which TF to use**, **which VR relates to what TF**, and **the confirmation on what TF**.

**Two types of setup / two types of confirmation:** **High Risk** and **Low Risk**.

- **High Risk Confirmation** — you **skip one timeframe**. *Example:* Monthly as trade setup → high-risk confirmation = **Daily** (skips Weekly). Daily setup → high-risk confirmation = **H1** (skips H4). Because you skipped a TF you don't yet know how price plays out → high risk → but you get a **discounted (better) entry price**.
- **Low Risk Confirmation** — you **wait for one timeframe below** (no skip). Monthly → Weekly; Daily → H4. Safer, but you pay a **premium (worse) entry price**.

> Trade-off rule: **High Risk = discounted price; Low Risk = premium price.**

- 🖼️ **Image 2.1** — The full **TF ladder** over one zig-zag price path. Top row (red down-arrows, the "skip" path): **Monthly → Daily → H1 → M15 → M1**. Bottom row (red up-arrows): **Weekly → H4 → M30 → M5**. Visualises that jumping along the top row skips the intervening (bottom-row) timeframe = the High-Risk path.
- 🖼️ **Image 2.2** — Titled *"High Risk Setups — You SKIPPED one Time Frame."* Three mini price-sketches: **Monthly/Daily** (red broken levels), **Weekly/H4** (green level + entry dot), **Daily/H1** (red level). Each pairs a TF with the one *two* steps down, i.e. a skip.
- 🖼️ **Image 2.3** — Titled *"Low Risk Setups — You WAIT for one Time Frame Below."* Three mini-sketches: **Monthly/Weekly**, **Weekly/Daily** (green level), **Daily/H4** (red level) — each pairs a TF with the *adjacent* one below (no skip).

### MTF — Situation of High Risk & Low Risk Setups

- 🖼️ **Image 2.4** — Down-trend zig-zag. *"Daily setup BO Sell"* (red level on top), then a stack of *"H4 BO Buy"* green levels stepping up, *"CMP H4 BO Buy,"* and at the top a red-circled *"H1 Create BO Sell, High Risk."* **In-image notes:** *"PAY ATTENTION — Daily made BO Sell, H4 made BO Buy. **Why High Risk?** You are trading against the trend. H1 made BO Sell **AGAINST** CMP H4 BO Buy. Therefore H4 is the safer trade as it has made a confirmation — a clear SOP explained further."*
- 🖼️ **Image 2.5** — *"Daily BO Buy"* (green level), *"H4 BO Sell"* (red), *"H4 CMP BO Sell"* with a **purple zone**, a green-circled *"H4 BO Buy Low Risk,"* and a red-circled *"H1 Create BO Buy High Risk."* **In-image notes:** *"Daily BO Buy, H4 BO Sell as VR. **Why High Risk?** Trading against trend; H1 made BO Buy **AGAINST** CMP H4 BO Sell Conti. If you take the High-Risk H1 BO Buy, you can partial-TP or hold at the nearest H4 CMP BO Sell; continue loading your buy at H4 confirmation."*

> **Zone rule (bottom of page):**
> - *If CF happens **in the ZONE**, Sir Bonker takes the **High Risk** and does **not** repeat SOP — because you might miss the movement. (Still High Risk.)*
> - *If CF happens **below the ZONE**, take it and **follow SOP** — sometimes gives a good range of pips.*

### MTF — Failed Breakout

- 🖼️ **Image 2.6** — *Daily BO Sell Setup.* Two sketches: (1) Daily green level, a red-circled *"H1 BO Sell"* that fails; (2) Daily with a **purple zone**, *"H1 BO Sell,"* then a large **red down-candle**. **In-image notes:** *"Setup Daily Sell, H1 BO Buy. **Is it a buy?** Not yet — Daily MUST make a new BO buy. **Follow your TF setups:** the Daily candle must fail its own setup, the H4 candle must fail its own setup, the H1 candle must fail its own setup."*

*End of MTF High Risk & Low Risk — Bonker Video July 2024, Sequence Phase 1, ends at 1h 40m.*

---

## VR — Valid Retracement  *(MOST IMPORTANT IN OUR SOP)*

- This was previously a simple **Breakout Pullback (BO PB)**. The problem with BO PB: price pulls back **multiple times**, so you can't tell which pullback is tradeable.
- **How to identify a Valid Retracement?** → the rules below.

### VR — Rules

- You need **one BO "berlawanan" (opposite)** — a breakout in a *different* direction. This also tells you what TF you're on.
- **Must look one TF BELOW.** Monthly looks at **Weekly** as its VR (opposite direction). Same for every TF.
- **DO NOT skip a TF.**
- **VR only happens ONCE!!!**

- 🖼️ **Image 3.1** — *"Valid Retracements."* A grid of TF pairs, each showing an upper-TF breakout level and, one TF below, the opposite-direction breakout that *is* the VR: **M→W, W→D, D→H4, H4→H1, H1→M30** (top row) and **M1→M5, M5→M15, M15→M30, M30→H1** (bottom row). Each VR sits exactly one timeframe below its setup.
- 🖼️ **Image 3.2** — *"Daily BO Sell"* (red level). Price drops, forms a **purple zone** labelled *"H4 VR, VR only once!"*, then rallies into a **green-circled** leg labelled *"This is Conti, not VR."* Teaches the distinction: the *first* opposite BO one TF down = the VR; a later same-direction leg is just continuation.

### VR — Multi Timeframe

- VR is the point that **validates** a setup.
- If a BO happens on **two timeframes** (double BO), which do you follow? → **whichever TF made VR first.**
- Remember **VR ONLY HAPPENS ONCE.**

- 🖼️ **Image 3.3** — Top: *"Daily BO Buy"* (green) and *"H4 BO Buy"* (green) with *"H1 VR"* (red level marked). Bottom row *"How to Scalp!"*: *"H1 BO Buy," "M30 BO Buy," "M15 BO Buy,"* then *"M5 VR"* (red) and *"M15 BO Sell."* **In-image notes:** *"Daily & H4 BO Buy. **Which TF should we follow?** Whichever TF created a VR — VR dictates which TF we trade. Here it's H4 BO Buy because H1 has created VR. **Scalping example:** H1, M30 & M15 BO buy; M5 VR creates a new sell — which TF are you trading? **M15**, as M5 has VR and breaks M15 support."*

### VR — Types and Placements of VR

- VR can happen in **different areas**.
- VR must happen in a **BO manner**.

- 🖼️ **Image 3.4** — *"Types of VR."* Three sketches: VR forming **low** (green level, good), VR forming **mid**, and *"VR in zone"* inside a **purple box** labelled *"\*not the best."*
- 🖼️ **Image 3.5** — *"VR Weekly **Buy** and its TF Setups — What TF made VR first"* (refer Bonker Sequence Phase 1, July, 2h 38m). A large **green Weekly candle** (close up) on the left; to its right, one week's worth of price action across nested zones (H1 / H4 / D / **W Breakout**), numbered 1–9: **(1)** M30 BO Sell VR, set up H1; **(2)** H1 CF Buy; **(3)** H1 BO Sell; **(4)** H1 BO Sell, set up H4 now, price break; **(5)** No CF, price break — now it's a D setup; **(6)** H4 enters D zone with H4 CF; **(7)** Price reject, maybe news; **(8)** Price breaks D zone and creates VR for W; **(9)** D enters W zone — now it's a W setup, D creates CF and price took off.
- 🖼️ **Image 3.6** — *"VR Weekly **Sell** and its TF Setups — What TF made VR first"* (refer Bonker Phase 1, July, 2h 42m). A large **red Weekly candle** (close down); numbered 1–9: **(1)** M30 VR Buy, set up H1; **(2)** H1 CF Buy; **(3)** Price reject; **(4)** H1 VR BO, setup H4; **(5)** H4 setup — if there's a CF you can trade it; **(6)** Price rejects this zone to continue sell; **(7)** New BO; **(8)** Price BO VR Daily, W setup; **(9)** Daily creates CF Sell — **Anchor lot / Full Margin**, as we know this is a W setup.

### VR — Warning: Two Types of VR

- **Clean VR.**
- **Messy VR** — can be in a sideways, very messy.
- Advisable **not** to trade ("ride") a VR. **Entry with a CF in a zone is much better.** Riding VR is **High Risk** unless the distance is far (e.g. Daily timeframe).

- 🖼️ **Image 3.7** — Two sketches: a messy/sideways VR (top) and a **purple-circled** messy retracement (bottom) with note *"When you buy here it will be high Risk. You can avoid this when you understand about SEQUENCE."* **In-image notes:** *"Messy VR, Sideways VR. **What should you do?** Wait for a Low-Risk CF for entry. **Why?** VR in nature is **High Risk**. Remember — VR's main purpose is to tell you which TF to trade."*

*End of VR — Bonker Video July 2024, Sequence Phase 1, ends at 3h 10m.*

---

## CF — Confirmation (BO Structured & Non-Structured)

### CF — High Risk & Low Risk

- **Breakout CF normal** → most common is a **Conti (continuation)** setup.
- **Breakout CF structured** → most common for a **Reversal** setup.
- **Which CF does Sir B always use?** → **BO CF structured.**

- 🖼️ **Image 4.1** — Two sketches in **purple zones**: *"Breakout CF Normal"* (M-shape, circled = "CF — confirmation") and *"Breakout CF Structured"* (M-shape with extra structure, circled = "CF — confirmation structured"). **In-image notes:** *"Two types of CF. **Which should you use?** Structured is always **better!** **Why?** It gives certainty price will go in its direction."*

### CF — Placements

- Breakout CF **in the Zone** = the best.
- Breakout CF **above** the Zone.
- Breakout CF **before** the Zone.
- **If CF failed, close your position first.**

- 🖼️ **Image 4.2** — Three stacked sketches, each with a purple zone and a circled CF: **(a) "CF in the zone"** → *"Safe."* **(b) "CF above zone"** → *"Should try and avoid this, but if price breaks above and below the zone it would be great."* **(c) "CF before/below zone"** → *"This zone can be used as well."*

### CF — Situation Awareness

- VR, CF, Pullback.
- **Shadow can count as well.**
- **If CF failed, close your position first.**
- **CF is an essential part of Storyline.**
- **CF stops before the zone sometimes because of barriers** — and there are cases with no barrier where price still makes CF before the zone.

- 🖼️ **Image 4.3** — *"CF Situation."* Sequence across purple BO boxes: **BO** → down → **CF H1** (green circle) → **CF M15** (purple box) → **PB M5** → **VR M30** (purple box), captioned *"REPEAT cycle of SOP again and again, so easy to understand."* **In-image notes:** *"Once there's CF, **repeat SOP**. **Why?** Further minimize **RISK**. **Take note:** if the CF zone is 20 pips it's not worth repeating SOP; if 30 pips above, repeat SOP. Repeat SOP again and again. Some CF will just move — ways to counter it explained later. CF that need / don't need to repeat SOP explained later."*

### CF — & VR Relationships  *(Phase 1 Part 2, 2h 32m)*

- Has several situations; a failed setup that will always happen.
- **Backtest on Daily BO, follow the images below — this is to understand STORYLINE!**

- 🖼️ **Image 4.4** — *"CF & VR **SELL** Situation 1."* D BO Sell (purple top), **1. CF H1** (green circle), **H4 VR Buy Zone** (purple, lower), **2. CF price ends in H4 VR zone, failed to break VR Zone**, **3. Do not entry sell here.** **Notes:** *"D BO sell, H4 VR, H1 CF. **Do not enter SELL** at the CF zone when price comes back from the VR Zone. **Why? RISK!** Price has rejected zone H4 VR, indicating price will further break the H1 CF zone. This always happens — you'll think it's a valid CF to continue sell — but it's because price **failed to break the VR Zone.**"*
- 🖼️ **Image 4.5** — *"CF & VR **SELL** Situation 2."* D BO Sell, **1. CF H1 High Risk CF** (green circle), **4. DO NOT SELL**, **3. CF price ends in H4 VR zone, failed to break VR Zone**, **H4 VR Buy Zone** (green circle), **2. VR Zone is strong — wait for new BO.** **Notes:** *"D BO sell, H4 VR, H1 High-Risk CF. You can take the sell as price entered the D Sell zone, but you **must TP at the VR Zone**. **Why? VR ZONE H4 — VR is most important in our SOP.** Price **FAILED** to break the H4 VR Zone → do not sell → **follow SOP and wait for a new CF.**"*
- 🖼️ **Image 4.6** — *"CF & VR **BUY** Situation 1."* D BO Sell, **1. CF H1** (green circle), **3. Best place: SCALP to BUY**, **2. CF price ends in H4 VR zone, failed to break VR Zone**, **H4 VR Buy Zone**, **4. TP Here.** **Notes:** *"D BO sell, H4 VR, H1 CF. Price BO failed CF → **best entry point**. **Why?** Price rejected VR H4, broke **ABOVE** CF HR H1 and pulled back. You **MUST TP in the Daily zone**. Pay attention to the H4 VR Zone."*
- 🖼️ **Image 4.7** — *"CF & VR **BUY** Situation 2."* D BO Sell, **1. CF H1**, **3. Best place to BUY**, **2. CF price ends in H4 VR zone**, **H4 VR Buy Zone**, **4. New BO.** **Notes:** *"This could be a **Point of Reversal** — now start a new cycle. **Why?** Price rejected VR H4, broke **ABOVE** CF HR H1 and PB. You **MUST see WHERE** this is happening — location is important, this is the starting point of a **REVERSAL.**"*
- 🖼️ **Image 4.8** — *"CF & VR **BEST SET UP** Situation 1 (\*Break LINE CHART)."* D BO Sell, **1. CF H1**, **H4 VR Buy Zone**, **2. Price finally breaks VR Zone — remember it has to be H4 that breaks the zone**, **3. Best place to SELL** (green circle). **Notes:** *"Price **breaks the VR ZONE** = the best time to entry. Reject VR Zone, create structure, and break the VR Zone. **Why?** VR is an important ZONE — if this happens on H4, best point to **FULL MARGIN**. **STRONG BREAK AND CLOSE** (not a small break of the VR zone). You don't have to wait at the H1 CF zone. Follow your TF that makes and breaks the VR Zone. Sir B always said this happens on **H1 below.**"*
- 🖼️ **Image 4.9** — *"CF & VR **BEST SET UP** Situation 2 (\*BREAK LINE CHART)."* Same layout/notes as 4.8 with a slightly different price path (the second illustrative case of the "strong break & close of VR zone = full-margin entry").

### CF — & VR Sideways  *(Most common question asked to Sir B — Phase 1 video 3:22:10)*

- *"If price breaks back and we cut loss (CL), what do we do?"*
- **Answer: Wait for a new CF.**

- 🖼️ **Image 4.10** — *"CF & VR **SELL** Situation CONTINUATION."* D BO Sell, **2. DO NOT SELL FIRST**, **3. WAIT for 2nd CF to entry** (green circle), **H4 VR Buy Zone**, **1. VR Zone is strong — wait for new BO**, **4. Confirm a new BO.** **Notes:** *"Wait for the **2nd CF** to happen. **Why? VR ZONE H4 — the 2nd CF is the best CF in this case.** New CF doesn't have to be in line, it can be a new CF. Monitor price to break the H4 VR Zone."*
- 🖼️ **Image 4.11** — *"CF & VR **BUY** Situation SIDEWAYS."* BO, VR, **1st CF — Don't Buy here** (purple zone), **2nd CF — Buy here in VR Zone** (green zone). **Notes:** *"Wait for the 2nd CF; CF does **not** have to be side by side. **Why?** Price sideways. New CF doesn't have to be in line. **Follow the main direction; don't get caught.**"*
- 🖼️ **Image 4.12** — *"CF & VR **BUY** Situation SIDEWAYS"* (variant). BO, VR, **Do not SELL!!!** (purple zone), **Buy** (green zone), *"Repeat SOP with CF in Zone."* Same notes as 4.11 (don't get caught **selling**).

### Purpose — of a Breakout

- A breakout in the Bonker system **must follow its SOP**. A breakout has a meaning of its own: a **VR BO** is a sign price will reverse with a **CF BO** from its **CMP BO** → **BO → VR → CF.**
- Each breakout signifies whether the trade is a **reversal, continuation, retracement, or CF**.
- **Double Breakout = Continuation** (e.g. Daily BO Sell + H4 also BO Sell).
- **Every BO just checks one TF higher** to see what price is doing.

### CMP — SOP

- **Breakout → Valid Retracement → Confirmation**
- **BO → VR → CF**
- Example: **H4 BO Sell, H1 VR, H1 CF (low risk), M30 CF (high risk)** — refer Phase One.

> **Special Note:** *"Choose any of the setups mentioned above for your entry. This will help you understand your strengths. These setups are optimal depending on your trading style. Some traders use these simple setups to trade large positions, like 100 lots or 30 lots. Keep in mind that these traders do not trade all the time."*

*End of CF — Bonker Video July 2024, Sequence Phase 1 Part 2, ends at 3h 26m.*

---

## Direction & Bias  *(Phase 1 Part 2, 3h 44m)*

### Direction — Daily (below)

- Shows the direction price is moving. Buy or Sell on any breakout. **Prioritize Daily.**

### Bias — Weekly only

- A **helicopter view** of overall direction = the main direction. The Bonkers syllabus analyses **exclusively on the Weekly timeframe**.
- Weekly helps you understand what's happening on Monthly and gives insight into Daily and below.

### How to connect Direction & Bias

- If you understand **BIAS** you'll trade with ease.
- **BIAS buy** → prioritize buy, as long as Daily keeps breaking out Buy.
- To Sell, you must **wait for Daily to make a Sell** — and that Sell is **temporary**, it can become Buy at any time. (Vice versa for all of the above.)
- **Bias plus sequence will be powerful!**
- **If Weekly is near and entering the Weekly Barrier, be careful!**

- 🖼️ **Image 5.1** — *"Direction + Bias Connection."* A big **W BO** (green level) at the bottom, then a staircase of *"D BO"* and *"D BO Sell"* labels climbing up, with one **red level** (D BO Sell) and a **green level**. **In-image notes:** *"BIAS buy → buy until Daily creates a BO Sell. **Why? Bias is stronger.** Sell is temporary; Bias is on buy, so keep buying."*

### Direction + MTF = Same Concept  *(Important — Phase 1 Part 2, 4h 06m)*

- Each TF looks for another TF: **M1 → M5 → M15 → M30 → H1 → H4 → D → W → M.**

- 🖼️ **Image 5.1 (second)** — *"Direction + Multi Time Frame."* *"BO D sell,"* *"H4 creates a VR — H4 will look for Daily,"* a **purple zone** labelled *"H4 VR zone — if price breaks it, it becomes an H4 setup, H4 will look for Daily,"* and *"D high-risk CF is H1; H1 CF will look for H4."* **In-image notes:** *"Generally each BO looks for its pair. **Why?** It's the closest TF to which price made a BO. Things get clearer in the Sequence video; refer to the VR chapter if confused."*

*End of Direction & Bias — Bonker Phase 1 Part 2, ends at 4h 08m.*

---

## Barrier  *(Sir B doesn't use barriers as entry points — only for Take Profit; Phase 1 Part 2, 4h 08m)*

- **Barrier can be used as a direction** ("barrier after barrier").
- Entering **at** a barrier is **not advisable** — high likelihood of price rejection. Using CMP for entry is much safer.

### Barrier — 2 Rules

1. **Same-timeframe barrier** — Daily BO to Daily Barrier.
2. **One timeframe below** the barrier.
3. *Bonus:* **Overlap Barrier.**

- 🖼️ **Image 6.1** — *"Barrier — Same Time Frame."* *"BO D Sell"* (purple zone top), *"BO D Buy"* (purple zone bottom), *"D will look for D first."* **Notes:** *"Rules of Barrier: D to D and so on. **Why?** It looks for its own TF first. Barrier to Barrier."*
- 🖼️ **Image 6.2** — *"Barrier — One Time Frame Below."* *"BO D Sell,"* a stack of **blue barrier zones** (*"LTF barrier before VR happens"*), *"CF Structured for FM,"* a green-circled *"PB Buy with CF for FM,"* *"BO D Buy,"* and *"1st Barrier MUST break!"* **Notes:** *"Lower TF looks for the barrier — clearing barrier by barrier on the LTF. **1st barrier must break!** Why? The higher TF is looking for its own TF. Sir B likes to FM (full-margin) a CF in a zone BO because it's a Daily VR, Big TF. Sir B follows CMP SOP."*
- 🖼️ **Image 6.3** — *"Barrier — One Time Frame Below"* (rejection case). Blue barrier zones, *"Barrier Rejection with just Shadow"* (green circles), *"DO NOT Buy! Or Sell!"*, a **red candle**, *"VR zone must break."* **Notes:** *"Be careful when a barrier rejection is **just a shadow**. **Why?** Price makes a new BO Sell and breaks VR. Rejection does **not** mean it rejects — simply wait for a new breakout. Hence Sir B doesn't trade a barrier buy without a CF."*
- 🖼️ **Image 6.4** — *"Barrier — Overlap."* Blue barrier zones, *"DO NOT Sell when this barrier has broken — it's considered an overlap,"* *"Overlap BO zone"* (green circle), *"BO D Buy,"* *"Just wait for this VR to break and enter on CF when price comes back into the VR BO Zone."* **Notes:** *"Overlap barriers above are **not** to be used as an entry. **Why?** That barrier has already broken. Therefore wait for a new CMP BO or VR-zone BO."*

### Barrier — Cheat Code  *(Phase 1 Part 2, 4h 33m)*

- Hints at a **reversal signal**.
- When price goes **sideways in a barrier zone**, it most likely will reverse.
- **Create a new BO and BO again toward the opposite direction.**
- The opposite BO did **not** break barrier support/resistance.
- This usually happens in the **same TF and with a VR**.
- **Use M30 for GOLD.**

- 🖼️ **Image 6.5** — *"Barrier — Sideways."* *"BO Sell,"* *"LTF barrier before VR happens,"* a green-circled *"Price sideways at a barrier and makes a new BO — so just follow the new BO,"* *"BO D Buy."* **Notes:** *"Price sideways at a barrier → wait for a BO. **Why?** A new BO to a new direction, as price failed to break the barrier. Once there's a new BO from the sideways, follow that BO. If price breaks sideways **and** breaks the barrier, it will go in the direction of the barrier BO."*
- 🖼️ **Image 6.6** — *"Barrier — Cheat Code."* *"2nd Barrier"* (red level), *"Price failed to BO barrier,"* *"BO Buy"* (green), *"BO Sell"* (red), *"1st Barrier"* (blue zone). **Notes:** *"Price makes an early BO sell before the barrier → entry sell at Barrier Resistance. **Why?** That barrier has not broken. **M30 is the best for the reversal barrier.**"*

---

## Ride The Trend (RTT)  *(Phase 2 video, July 14 2024, 38m)*

### RTT — Purpose: Continuation Setup (Setup Conti)

- **When to use it?** The safest way is to **wait for one BO in a bigger TF**. To Conti on H4, look at the **Daily BO first**.
- *Example:* H4 BO sell → keep selling until there's a new H4 BO buy. In that case, turn to **H1 and look for multiple H1 BO sells** because H4 is still selling.

- 🖼️ **Image 7.1** — *"RTT — Conti Sell."* *"H4 BO Sell"* (red levels), a large **red down-candle**, *"H1 Conti Sell"* (red levels stepping down). **Notes:** *"It's a conti setup on H1. **Why?** H4 BO sell, H1 keeps making BO sell. Watch out for barrier — you can TP at a barrier; once at a barrier you monitor first."*
- 🖼️ **Image 7.2** — *"RTT — Conti Sell."* *"D BO buy"* (blue zone, bottom), *"D BO sell,"* *"H4 BO sell,"* *"Relax first here,"* *"Barrier break"* (blue zone). **Notes:** *"D BO Sell with H4 conti. **Why?** H4 keeps on BO Sell. Watch out for barrier; TP at barrier; once at barrier monitor first. **Keep conti as long as there is no VR BO.**"*
- 🖼️ **Image 7.3** — *"RTT — Conti Buy that does **not** need CF."* *"H1 VR"* (red box), *"H4 BO buy"* (blue zone), *"Usually price will touch and go without CF,"* *"If you want to enter, look at a high-risk CF M30 for buy."* **Notes:** *"VR goes straight to the BO zone for conti without CF. **Why?** Same concept as BO-VR and stuck-in-barrier — it's the same concept; VR happens without a structure. If you're not confident you can wait for a CF or HR CF."*
- 🖼️ **Image 7.4** — *"RTT — Conti."* *"BO Normal — NO structure"* (red box), *"BO with structure"* (red box), *"False big movement, sell-off etc,"* blue zone. **Notes:** *"We follow CMP SOP — thus conti sell on the left drawing. **Why?** Conti because the BO-sell-normal (left) vs the with-structure one that has potential to break below. **No matter how huge the movement, just follow CMP SOP: BO–VR–CF.**"*

> *Video paused at 1:09:44.*
> **Special Note:** *"When you truly understand direction and storyline, VR and Barrier will be an easy walk." / "Sir B students make millions on riding Setup Conti."*

### RTT — VR Fresh and Not Fresh (Setup Conti Layering)  *(Phase 2 video, 1h 53m)*

**VR — Fresh:**
- After a breakout, price goes **straight into the origin zone BO**.
- **No retracement into the VR Zone.**
- *"WAJIB TP bila entry CF untuk masuk zone VRF"* — **must TP when you enter a CF to get into the VRF (VR-Fresh) zone.**
- **Wait for the 2nd CF for layering.**

- 🖼️ **Image 7.5** — *"RTT — VR FRESH."* *"VR normal"* (blue circle), *"No retracement in VR zone after BO,"* *"VR zone"* (red box), *"Entry 1 — TP here,"* *"Layer,"* *"CF Entry 2"* (green circle), *"CF Entry 1"* (green circle), *"BO"* (blue zone). **Notes:** *"It's a VR Fresh because price has **not** retraced and closed back into the VR Zone. 1st entry MUST TP in the VR zone. **Why?** The VR zone is fresh and will most likely create a CF for sell first. You must wait for a new CF to enter; if price creates a new CF you can **start layering/stacking your entries.**"*

**VR — Not Fresh:**
- After a breakout, price retraces and **"closes" inside the VR Zone** (**shadow does not count**).
- This particular VRNF is considered a **VR structured**.
- Price will go back to [the zone].

- 🖼️ **Image 7.6** — *"RTT — VR NON FRESH."* *"VR Structured"* (blue circle), *"Retracement in VR zone after BO,"* *"VR zone"* (red box), *"Ride the trend,"* *"Layer,"* *"CF Entry"* (green circle), *"BO"* (blue zone). **Notes:** *"The difference between fresh and not-fresh is that there's **no retracement** on the VR zone — therefore you can **ride the wave**. **Why?** The VR zone is no longer fresh, therefore you can **hold**. Wait for a new CF to enter; if price creates a new CF you can start layering/stacking your entries."*

**— END OF PHASE ONE —**

---

# PHASE TWO — STORYLINE SEQUENCE

> *"Once you understand storyline, you can enter without CF — given it's in the right place."*

## Storyline Sequence  *(Phase 2 video, July 14 2024, 2h 38m)*

### Why?

- Understanding the storyline sequence helps you use different timeframes effectively and decide where to **take profit** and **hold**. Mastering Phase 1 and combining it with Phase 2 makes your analysis much clearer — you can identify your current position in the market more easily.

### Explanation

- Every market movement (a price break of structure or a significant surge) is influenced by **TRADE CONTROL**.
- These movements are **linked to Multiple Time Frames (MTFs)**, highlighting which TF is controlling the market at any given moment.

- 🖼️ **Image 2.1.1** — *"Sequence."* Left sketch: **BO → VR →** price drops away (no CF). A center arrow notes *"Sample structure that always happens: price moves without a pullback and keeps moving."* Right sketch: **BO → VR → CF** (price makes structure before continuing). Contrasts a no-pullback runaway vs a CF-structured move.

### What does it mean by "control"?

- **One TF lower controls one TF higher.**
- In a Daily BO, **H4 controls the movement of the Daily** → H4 is the trade control.
- Remember price moves **up and down**: H4 makes a BO sell and a reverse BO buy to continue to its destination.

- 🖼️ **Image 2.1.2** — *"Sequence."* A boxed note *"Lower Timeframe controls the bigger Timeframe"* and the ladder **M1–M5–M15–M30–H1–H4–D–W**. A large **green Daily candle** sits over a **purple D level**, and a string of **H4** sub-swings (with green levels) builds the Daily leg. A legend keys **Daily = red, H4 = blue, H1 = orange**, with a red Daily zig-zag and a nested blue-H4 + orange-H1 zig-zag below showing the LTF completing the HTF move.

### What does it mean by control? *(\*to avoid missing the big movement)*

- It's basically a **BO–VR–CF**.
- Combine it with SOP → you know where to properly buy and sell.
- The **lower TF completes the HTF**, on the condition that a higher TF is making a BO.

### Most common problem?  *(Phase 2 video, 2h 51m)*

- **"Tertinggal Bas" (missing the bus)** — a big TF makes a BO and you're waiting for the CMP SOP to repeat.
- This leads you to wait for **"price that is not coming back."**
- **Catch whichever LTF makes a VR — not M1!** Take M5 and above.
- **WITH SEQUENCE you'll know which setups NOT TO TRADE.**
- Sequence is basically **finding a VR on a lower TF when the HTF candle is trending.**

- 🖼️ **Image 2.1.4 (first)** — *"Sequence — Waiting for price that does not come back."* *"VR Structured," "H1 VR," "H4 BO," "H1 CF,"* then *"H1 price trending — who moves H1??? M30"* with a **green trending staircase** up. **Notes:** *"After the CF breakout and price rally, look for M30 to entry. **Why?** M30 moves H1, therefore you trade the M30 CMP SOP. If there's no sign on M30 BO with M15 VR, then look for M15 BO, M5 VR — this is **Sequence**. From these sequences we KNOW WHICH SETUP you don't have to enter."*

### Sequence Direction  *(Phase 2 video, 3h 31m)*

- High potential to show **where we should TP**.
- The distance of the TP lets us **maximize profits**.
- Sequence between timeframes: when you have MTF breakouts (**H4, M30, H1**) all at once, price makes a **strong move**.

- 🖼️ **Image 2.1.3** — *"Sequence Direction — Swing."* *"Weekly BO Sell"* (blue), *"H4 TP at Weekly,"* *"Daily VR"* (box), *"H4 BO"* (orange/red). **Notes:** *"TP at Weekly; Daily looking for Weekly. **Why?** H4 trade-controls Daily. When you trade H4, follow CMP SOP — H1 VR & CF (low risk), HR M30 CF. From these sequences we KNOW WHICH SETUP you don't have to enter."*
- 🖼️ **Image 2.1.4 (second)** — *"Sequence Direction — 'Setaman' (Multi Breakout at the same time)."* *"Daily BO Buy,"* circled clusters of LTF swings, and a circled *"Lower Time frame SOP"* (purple zig-zag). **Notes:** *"Timeframe in a timeframe. **Why?** Lower TF controls one higher TF; the LTF has completed the sequence. These breakouts happen with multiple breakouts across **3 different timeframes ON THE SAME DIRECTION** — 'Setaman' = concurrent confirmation."*
- 🖼️ **Image 2.1.5** — *"Sequence Counter — 'False Breakout' (Multi Breakout at the same time)"* (Phase 2 video, 3h 52m). *"H4 Buy Sequence Buy"* (blue), *"H4 BO Sell"* (red level), *"Partial TP,"* and a blue-circled *"H1 VR for counter buy — Major TF still in buy sequence."* **Notes:** *"Counter-buy on H1 VR. **Why?** The higher-sequence TF is still a buy. Watch out for resistance at the H4 BO sell. VR to VR. **Important that the higher-TF sequence is not turning direction.**"*
- 🖼️ **Image 2.1.6** — *"Sequence Scalping."* *"Daily BO Sequence Buy"* (blue), *"H4 VR Sell,"* *"H1 VR Buy — scalp buy here,"* *"H1 VR Buy — TP scalp here,"* a circled *"Low Risk CF buy,"* a circled *"High Risk CF buy,"* *"H1 VR Buy for this sell."* **Notes:** *"Scalp on VR H1. **Why?** VR-to-VR trade. Important that the higher-TF sequence isn't turning direction. A high-risk CF is a VR-to-VR trade — risky in nature; you have to be quick and pay full attention. **Sequence scalp needs skills.**"*

### Market Cycle  *(Phase 2 video, 3h 59m)*

- It's a **repetition of CMP → BO → VR → CF — that is a cycle**.
- Price has to **break VR** to repeat its cycle and go cycle by cycle.
- As we trade CMP, we repeat the CMP SOP.

- 🖼️ **Image 2.1.7** — *"Cycle Sequence."* An up-staircase with **red boxes** marking each *"New Cycle CMP SOP,"* labelled *"CMP SOP: BO-VR-CF."* Side note: *"Just repeat CMP SOP. That is CYCLE."*

### Cycle VR Breakout  *(Phase 2 video, 4h 3m 33s)*

- When price BOs the VR and pulls back, **DO NOT ENTER. MUST WAIT FOR A NEW CYCLE BO.**

- 🖼️ **Image 2.1.8** — *"Cycle VR Breakout."* *"VR"* (blue zone) with *"DON'T enter on PB — VR is high risk,"* and *"Enter on New BO"* (green level). Side note: *"Enter at the NEW BO, not at the BO VR. Refer back to the RTT VR chapter and the VR chapter."*

**— END OF THEORY —**

---

# PHASE THREE — MT5 CHARTS

> Phase 3 applies Phases 1–2 to **live XAUUSD MT5 mobile screenshots** (Just Markets, "GOLD vs US Dollar"). Across all charts: **blue/cyan boxes = demand (buy) zones**, **pink/red boxes = supply (sell) zones**, **grey boxes = marked zones/barriers**, **red arrowed lines = the VR/CF impulse leg**, and **purple freehand = the author's own circles/labels**. Each screenshot is a real instance of a concept already taught above.

## BIAS  *(Phase 2 Sequence video, 4h 35m)*

- Use **only the Weekly timeframe**. Look for the **Weekly candle close**.

🖼️ **Charts (Weekly):** XAUUSD Weekly line chart with a purple hand-drawn ring around the symbol/TF (W1) and a marked level — establishing the weekly bias before anything else.

## Direction

- Check **where the Daily candle closed**. Identify the direction of the Daily closing price: **Bias buy + Direction buy** → buy; Direction sell → sell.
- Where's the sequence? It's **H4**. Repeat SOP CMP. **H4 controls Daily.**

🖼️ **Charts (Daily):** XAUUSD Daily with stacked blue demand zones and pink supply zones drawn at prior swing levels, plus small purple tick-marks at the reference closes.

## Sequence  *(Phase 2 Sequence video, 4h 40m 22s)*

- H4 created a **BO VR with a BO Sell** — however **Bias (W) and Direction (D) are still a buy**.
- This is why you must understand SOP and Sequence. H4 created a **VR WITHOUT STRUCTURE** → therefore **prioritize BUY, not Sell**.
- **Bias Weekly buy → Direction Daily buy → H4 VR Sell** (the VR is for continuation of the Daily BO Buy). Simple.
- **Barrier-rejection trade:** when **Bias, Direction and Sequence align → FM (Full Margin)!**
- **Entry at origin price on H1** (4h 44m 03s) — *"entry pucuk"* (enter at the tip/origin).

🖼️ **Charts (H4 → H1):** H4 line charts with **red arrowed VR legs** thrusting up into pink supply zones; a final H4 chart with a broad pink barrier and a red projection — the barrier-rejection / origin-entry case.

## Reversal Signs  *(Phase 2 Sequence video, 4h 45m 48s)*

- H1 created a **BO Structured** = an **EARLY sign** of reversal — **early signs, NOT confirmation.**
- The **best way to grow the account** is when you have a **Bias + Direction Conti setup**.
- If price is sideways for a long time, just **wait for the Direction TF to make a breakout**.

🖼️ **Charts (H1):** XAUUSD H1 with pink supply zones at the highs and structure forming underneath — the early-reversal read.

## Sequence Sell  *(Phase 2 Sequence video, 4h 51m 0s)*

- Follow **Sequence Direction**. Direction has changed to **sell** while **Bias is still a buy**.
- *"Yang penting kita tahu tujuan BO dan mengikut direction dan sequence kita, auto kita tahu storyline"* — **as long as we know the purpose of the BO and follow our direction & sequence, we automatically know the storyline.**
- **Reversal VR** is tricky, e.g. **Daily BO Sell → BO Buy again → BO Sell** (4h 56m).

🖼️ **Charts (H1):** H1 with a large grey/pink zone marking the prior range and the sell sequence breaking down out of it.

## Sequence LTF  *(Phase 2 Sequence video, 5h 04m 7s)*

- Follow **Sequence Direction** when direction changes.
- **D BO → sequence of D is H4; H4 BO → sequence of H4 is H1; check H1.**
- H1 has made a **sequence Sell** → now look at a lower TF, **skip M30, go straight to M15** (or whichever TF makes a **VR first**).
- Direction for that moment is **temporarily sell** while **Bias is still a BUY**.
- Avoid sideways by **not trading in a barrier or at a point of BO**. One way to enter safely is when the **Control TF makes a clear BO**.

🖼️ **Charts (H1 → H4):** H1 with a small grey zone and a **red VR arrow** marking the impulse, plus an H4 with grey VR boxes showing the LTF→HTF chain.

## Sequence VR  *(Phase 2 Sequence video, 5h 34m 07s)*

- A **VR that you should AVOID entering.**

🖼️ **Charts (H4):** XAUUSD H4 with a **red VR arrow** into a grey zone illustrating the no-trade VR.

## Intraday OHLC — Open/High/Low/Close  *(Phase 2 Sequence video, 5h 44m 22s)*

- **Use the period separator.**
- **Every day, look at what's happening on H1.**
- If H1 sells, follow it — but know **what function** that H1 sell serves (VR? CF?). In this case, the intraday Direction is **H1 as a VR to the H4 Buy**. Who controls H4? **H1** — so we follow H1's direction.
- **H1 BO Sell on the day as a CF to the H4 Sell** = **best setup** (Phase 2 Sequence video, 5h 52m 52s).
- **H4 Sell with H1 CF** = **best setup.**

🖼️ **Charts (H1, candlestick + line):** candlestick H1 with a grey CF zone at the swing high; companion line charts (one with the broker contact-list sidebar visible) showing the same H1-as-CF-to-H4 day.

## Scalping  *(Phase 2 Sequence video, 5h 58m 00s)*

- Start from **H4 as direction**, move to **M30 → M15 → M5**.
- Still **follow Bias and Direction**.
- **Intraday = M30 and above; Scalp = M30 and below; Swing = H4 and above.**
- *H4 scalping Direction = Sell.*
- When you scalp the **M15 TF you MUST look one TF higher = M30**. Don't get trapped in a VR.

🖼️ **Charts (M15 / M30):** M15 with a wide pink range zone and a small VR mark; an M15 with a **red VR arrow** into a grey zone and the H4-direction-sell context.

## Swing  *(Phase 2 Sequence video, 6h 17m 48s)*

- Start from **Weekly → Daily**.
- Still **follow Bias and Direction**.
- **Counter-VR when H4 makes a False CF.**

🖼️ **Charts (W / D / H4 / H1):** Weekly uptrend with a grey marker; **Daily with the author's purple handwriting — "VR" (over a small high) and "CF" (over a grey zone) — the clearest worked swing example**; H4 and H1 with grey demand zones and **red projection arrows** sketching the continuation target.

## How to Back Test & Do Homework  *(Phase 2 Sequence video, 5h 37m 20s — last 15 minutes)*

- **Identify what style of trader you want to be: Swing, Intraday, or Scalp.**
- **Intraday = M30 and above; Scalp = M30 and below; Swing = H4 and above.**

---

# THE END

> *"It is what it is." — SIGMA Trading.* All rights reserved; for the personal use of the author only.

---

## Dissection note (provenance & gaps)

- **Completeness:** all manual text (Phases 1–3, terminology, special notes) is transcribed verbatim/closely; **all 91 figures are accounted for** — 61 Phase-1/2 concept sketches + 30 Phase-3 MT5 screenshots.
- **Source caveat:** the `.docx` had only the 30 Phase-3 screenshots embedded; its 61 concept sketches were 1×1 transparent placeholders. **Every concept sketch here was recovered from the PDF** (`FOB Breakout system Complete.pdf`), which baked them in.
- **Image 1.8** in the source is a near-blank "Quiz: Where is your CMP???" exercise sketch (recovered from the page render).
- **Figure numbering** follows the manual exactly, including its own duplications (two "Image 2.1.4", two "Image 5.1") — preserved rather than renumbered.
- **Original-language phrases** (Malay: *berlawanan, wajib, tertinggal bas, entry pucuk, yang penting…*) are kept and glossed inline.
