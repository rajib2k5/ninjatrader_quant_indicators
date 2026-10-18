# Implementation notes - readings where PROTOCOL.md / rules.yaml / the ledger are silent

One line each. Written 2026-10-17 with the first implementation, before the results were read.

1. Trading date: "after 17:00" is strict - a bar closing exactly 17:00:00 keeps its calendar date (and is a halt bar).
2. Halt: a bar closing in (16:00, 17:00] CT makes the session builder raise (P1 has none); `--no-halt-check` disables it for other markets.
3. De-duplication "first wins" = first in file-name order (chronological for the MES_1min_* names), then row order; P1 had 0 duplicates.
4. Partial sessions are kept as they are (no synthetic bars), incl. the six 1-bar sessions at file starts (2020-01-03, 2021-02-02, 2022-02-01, 2023-02-02, 2024-03-04, 2025-04-02).
5. Bar 0 carries nothing; the last bar carries no P&L, but the change executed at its open is charged and held (fix of Channel B F3, 2026-10-17); the final position is not liquidated (no exit cost), as for buy-and-hold.
6. Every bar's P&L and cost are booked on the trading date of the holding bar t+1 (the execution bar), for both frames.
7. A 15m bar that is the last of its date earns until the next date's first open and is booked on its own date.
8. Window filter acts on that booking date, so a position opened in 2020 and still held on 2021-01-04 pays no entry cost inside the window.
9. Exposure = % of window days on which at least one bar was held with p != 0; long/short split = % of window frame bars held long / short and gross P&L by side.
10. Trades = number of execution bars in the window with p_t != p_{t-1}; sides = sum of |p_t - p_{t-1}| (a flip = 1 trade, 2 sides).
11. Max drawdown includes the starting equity 0 in the running peak.
12. Skewness and kurtosis use the biased moment estimators m3/m2^1.5 and m4/m2^2 (non-excess); the per-day SR uses std with ddof = 1.
13. V[SR] = sample variance (ddof = 1) of the per-day SRs of the rules with a finite SR in the same run (same dataset and cost multiplier); N = number of rules in rules.yaml (25).
14. SR is NaN when the daily P&L has zero variance; such rules rank after all finite-SR rules, A->Z, and are excluded from V[SR].
15. Tie rule: a tie cluster is a maximal run of the SR-descending order whose adjacent SRs differ by < 0.005 (strict); inside it DSR descending compared on log DSR (`dsr_log`, so values that underflow still decide), NaN last, then module A->Z (fix of Channel B F2: Phi = 0.5*erfc(-z/sqrt 2), asymptotic log tail below z = -37).
16. Pending rules get no rank; the non-backtestable modules still take numbers 26, 27 (n_rules + 1 ...), so relabel refuses an incomplete ranking (rank gaps).
17. Benchmark: p_t = +1 from the D bar before the first window date, so one side executes at the first evaluation open; its correlation uses daily net P&L at the same cost multiplier.
18. Correlation with buy-and-hold = Pearson on the daily net P&L series over the window calendar.
19. ibs_daily = qi_ref.ibs_bar on the D frame (the completed daily bar), not qi_ref.ibs_daily (the forming bar on an intraday chart).
20. bollinger_touch tests the Buy branch (-1) first, as ORIG does; NaN while Bollinger(20) is undefined (-> flat); ATR14 is the frame's ATR.
21. vwap_distance: VWAP and ATR14 on the 15m frame; qi_ref.SESSION_FLAG_COL = 1 on the first 15m bar of each trading date.
22. day_of_week uses qi_ref's default numbering (Sunday = 0 ... Saturday = 6, = .NET DayOfWeek used by ORIG), which already has Monday = 1; applied to the trading date.
23. turn_of_month and day_of_week are evaluated on the bar's trading date, not on its close-time calendar date.
24. overnight_gap_pct = qi_ref.gap_pct on the D frame: (Open_d - Close_{d-1}) / Close_{d-1} * 100, i.e. the 17:00 reopen vs the prior D close (16:00 last trade in v1, the settlement close in A1).
25. D-frame BarTime (passed to qi_ref / patterns) = close time of the date's last 1-minute bar.
26. Pattern values are called as qibt.patterns.<value>(frame with BarTime, Open..Volume); any import error, missing function, exception or wrong length marks the rule pending with the reason.
27. Long and short conditions holding on the same bar is an error (cannot happen with rules.yaml v1); NaN satisfies no condition.
28. Sensitivity runs (`--costs 0`, `--costs 2`) write suffixed files; the PROTOCOL section 8 ranking is the `--costs 1` file.
29. Non-P1 datasets use their own V[SR] unless `--var-sr` is given, and write ranking_<stem>.csv (the protocol ranks on P1 only).
30. Cache: pickle under backtest/data/, keyed by source file names, sizes and mtimes, loader version and pandas version; loader v2 adds databox_IBS (OHLCV read unchanged).
31. `python -I -m qibt.cli` needs the editable install (python -I drops the current directory from sys.path); tests do not (conftest adds backtest/ to sys.path).

## Amendment A1 (D-frame close) and the bootstrap - added 2026-10-17

32. IBS_ORIG = databox_IBS of the date's last 1-minute bar itself (an empty value there is "missing"; no earlier bar's value is used).
33. On-grid test uses the fixed 0.01-point tolerance of A1 (the validator's 0.00005*(H-L) gives 98.94% vs 98.86% of window dates); snapping rounds to the nearest 0.25.
34. Fallback order per A1: missing IBS_ORIG, H == L or off-grid -> close of the bar whose close time is exactly 15:00:00 on the trading date -> else the date's last close (a "last bar <= 15:00" reading is not used).
35. Datasets without databox_IBS (robustness CSVs) get the A1 fallback on every date; the branch counts are printed and written to REPORT.md.
36. `--close 1500` = the exact 15:00 bar's close, else the last close; High/Low/Open/Volume and the 15m frame are the same in all three modes.
37. Bootstrap index draws follow the order integers(n) for day 0, then per day random() < 1/mean_block -> integers(n), else (i+1) mod n (circular), on one Generator(seed) - the order the validator used, so its v1 numbers reproduce exactly.
38. Bootstrap inputs are the ranked rules' net daily P&L at 1x costs (BuyHold excluded); a resample with zero variance gives SR NaN and ranks that rule last.
39. BOOTSTRAP.md: "A1 top 4" and "adjacent ranks 1-8" use the published ranking.csv order (section 8 tie rule incl. DSR); CIs are numpy linear-interpolation 5th/95th percentiles.
40. SENSITIVITY.md ranks at 0x/2x come from each cost run's own ranking file; H1/H2 ranks order the A1 rules by that half's SR with ties (< 0.005) broken A->Z (no DSR per half).
41. The v1 files written before the F2/F3 fixes are kept in results/v1_last_trade/superseded_pre_F2_F3/; results/v1_last_trade/ holds v1 regenerated with the fixed engine and metrics.
