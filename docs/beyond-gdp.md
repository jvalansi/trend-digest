# Beyond GDP — Power, Stocks, and Other Gaps

Why GDP is incomplete as a measure of national position, what specifically it misses, and how much of the gap can be priced. Complements [`history-theory.md`](history-theory.md) (welfare gap) and [`gdp-monitoring-design.md`](gdp-monitoring-design.md) (monitoring the GDP signal itself).

---

## Three distinct axes, not one

GDP, welfare, and strategic capability are three different measurements that diverge in interesting cases.

| Axis | What it measures | Best proxy | Whose benefit |
|---|---|---|---|
| Output | What the country produces | GDP | Mixed (state + citizens) |
| Welfare | How citizens fare | WHR, life expectancy, trust | Citizens |
| Strategic capability | What the state can compel or deny | CINC, SIPRI, custom | State |

These can move in opposite directions:
- USSR 1980: high capability, mid output, low welfare
- Switzerland 2024: low capability, high output, high welfare
- North Korea 2024: high capability per capita, very low output and welfare
- Saudi Arabia 2024: oil-dominated mid output, modest citizen welfare, high state capability (oil swing)

Capability is state-only; welfare is citizen-only; output is mixed. Summing them loses information about which actor benefits, which is the point of keeping them separate.

---

## Strategic capability — the power axis

### Step-function instruments

Some capabilities have nonlinear payoffs: crossing a threshold gives the holder a *veto* over a system. Marginal additional units barely matter; the first unit changes the equilibrium.

**Nuclear weapons.** Discontinuity is 0 → 1 deliverable warhead. Below: invadable conventionally. Above: MAD makes invasion off the table. Secondary step: no second strike → secure second strike (SSBN, road-mobile ICBM). North Korea's 2017 *Hwasong-15* crossed this ([CSIS Missile Threat](https://missilethreat.csis.org/missile/hwasong-15/)).

**UN Security Council veto.** Binary, no seats added since 1945. Blocks UN-authorized military action against the holder; shields allies from sanctions resolutions. Russia 158 vetoes used to date, US 92 ([UN Dag Hammarskjöld Library](https://research.un.org/en/docs/sc/quick)). G4 (India, Japan, Germany, Brazil) has campaigned for additional seats since 2005 with no movement.

**Reserve currency status.** Gradations exist but with sharp top. USD ~58% of allocated reserves, EUR ~20%, RMB ~2% ([IMF COFER Q4 2024](https://data.imf.org/?sk=E6A5F467-C14B-4AA8-9F6D-5A09EC4E62A4)). Confers extraterritorial sanctions reach (SWIFT, correspondent banking) and lowest-cost borrowing ("exorbitant privilege," Giscard d'Estaing 1965).

**Chokepoint control.**
- TSMC: ~90% of <7nm logic ([TrendForce 2024](https://www.trendforce.com/)).
- ASML: sole EUV producer; Dutch jurisdiction, US-influenced via component dependencies.
- Suez: ~12–15% of global trade. Houthi attacks cut transits 42% in early 2024 ([UNCTAD](https://unctad.org/news/red-sea-crisis-suez-canal-transits-down-42-disrupting-global-trade)).
- Malacca: ~25% of seaborne oil, ~80% of China's oil imports ([EIA Chokepoints](https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints)). Hu Jintao's "Malacca Dilemma" (2003).
- OPEC+: ~3M bpd spare capacity, ~all in Saudi/UAE ([IEA OMR](https://www.iea.org/reports/oil-market-report-march-2025)).

### Flow rent vs. denial options

Each chokepoint generates two distinct streams:

1. **Flow rent** — what the holder earns by selling. Monetized, in GDP/valuations.
2. **Denial option** — the right to *refuse* sale under specified conditions. Not monetized; exercising usually requires forgoing flow rent.

Black-Scholes intuition: option value = intrinsic + time value. Flow rent is the intrinsic part. The "veto" is the time-value part — the right to deny under future states of the world. The state holds option #2 and rarely sells it because selling destroys it.

Calabresi & Melamed (1972, "[Property Rules, Liability Rules, and Inalienability](https://www.jstor.org/stable/1340059)") formalize this as the *inalienability rule*: some entitlements are deliberately non-tradable because exchange would destroy the social function.

Pattern: **when strategic value > monetary value, the holder refuses to monetize.** Iran/NK don't sell nuclear programs; Russia doesn't sell vetoes; Saudi 1973 embargo and 2022 production cut against Biden — both forewent revenue to exercise coercive option. TSMC would prefer to sell to Chinese firms; US export controls (Oct 2022 BIS rules) force it not to.

### What money can't buy

In a frictionless market, almost nothing. Power exists as a separate dimension because of structural market failures:

1. **Sellers who refuse at any price because selling destroys the asset.** North Korean nukes; US P5 veto; reserve currency privileges.
2. **Public-good commitments that require non-pricing for credibility.** NATO Article 5. Saudi Arabia has been trying to buy something equivalent since the 1940s and never has.
3. **Coercion of behavior, not extraction of goods.** Money buys movements within an equilibrium; power changes which equilibrium prevails (Lukes, [*Power: A Radical View*](https://philpapers.org/rec/LUKPAR)).
4. **Time-conditional options without underlying markets.** Right to freeze adversary central bank reserves contingent on event X. No counterparty.
5. **Legitimacy and recognition.** Russia's wealth didn't restore standing lost in 2022. India has campaigned for a P5 seat with the fifth-largest economy for 20 years.

Unifying pattern: anything non-fungible, credibility-dependent, or infrastructure-dependent resists monetization.

### Pricing denial options

Six methods, none complete on its own but they triangulate.

1. **Replacement cost.** What would the protected party pay to self-provide? Beckley ([*Unrivaled*, 2018](https://www.cornellpress.cornell.edu/book/9781501724787/unrivaled/)) estimates US allies underspend on defense by ~$300B/year vs. self-sufficient baseline.
2. **Cost imposed on denied party** (revealed-preference floor). China's semiconductor self-sufficiency spend: $47.5B Big Fund III ([Reuters May 2024](https://www.reuters.com/technology/china-launches-third-fund-boost-semiconductor-sector-with-475-bln-2024-05-27/)) + ~$73B earlier rounds = floor on US chip-denial value. Russia GDP ~5–7% below counterfactual ≈ $150B/year ([IMF Article IV 2024](https://www.imf.org/en/Publications/CR/Issues/2024/04/16/Russian-Federation-2023-Article-IV-Consultation-548080)).
3. **Insurance market analogues.** Sovereign CDS, marine war risk premia. Red Sea premiums went from 0.07% to 1% of hull value post-Houthi ([S&P Global Feb 2024](https://www.spglobal.com/marketintelligence/en/news-insights/latest-news-headlines/red-sea-attacks-push-up-war-risk-insurance-rates-by-up-to-50-78996918)) → ~$1.8B/year priced denial cost.
4. **Real options pricing.** Black-Scholes on the underlying flow. Crude but parametric.
5. **Convenience yield.** Reserve currency premium: Krishnamurthy & Vissing-Jorgensen estimate ~70bp ([NBER w17555](https://www.nber.org/papers/w17555)) on $26T marketable debt = $130–260B/year fiscal benefit.
6. **Exercise event accounting.** Frozen Russian reserves: ~$300B held; interest income (~$3B/year) flowing to Ukraine via EU mechanism = floor on what option was worth pre-exercise.

### Per-use depletion budget for sanctions

Sanctions reach is a depletable resource. Dollar share of allocated reserves fell from 58.4% (Q4 2021) to 57.4% (Q4 2024) — about 1pp over three years, with attribution to sanctions risk estimated at ~$60B per major event ([Arslanalp et al. IMF WP 2024](https://www.imf.org/en/Publications/WP/Issues/2024/06/11/Geopolitics-Sanctions-and-the-International-Reserves-Diversification-549937)).

Budget arithmetic: 58% to ~40% threshold = 18pp headroom. At ~2pp per major exercise (event + structural drift), ~9 more major uses available. Per-use damage capacity ~$750B over 5-year recovery (Russia precedent). Total ~$6.7T; NPV at 5%, 45-year exhaustion: ~$1.8T; annualized **~$90B/year** of exercise value alone. The unexercised-deterrent value is on top.

### US bundle aggregate

Method A — sum of flows:

| Component | Annual flow | Source |
|---|---|---|
| Nuclear umbrella to allies | $300B | Replacement cost (Beckley) |
| Reserve currency convenience yield | $180B | 70bp × $26T |
| Sanctions exercise (amortized) | $90B | Depletion budget |
| Sanctions threat compliance leverage | $400B | Imposed compliance + foregone-GDP transfers |
| Tech denial regime | $70B | China escape-spend ÷ tenor |
| Alliance burden-sharing | $150B | Replacement of CONUS-equivalent reach |
| Standards influence | $50B | Brussels/Bretton Woods institutional rents |
| **Total** | **~$1.24T/year** | **~4.3% of US GDP** |

Method B — cost to challenger. China spends ~$280B/year attempting to chip away (Belt & Road ~$100B + military modernization above baseline ~$130B + RMB internationalization ~$10B + tech self-sufficiency ~$50B). Apply 2–3× incumbent advantage → US position worth ~$600–840B/year to defend. Converges with Method A within order of magnitude.

NPV at 30-year horizon, 5% discount, 1.5% erosion: **~$18–22T present value** — roughly one full US GDP or ~80% of marketable federal debt.

### Nuclear weapons valuation, by holder

| Country | Warheads | Annual cost | Annual strategic value | Cost-to-value multiplier |
|---|---|---|---|---|
| US | 5,044 | $51B | $230–430B | 4–8× |
| Russia | 5,580 | ~$15–20B | $130–200B | 7–13× |
| China | ~500 (→ 1,000 by 2030) | ~$11B | $100–180B | 9–16× |
| UK | 225 | $3.8B | $30–50B | 8–12× |
| France | 290 | $5.4B | $30–50B | 6–10× |
| India | 172 | $2.7B | $40–70B | 13–23× |
| Pakistan | 170 | $1B | $30–50B | 30–50× |
| Israel | ~90 | $1B | $30–60B | 30–60× |
| North Korea | ~50 | $0.6–1B | $10–20B | 10–20× |

Sources: arsenal counts and program estimates from [SIPRI Yearbook 2024](https://www.sipri.org/yearbook/2024), [FAS Status of World Nuclear Forces](https://fas.org/initiatives/nuclear-information-project/status-world-nuclear-forces/), [ICAN 2024 spending report](https://www.icanw.org/2023_global_nuclear_weapons_spending_91_billion). US program: [CBO 2023](https://www.cbo.gov/publication/59054).

Global aggregate: **~$700B–1.1T/year strategic value against ~$92B/year cost.** Roughly 30–45% of total military-derived strategic value at ~4% of total military spending ([SIPRI mil-ex 2024](https://www.sipri.org/publications/2024/sipri-fact-sheets/trends-world-military-expenditure-2023)) — the lowest cost-to-value ratio of any major instrument of state power.

The cleanest natural experiment for value: Iraq (invaded 2003 after WMD program dismantled), Libya (Gaddafi gave up nuclear program 2003, toppled 2011), North Korea (nuclearized 2006, regime intact). The pattern explains Pakistan/Israel/NK extreme multipliers — for these holders nukes are the entire basis of regime/territorial continuity.

### GDP plus strategic value

| Country | 2024 GDP | Nuclear | Other strategic | Total strategic | % of GDP |
|---|---|---|---|---|---|
| US | $28.8T | $330B | $850B | $1,180B | 4.1% |
| China | $18.0T | $140B | $110B | $250B | 1.4% |
| Russia | $2.2T | $165B | $45B | $210B | 9.5% |
| Germany | $4.7T | 0 | $25B | $25B | 0.5% |
| Japan | $4.1T | 0 | $20B | $20B | 0.5% |
| India | $3.9T | $55B | $25B | $80B | 2.1% |
| UK | $3.6T | $40B | $50B | $90B | 2.5% |
| France | $3.0T | $40B | $25B | $65B | 2.2% |
| Saudi Arabia | $1.1T | 0 | $120B | $120B | 10.9% |
| Israel | $0.51T | $45B | $10B | $55B | 10.8% |
| Pakistan | $0.37T | $40B | $10B | $50B | 13.5% |
| North Korea | $0.030T (est) | $15B | $2B | $17B | 56.7% |

GDP from [World Bank 2024](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD), [IMF WEO Oct 2024](https://www.imf.org/en/Publications/WEO).

Pattern: **for states with GDP < $1T holding step-function instruments, strategic value is 10–60% of GDP; for states with GDP > $3T, at most a few percent.** The "punching above their weight" cluster (NK, Pakistan, Israel, Saudi, Russia) all hold step-function assets. The "punching below their weight" cluster (Germany, Japan, Korea, Brazil, Indonesia, Mexico) are large economies without strategic instruments — many consuming US umbrella value rather than producing their own.

Top of the GDP ranking is unchanged; Russia jumps ~3 ranks (11th → ~8th); North Korea becomes a meaningfully-ranked state from a statistical-floor one.

### What this calculation excludes

- **Existential externality.** Toby Ord ([*The Precipice*](https://theprecipice.com/)) estimates ~0.1%/year existential risk from nuclear war. Vast negative externality on humanity not borne by holders. The ~$700B–1.1T gross value to holders is plausibly negative net of humanity-wide cost.
- **Bundle synergy.** Reserve currency + sanctions + alliances + military reach reinforce each other. Cross-term positive but unbounded.
- **System credibility cost of exercise.** Each sanction use weakens the option for next time (de-dollarization). No market prices the stock depletion.
- **Zero-sum extraction.** Much strategic value is taken from someone else. Global aggregate is closer to a distribution shift than a production addition.
- **Endogeneity.** US GDP itself is partly the result of holding the position. The strategic income is spent in the US economy and counted as GDP. The numbers aren't independent.
- **Double-counting at the margin.** Defense spending is in GDP (government consumption). Strategic value is the *benefit*; cost is already in GDP. Net surplus = benefit − cost. Overstates the addition by roughly the cost basis (~$51B US nuclear program, ~$300B total defense) for major holders.

---

## Other gaps beyond strategic capability

Strategic capability is one missing dimension. There are at least four others.

### Measurement gaps inside GDP's framework

- **Non-market production.** Household work, childcare, eldercare, volunteer labor. ATUS data implies ~$3.8T/year of unpaid US household production at market wage rates. Waring's [*If Women Counted*](https://www.jstor.org/stable/40643691) is the canonical critique.
- **Informal/underground economy.** Schneider's panel estimates ~30–50% of GDP in developing economies, ~8–15% in advanced ([Schneider IZA DP 15184, 2022](https://www.iza.org/publications/dp/15184)).
- **Statistical capacity asymmetry.** Nigeria's 2014 GDP rebasing raised measured output 89%; Ghana 60%; Kenya 25%. Poor countries are systematically undercounted ([Jerven, *Poor Numbers*, 2013](https://www.cornellpress.cornell.edu/book/9780801478604/poor-numbers/)).
- **PPP vs. market exchange rates.** China $18T market, ~$35T PPP. Market rates for coercive economic weight; PPP for living standards. Two-fold gap for the same country.

### Stocks that flow-GDP ignores

- **Natural capital.** Pumping oil shows +$80 in GDP without −$80 from underground stock. Same for fish, forests, groundwater (Saudi/Iranian aquifers). World Bank [Adjusted Net Savings](https://www.worldbank.org/en/topic/natural-capital) and Inclusive Wealth Index attempt corrections; for resource exporters the gap can flip the growth sign.
- **Human capital.** $100B on schools is consumption in GDP, identical to $100B on entertainment. Treating education as investment changes growth accounting substantially (Mankiw-Romer-Weil 1992).
- **Institutional / social capital.** Trust, rule of law, contract enforcement — strong predictors of long-run growth (Acemoglu-Robinson Nobel 2024). No balance-sheet entry.
- **Net foreign assets.** US runs persistent current account deficits — consumption financed by foreign capital inflows. Norway runs surpluses, accumulating a $1.7T sovereign wealth fund. Same flow GDP, very different national net worth.

### Things GDP counts that aren't welfare

- **Defensive expenditure.** Security guards, anti-virus, insurance, lawyers, fences. Necessary because of bads; doesn't generate welfare. Nordhaus & Tobin (1972, [MEW](https://www.nber.org/system/files/chapters/c3621/c3621.pdf)) subtracted these.
- **Cleanup after disasters.** Hurricanes raise GDP. The 2020 Atlantic season added ~$60B in rebuild spending.
- **Healthcare cost vs. health outcome.** US 17% of GDP on healthcare with OECD-below-average life expectancy ([OECD Health Statistics 2024](https://www.oecd.org/health/health-statistics.htm)).
- **Prison economy.** US ~1.8M incarcerated; corrections + private prison ~$80B/year, all GDP-positive.

RFK's 1968 University of Kansas speech remains the cleanest articulation: GDP "measures everything in short, except that which makes life worthwhile."

### Distribution and risk — captured but invisible

- **Mean vs. median.** US GDP per capita ~$82K; median household income ~$80K. Norway GDP per capita ~$87K; median ~$72K. The mean-median gap is itself an inequality measure that GDP-per-capita masks.
- **Volatility.** Argentina and Australia have had broadly similar historical GDP per capita; Argentina's volatility makes that income worth substantially less in standard utility framework (Lucas 1987 welfare cost of business cycles, large for emerging markets).
- **Demographic discount.** Japan has high GDP today; current fertility trajectories project ~30% population decline by 2070. Current vs. sustainable income across generations are different quantities.

### What GDP isn't trying to measure

Already covered in [`history-theory.md`](history-theory.md):
- Welfare/happiness (WHR factors, Easterlin paradox, eudaimonia)
- Cooperative problem-solving radius / institutional reach
- Energy + information as civilization-scale axes

Plus:
- **Soft power / cultural reach.** K-pop, anime, Hollywood. Partially in services exports; agenda-setting and identity-shaping returns aren't.
- **Resource sovereignty.** Norway's oil in SWF vs. Nigeria's oil captured by elites and foreign majors. Same GDP contribution from oil, radically different national position.
- **Climate / geographic amenity.** Cross-country, climate quality is a real consumption good that doesn't flow through prices ([Albouy et al. 2016, "Climate Amenities"](https://www.aeaweb.org/articles?id=10.1257/aer.20141846)).

---

## The dashboard, not a single number

GDP is a *flow* of *market-priced* *current* *output*, with no adjustment for *distribution*, *sustainability*, *welfare*, *capability*, or *stock position*. Each gap corresponds to one missing dimension:

| Missing dimension | What it covers | Best existing measure |
|---|---|---|
| Stock | Natural, human, institutional, strategic capital, net foreign assets | Inclusive Wealth Index, World Bank wealth accounting |
| Non-market | Household production, free digital goods, leisure, amenity | ATUS, Brynjolfsson consumer surplus, GPI |
| Distribution | Median vs. mean, regional inequality | Gini, Atkinson, P50/mean ratio |
| Sustainability / risk | Depletion, climate damage, volatility, demographic trajectory | Adjusted Net Savings, Stern-style damage estimates |
| Welfare | Subjective well-being, meaning, capability (in Sen sense) | WHR, HDI, Sen-style capabilities |
| Strategic capability | What the state can compel or deny | CINC, SIPRI, custom (this doc) |

These don't combine cleanly into one number — the dimensions trade off against each other and against GDP itself. The honest version is a small dashboard — GDP + one stock measure + one distribution measure + one welfare measure + a capability proxy — rather than any single "better GDP."

The gap between GDP and what we actually care about isn't a single thing. GDP is one column of a national income statement; what we want is the balance sheet, the dispersion, and the sustainability footnotes alongside it.
