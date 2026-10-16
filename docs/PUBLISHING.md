# Where these indicators can be published

Researched 2026-10-15. Every claim carries its source; items that could not be verified are
listed at the end. This is information, not legal advice.

## NinjaTrader — free: User App Share

- Page: https://ninjatraderecosystem.com/user-app-share/ ("100s of FREE TO USE apps & tools
  built by the user community").
- Submission form: https://ninjatraderecosystem.com/submit-your-app/ — "Submit for review".
  Stated requirements: the archive exported from NinjaTrader (`Tools › Export › NinjaScript`),
  **not loose source files**; `.zip`, max 8 MB; source only — no DLLs or external DLL
  references; screenshots PNG preferred, minimum 250 × 250 px; derivative work must credit the
  original author; the submitter indemnifies NinjaTrader; NinjaTrader may remove any submission
  at any time.
- Export how-to: https://static.ninjatrader.com/support/helpGuides/nt8/export.htm

This repository's indicators fit this channel as-is: source-only, no external DLLs, one
screenshot per indicator in `screenshots/`.

## NinjaTrader — commercial: Ecosystem vendor listing

- No public application form. The Ecosystem footer says "Interested in becoming a NinjaTrader
  Ecosystem 3rd party Vendor? Contact Us" (https://ninjatraderecosystem.com/); NinjaTrader staff
  direct vendor requests to info@ninjatraderecosystem.com and describe a vetting process
  (https://forum.ninjatrader.com/forum/ninjatrader-8/indicator-development/108644-3rd-party-licensing-api-for-vendors).
- After approval, vendors use https://ecosystem.ninjatrader.com/ and the Marketplace API for
  licensing (https://docs.ninjatrader.com/marketplace).
- Distribution is the same NinjaScript export; "Export as compiled assembly" hides source.
- Fees, revenue share, approval timeline and vendor-specific disclaimer requirements: **not
  published** on any official page found.
- Roadmap note: "Ecosystem 2.0" (https://developer.ninjatrader.com/blog/the-continued-evolution-of-the-ninjatrader-ecosystem).

There is no "NinjaTrader App Store" by that name: the Ecosystem is the commercial channel, User
App Share is the free community channel.

## Other platforms (all require a rewrite — NinjaScript does not run elsewhere)

| Platform | Language / format | Where to publish | Notes |
|---|---|---|---|
| TradingView | Pine Script | Community Scripts (https://www.tradingview.com/pine-script-docs/writing/publishing/) | Rules forbid "unsubstantiated performance claims"; paid scripts need vendor status (https://www.tradingview.com/support/solutions/43000590599-script-publishing-rules/) |
| MetaTrader 4/5 | MQL4/MQL5, compiled EX4/EX5 only | MQL5 Market (https://www.mql5.com/en/market/rules) | Seller ID verification; free allowed; paid min $30; 20% commission; automated pre-test |
| TradeStation | EasyLanguage | TradingApp Store (https://help.tradestation.com/10_00/eng/tradestationhelp/desktop/tradingapp_store.htm) | Developer onboarding not publicly documented |
| Sierra Chart | ACSIL (C++) → DLL | No store; distribute directly (https://www.sierrachart.com/index.php?page=doc/AdvancedCustomStudyInterfaceAndLanguage.php) | Optional listing on the third-party programmers page |
| MultiCharts | PowerLanguage, or C#/VB.NET (.NET 4.8) in MultiCharts .NET | No official marketplace found | Closest C# API to NinjaScript |
| cTrader | C# cTrader Algo (also Python), exported `.algo` | cTrader Store (https://help.ctrader.com/ctrader-store/how-tos/publish-a-product) | Verified seller; free or paid (min $19); 30% commission; 1-3 day review |
| QuantConnect | C# `IndicatorBase<>` / Python `PythonIndicator` in LEAN | Forum, or PR to LEAN (https://github.com/QuantConnect/Lean/blob/master/CONTRIBUTING.md) | PRs need unit tests |

## US regulatory awareness (not legal advice)

- A commodity trading advisor is a person who, "for compensation or profit, engages in the
  business of advising others" on futures/swaps; the definition excludes "the publisher or
  producer of any print or electronic data of general and regular dissemination" when advice is
  "solely incidental" (7 U.S.C. 1a(12), https://www.law.cornell.edu/uscode/text/7/1a).
- 17 CFR 4.14(a)(9) exempts from CTA registration those who do not direct client accounts or
  give advice tailored to particular clients; the CFTC's 2000 adopting release names
  "non-customized computer software" as covered media and notes exempt persons remain subject to
  the CEA antifraud provisions (https://www.law.cornell.edu/cfr/text/17/4.14;
  https://cftc.gov/foia/fedreg00/foi000310a.htm; NFA summary:
  https://www.nfa.futures.org/registration-membership/who-has-to-register/cta.html).
- Statistics-only tools with no signals arguably sit outside "trading advice"; no official source
  addresses that directly. Marketing them for securities would raise separate SEC
  investment-adviser questions that were not researched.

## Not verified

NinjaTrader Ecosystem vendor fees / revenue share / timelines / required disclosures; whether the
old forum "User App Submission" section still accepts posts (it now redirects); TradeStation
TradingApp Store developer terms; MultiCharts forum structure.
