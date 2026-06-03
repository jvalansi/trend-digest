# Historical Theory and Frameworks

Conceptual context behind the [GDP Monitoring System](gdp-monitoring-design.md) — welfare beyond output, civilization trajectory, and how to think about predicting history.

---

## Beyond GDP — Happiness and Welfare

GDP was designed by Simon Kuznets in WWII to measure industrial war capacity. He explicitly said it shouldn't be used as a welfare measure. The World Happiness Report (WHR) attempts a richer picture using the **Cantril Ladder**: respondents rate their life 0–10 against their personal best/worst possible life. Country scores are national averages from ~1,000 Gallup respondents, 3-year rolling average.

### WHR regression factors and coefficients

| Factor | Coefficient | Gallup question |
|---|---|---|
| Social support | **2.563** | "Do you have friends/family to count on in a crisis?" |
| Freedom | 1.378 | "Are you satisfied with your freedom to choose what to do with your life?" |
| Corruption (negative) | −0.733 | "Is corruption widespread in government/business?" |
| Generosity | 0.487 | "Did you donate to charity in the past month?" (residualized on GDP) |
| GDP per capita (log) | 0.349 | — |
| Life expectancy | 0.028 | — |

These 6 factors explain ~75% of cross-country happiness variance. Social support has the largest coefficient; when multiplied by the actual range of variation across countries, GDP and social support contribute roughly equally in practice.

### Notable gaps in the WHR model

**Generalized trust** — "Generally speaking, would you say most people can be trusted?" (World Values Survey) — is not an explicit WHR factor, despite being one of the strongest independent predictors of national happiness. The WHR proxies for it through "absence of corruption" (institutional trust) and "social support" (in-group trust), but neither captures trust in strangers, which is what differentiates Nordic societies most sharply.

Generalized trust correlates negatively with the Gini coefficient (more unequal → less trust), but causation is contested: Uslaner argues trust predicts future equality; Wilkinson & Pickett argue inequality erodes trust; Rothstein argues institutional quality drives both.

### US happiness trend

US happiness peaked ~2008–2012 (ranked 11th globally in 2012, now 24th in 2025). The decline is sharpest among young people and correlates precisely with smartphone/social media saturation (~2012–2015). Older Americans (65+) who use social media less have held steady. Material living standards continued rising over this period — the divergence is the strongest evidence that above a baseline income, social connection quality dominates over material wealth as a happiness driver.

### Implications for GDP monitoring

The monitoring system tracks economic *output*. The happiness literature suggests output is a proxy for welfare with significant limitations: real wage growth, social trust, and freedom to make life choices are more directly predictive of whether people are actually better off. A future extension could layer WHR country scores against economic anomalies — flagging cases where output is rising but welfare indicators are not.

---

## Beyond Happiness — Civilization Trajectory

### What do people actually optimize for?

Happiness may not be the right welfare target. Aristotle's distinction between *hedonia* (felt pleasure) and *eudaimonia* (flourishing through achievement and virtue) is 2,400 years old — the observation that people don't purely optimize for happiness predates the WHR by millennia. Nozick's experience machine (1974) formalized it: most people decline guaranteed happiness if it means forfeiting authentic achievement.

Empirical evidence from revealed preferences (time use, consumption patterns, career choices) and stated preferences (Pew's "what makes life meaningful" surveys across 17 countries) points to people actually optimizing for **status, security, and belonging** — with happiness as a downstream byproduct, not the direct target. The Easterlin paradox (GDP growth above ~$60–80k household income doesn't raise average happiness) suggests feedback loops that would exist if populations were optimizing for happiness are absent.

This suggests capability and output metrics are closer to what people actually chase than happiness surveys.

### The two fundamental axes

If the question is *species* advancement rather than just economic output, two physics-grounded metrics emerge:

**Energy capture per capita** — the Kardashev scale (1964). Civilization advancement measured by energy harnessed: Type I (planetary), Type II (stellar), Type III (galactic). Humanity is currently ~Type 0.73. Chaisson's refinement — *energy rate density* (ergs/s/g) — captures thermodynamic complexity: bacteria ~0.5, human brain ~150,000, modern society ~500,000. Every major historical discontinuity (Industrial Revolution, post-WWII boom, China's rise) is visible in energy consumption before it shows up in GDP.

**Novel information consumed per capita** — the cognitive axis. Bohn & Short (2009) measured ~34 GB/person/day in modern America. Reconstructible historically via literacy rate × available corpus × reading time, with clear discontinuities at each communication technology: writing, printing press (~1450), telegraph, mass literacy (~1850), internet (~1995).

These two axes are not independent — Landauer's principle establishes a hard thermodynamic cost per bit processed. Energy and information are the same phenomenon viewed physically and cognitively.

### Institutional reach as the unifying latent variable

Both axes are downstream of a single latent variable: **institutional reach** — the radius within which people trust the system enough to cooperate with strangers rather than handle disputes personally.

Two historical proxies, both reconstructible to ~1200 AD:

**Homicide rate per 100k** (Eisner dataset, European records back to ~1200) — measures whether people defer to institutions vs. personal violence. The European decline from ~35 per 100k in medieval England to ~1 today tracks exactly with state formation and legal system development. Elias (*The Civilizing Process*, 1939) argued this was the internalization of "use law, not force" — the civilizing process as expanding trust in institutional dispute resolution.

**Market integration + contract density** — do prices converge across cities (market integration), and how rich is the available contract law (contract density)? Greif's comparison of Maghribi traders (tight in-group coalitions, limited trust radius) vs. Genoese traders (impersonal contract enforcement with strangers) shows the institutional difference that determined which model scaled. The Commenda contract (~1000 AD, Genoa and Venice) — the first documented instrument for investing with a stranger — was guaranteed by the merchant courts of the Italian city-states: the first time merchants *were* the government, creating aligned incentives between contract guarantors and contract users. The same logic runs through to North & Weingast's (1989) account of the 1688 Glorious Revolution making English property rights credible.

When homicide falls *and* contract density rises together, institutional trust is genuinely expanding — not just one dimension suppressed. This is the European 1300–1800 pattern that preceded and enabled the Industrial Revolution.

### Cooperative problem-solving radius

Institutional reach is the civilizational expression of a more fundamental metric: **cooperative problem-solving radius** — how large a group can coordinate, and how complex the problems they can collectively solve.

| Threshold | Coordination radius | Key enabler |
|---|---|---|
| Pre-language | ~band (50) | — |
| Language | ~tribe (150, Dunbar) | Shared mental models |
| Writing + law | ~city-state | Enforceable contracts with strangers |
| Markets + courts | ~trading network (millions) | Impersonal exchange |
| Print + mass literacy | ~nation | Shared information layer |
| Internet | ~global | Near-zero communication cost |
| AI | potentially unbounded | Automated synthesis and translation |

Every step in the GDP monitoring system's historical analysis maps onto this: the Maddison GDP data is the economic output of this radius compounding; institutional trust is the mechanism; energy and information are the substrate and structure.

### Long-run metric stack

Metrics trackable at 100–1000 year scales, in rough order of historical depth:

| Metric | Trackable from | Source |
|---|---|---|
| Real GDP per capita | 1 AD | Maddison Project |
| Urbanization rate | 2000+ years | Archaeological + census |
| Homicide rate per 100k | ~1200 | Eisner dataset |
| Energy per capita | ~1500 | Smil historical reconstructions |
| Literacy rate | ~1500 | Parish records, OECD back to ~1800 |
| Book production / corpus size | ~1450 | Buringh & van Zanden (2009); Dittmar (2011) |
| Market integration (price convergence) | ~1300 | Medieval price series |
| Generalized trust | 1981 | World Values Survey (direct); proxied earlier |

GDP and happiness are both downstream of institutional reach, which is downstream of cooperative radius, which is downstream of energy + information. The monitoring system's real-time signals (electricity, mobility) are the short-lag layer of this same structure.

---

## Tech and Science Trees

Human knowledge accumulation can be modeled as two interconnected directed acyclic graphs (DAGs):

**Science graph — edges are citations.** A paper cites what it builds on. Citation intent filtering (Semantic Scholar labels citations as background, method, or result) isolates genuine "enabled by" edges from comparison or background references. Best corpus: OpenAlex (~250M works, fully open, with concept taxonomy and citation links).

**Tech graph — edges are composition.** A technology is made of components; the "built out of" relationship is a cleaner dependency signal than citations. Sources: Wikidata `has_part` / `uses` / `made_from_material` relations, patent forward/backward citations (CPC classification), Wikipedia technology infoboxes.

**The science→tech bridge** — the cross-graph edge — is when a scientific discovery becomes a technology. Proxies: first patent citing a paper, first commercial product, time-lag between publication and application (well-studied in biotech/pharma).

### Granularity levels

| Level | Node count | Example |
|---|---|---|
| Civilization-game (major milestones) | 500–5,000 | Transformer architecture, CRISPR, printing press |
| Wikipedia/Wikidata (named items) | 50,000–100,000 | All named inventions and discoveries with articles |
| Paper/patent (full corpus) | 100M–250M | Every patent and academic paper |

The Wikidata level is the most tractable starting point: large enough to be meaningful, structured enough to have existing edges, small enough to visualize. Pruning to the ~10–20K most-connected nodes produces a navigable graph.

### Node attributes worth tracking

Each node should carry at minimum: date of first publication/deployment, prerequisite edges, and two separate attributes — **capability maturity** (when the underlying technique became reliable) and **adoption threshold crossing** (when it became accessible to non-experts). These often occur years apart and have different causes. ChatGPT (Nov 2022) crossed the adoption threshold for LLMs; the capability had existed in GPT-3 (2020). The Mosaic browser (1993) crossed the adoption threshold for the web; HTTP existed since 1991.

### Multi-track convergence as a pattern

Major innovations are rarely single-track. LLMs required simultaneous maturity across four independent tracks: transformer architecture (algorithms), GPU memory bandwidth (hardware), Common Crawl / LAION (data), and distributed mixed-precision training (infrastructure). The 2020–2025 window was identifiable as early as 2019 by modeling each track's trajectory independently.

Other convergence examples: aviation (aerodynamics + internal combustion + lightweight materials), smartphones (cellular + touchscreen + mobile CPU + lithium battery), nuclear weapons (physics theory + isotope separation + precision engineering).

A well-built tech tree with rate-of-progress metadata on each node could function as a leading indicator for future convergence events — identifying windows where multiple tracks are simultaneously maturing.

---

## Consumer Basket and Attention Economy

### The basket through history

Human consumption can be tracked at three granularities:

| Level | Count | Example |
|---|---|---|
| Categories | 20–50 | Food, shelter, transport, media, healthcare |
| Subcategories | 500–2,000 | Streaming video, ride-sharing, prescription drugs |
| Named products/brands | 100,000s | Netflix, Uber, ChatGPT |

For tracking "what entered the basket and when," subcategory granularity is most useful — specific enough to be meaningful, abstract enough to track across decades. Best historical source: **BLS Consumer Expenditure Survey** (US household spending by category since 1901).

### Attention as a displacement metric

Time is zero-sum in a way money is not — 24 hours is fixed. When a new product category enters the attention stack it must displace something else. This makes time-use data a cleaner measure of adoption than spending or MAU counts.

Traceable displacement chain:
- Radio displaced church/community gathering (1920s–30s)
- TV displaced radio + in-person socializing (1950s–60s)
- Internet partially displaced TV (2000s)
- Social/YouTube displaced linear TV for under-35s (2010s)
- TikTok displaced long-form video (2018+)

Each transition is measurable with time-use surveys at both endpoints. **American Time Use Survey (ATUS, 2003+)** covers recent transitions. Earlier data requires patchy academic studies (Robinson & Godbey *Time for Life* is the standard reference).

US daily time allocation — 1965 vs. 2023 (Robinson 1965 survey + ATUS/eMarketer 2023, all adults, all days):

| Activity | 1965 | 2023 | Δ |
|---|---|---|---|
| Sleep | 8.0 | 6.8 | −1.2 |
| Paid work | 4.5 | 3.6 | −0.9 |
| Household work | 3.5 | 1.8 | −1.7 |
| Childcare | 0.5 | 1.2 | +0.7 |
| Eating & drinking | 1.4 | 1.2 | −0.2 |
| Personal care | 0.9 | 0.8 | −0.1 |
| TV watching | 1.5 | 2.8 | +1.3 |
| Other digital / social / streaming | 0 | 2.5 | +2.5 |
| In-person socializing | 1.2 | 0.4 | −0.8 |
| Reading (print) | 0.5 | 0.1 | −0.4 |
| Radio / music | 0.4 | 0.3 | −0.1 |
| Religion / church | 0.3 | 0.1 | −0.2 |
| Sport / exercise | 0.2 | 0.3 | +0.1 |
| Education | 0.2 | 0.3 | +0.1 |
| Other leisure (hobbies, games, events) | 0.9 | 0.6 | −0.3 |
| **TOTAL** | **24.0** | **24.0** | — |

Caveats: 1965 numbers are Robinson's smaller-sample survey; "other digital" in 2023 is estimated from eMarketer/Data.ai since ATUS buckets it poorly; work drop is largely demographic composition (more retirees, more part-time), not individuals working fewer hours. The 2023 work figure for full-time employed adults is similar to 1965.

### The ad market as the price of attention

"Free" digital products are paid for in attention to ads. The ad market reveals the price:

- Meta: ~$130 revenue per US user per year ([Meta Q4 2023](https://investor.fb.com/))
- Average US user: ~180 hours/year on Facebook/Instagram
- Implied price: **~$0.70/hour of attention**

This enables a clean consumer surplus calculation: `surplus = value to user − (hours × attention market rate)`. Attention price varies by platform — search intent (Google) commands higher CPMs than passive social browsing.

Products outside the ad model (Wikipedia, iMessage, open source software) are **commons goods** — collectively produced, freely consumed, surplus almost entirely unmonetized. Wikipedia runs on ~$150M/year in donations while generating consumer surplus that, at Facebook CPM rates, would be worth billions annually.

### CPI's blind spots

CPI tracks the cost of a fixed basket — it cannot capture:
- **New goods problem:** price drops before a category enters the basket are invisible (mobile phones got 10x cheaper through the 1990s uncounted)
- **Quality adjustment:** a 2024 smartphone replaced camera, GPS, map, clock, calendar, newspaper, TV, radio — hedonic adjustment methods are inadequate for bundle displacements this large
- **Free goods:** Google, Wikipedia, Gmail have zero dollar cost but enormous consumer value. Brynjolfsson et al. (2019) estimated US consumer surplus from free internet services at $500B+/year — entirely absent from CPI ([NBER w25770](https://www.nber.org/papers/w25770))
- **Work usage:** AI tools used during work hours are classified as "working" in time-use surveys — the highest-frequency AI usage is invisible to consumer-side measurement

The attention-based framework handles the first three better than CPI. Work attention remains a systematic blind spot across all current methodologies.

---

## Simulating and Predicting History

### Approaches to simulating history

Four broad approaches, not mutually exclusive:

1. **Agent-based modeling (ABM)** — simulate individual actors (people, states, firms) with behavioral rules; macro-level history emerges from their interactions. Best for testing hypotheses about structural forces (geography, resources, population). Tools: Mesa (Python), NetLogo.
2. **System dynamics** — model stocks and flows (population, wealth, military capacity) with feedback loops. Good for long-run trends (rise and fall of empires, economic cycles). Turchin's cliodynamics is the canonical example.
3. **LLM-as-actor** — instantiate historical figures or factions as LLM agents with period-accurate context, have them make decisions, step forward in time. More narrative and qualitative; suited to counterfactuals ("what if Napoleon didn't invade Russia?").
4. **Data replay with perturbation** — take actual historical records, replay through a model, perturb parameters to study sensitivity ("what if the 1918 flu had 2x the CFR?").

The most promising current direction combines 3 and 1: LLM agents embedded in a structured world model that enforces physical and economic constraints, so decision-making is plausible without unconstrained hallucination.

---

### Predictability of historical events

Different categories have very different predictability profiles:

**Financial bubbles (dot-com 2000, housing 2008)** — most predictable. The structural signals were visible and named in advance. Shiller published equity overvaluation warnings in *Irrational Exuberance* (March 2000) and housing warnings in 2005. He won the Nobel in part for these calls. Minsky's credit cycle model (1970s) describes bubble formation mechanically. The hard part is timing, not direction.

**Technological revolutions (agricultural, industrial, AI)** — predictable in direction once enabling conditions are measurable, not in timing. Turing predicted machine intelligence in 1950. The AI revolution was foreseeable from compute cost curves (Wright's Law applied to GPU costs) by ~2015. The industrial revolution was invisible to contemporaries — Malthus wrote his population trap in 1798 at the exact moment steam power was breaking it.

**Geopolitical events** — lower predictability. Structural models (power transition theory, Turchin) give decade-scale risk windows, not specific triggers.

**The meta-pattern:** direction is more predictable than timing. People who called these events usually predicted the right thing too early, were ignored, and credited retroactively.

---

### Tetlock's superforecasting

Tetlock ran a 20-year forecasting tournament (Good Judgment Project / IARPA ACE) where thousands of people predicted geopolitical and economic events. The core method:

1. **Reference class first** — before thinking about specifics, ask "what's the base rate for events like this?"
2. **Decompose** — break the question into sub-questions estimable independently (Fermi style)
3. **Express as a probability** — not "likely" but a number; forces precision and enables calibration tracking
4. **Update incrementally** — when new evidence arrives, move a little, not a lot
5. **Track calibration** — are events you called 70% actually happening 70% of the time?

**Key finding:** superforecasters — random smart people with no special domain expertise — consistently outperformed CIA analysts with classified intelligence access. The edge came from reasoning process, not information. They are "foxes" (many small things) not "hedgehogs" (one big theory), actively seek disconfirming evidence, and are comfortable with 55% rather than rounding to 50% or 60%.

**Limitation:** works best for 1–2 year horizons on well-defined questions. Degrades for long-horizon structural shifts and doesn't handle true black swans outside the reference class.

---

### Frameworks for summarizing human history

Four complementary lenses:

**Energy and complexity (Big History — David Christian):** Humans have progressively captured more energy per capita — foragers → agriculture → fossil fuels → potentially nuclear/solar. Each step enabled more social complexity, specialization, and population. Most of history is explained by which energy transition is happening and where.

**Cooperation at scale (Harari — Sapiens):** The uniquely human trick is cooperating with strangers via shared fictions — gods, nations, money, laws. Agricultural surplus enabled cities; cities enabled states; states enabled armies and trade. The bottleneck throughout: how many unrelated people can you coordinate, and around what shared story?

**The Malthusian trap and the one escape:** For ~10,000 years after agriculture, productivity gains were absorbed by population growth — average living standards barely moved. The industrial revolution broke this for the first time. That is the central discontinuity in human history.

**Secular cycles (Turchin):** Within any era, recurring ~200-year cycles: integration (stability, growth) → elite overproduction → popular immiseration → instability → correction. Plays out inside civilizations regardless of which energy regime they are in.

**Short version:** Humans learned to cooperate at larger and larger scales, driven by energy transitions that periodically reset the ceiling on complexity. Progress is real but nonlinear — punctuated by instability when the institutions governing distribution cannot keep up with productive capacity.

---

### Inequality dynamics — r > g (Piketty)

**The fundamental identity:** When the return on capital (r) exceeds economic growth (g), wealth concentrates over time. This is the mathematical default. Averaged over all of human history, the gap is enormous: r has been ~4–5% across centuries and civilizations (medieval English land rents, Roman agricultural estates, modern asset portfolios all converge on this range), while g was near zero for ~99% of human history. The post-WWII period of g ≈ 3–4% was the historical anomaly.

**When r < g** — the exceptions:
- **Post-WWII Golden Age (~1945–1975):** Growth hit 4–6% in Western Europe while r was compressed by capital destruction, progressive taxation (top marginal rates 70–90% in US), capital controls, unions, and inflation. The combination has not recurred.
- **The Black Death (1347–1353):** Killed ~30–50% of Europe. Labor scarcity drove wages up and land values down. The most dramatic natural shock to r > g in recorded history.
- **Active wartime:** WWI, WWII — capital physically destroyed, inflated away, taxed heavily.
- **Catch-up industrialization:** South Korea, Taiwan, Japan (1950s–80s), China (1980s–2000s): g hit 8–10%+.

**Gini: not rising everywhere.** Within-country inequality has risen in most large economies since ~1980, consistent with r > g reasserting. But globally: Latin America's Gini has *fallen* since ~2000 (Brazil, Mexico, Peru); between-country inequality has *fallen* as China and India converged. Milanovic's **elephant curve** (income growth 1988–2008 by global percentile) captures both: large gains for the Asian middle class (10th–65th percentile), stagnation for the developed-world middle class (75th–90th percentile), large gains for the global top 1%. r > g predicts this — it governs within-country dynamics, not which countries grow fastest.

**If r > g long enough, does r become g?** Mathematically yes — at the limit, capital owners own everything and their reinvestment *is* the economy's investment (AK endogenous growth model: g = r × savings rate). In practice the system resets before convergence: Scheidel's *The Great Leveler* documents that sustained inequality compression has historically only occurred through war, plague, revolution, or state collapse.

**Proposed mechanisms:**
- **UBI as demand maintenance** — if capital returns are recycled into consumer spending, the loop becomes self-sustaining: capital → profits → UBI → consumer spending → profits. Alaska Permanent Fund and Norway's sovereign wealth fund are real implementations. Structural argument: UBI is demand insurance, not redistribution — it maintains the consumer base that makes r possible. Limitation: redistributes income (flow), not wealth (stock).
- **Wealth tax** — directly compresses r. If r = 5% and wealth tax = 2%, effective r drops to 3%. Empirical record is poor: France's ISF (1982–2017) repealed after capital flight; Sweden, Germany, Netherlands all tried and repealed. Core problems: valuation of illiquid assets, liquidity (asset-rich cash-poor owners forced to sell), capital mobility. A global wealth tax requires international coordination that has not materialized.

---

### Where we are now

By the major frameworks simultaneously:

- **Turchin:** disintegration phase — wealth inequality at 1920s levels, elite overproduction, declining institutional trust, fiscal stress. Predicted peak instability ~2020, published 2010.
- **Dalio:** late long-term debt cycle (~100 years, analogous to 1930s) overlapping with a US-China power transition — historically the highest-risk combination.
- **Big History:** AI as a cognitive energy transition — automating mental labor the way fossil fuels automated physical labor. Analogous to the 1780s of the industrial revolution: enabling technology exists and is spreading, but full restructuring is decades away.
- **Piketty:** r > g gap has widened since 1980 as the post-WWII compression unwound. Without new policy intervention or a catastrophic reset, the default trajectory continues.

The unusual feature of the current moment: all four frameworks point to the same decade as a transition window. Whether it resolves as breakdown, reformation, or absorption into a new equilibrium at higher complexity depends on contingent factors the structural models cannot predict.
