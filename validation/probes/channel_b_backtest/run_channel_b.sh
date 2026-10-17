#!/usr/bin/env bash
# run_channel_b.sh - executes every Channel B backtest probe and its falsifier, verbatim log to $LOG.
# Usage (from the repo root):  bash validation/probes/channel_b_backtest/run_channel_b.sh SCRATCH_DIR
# Never writes under backtest/qibt (python -I -B everywhere; mutants live under SCRATCH_DIR).
set -u
S="$1"                                   # POSIX path of the scratch dir
SW="$(cygpath -w "$S")"
P=validation/probes/channel_b_backtest
LOG="$S/channel_b_run.log"
: > "$LOG"
PY="python -I -B"

run() {   # run <id> <command...>
	local id="$1"; shift
	{
		echo "################ $id"
		echo "\$ $*"
		local t0=$(date +%s.%N)
		"$@" 2>&1
		local rc=$?
		local t1=$(date +%s.%N)
		echo "rc=$rc  wall=$(python -I -c "print('%.2fs' % ($t1 - $t0))")"
	} >> "$LOG"
}

mut() {   # mut <name> <src_dir> <rel_file> <old> <new>
	run "MUTANT $1" $PY $P/_mutate.py "$2" "$SW\\mut_$1" "$3" "$4" "$5"
}

{
	echo "date: $(date)"
	python -I -c "import sys, numpy, pandas, yaml, scipy; print('python', sys.version.split()[0], 'numpy', numpy.__version__, 'pandas', pandas.__version__, 'pyyaml', yaml.__version__, 'scipy', scipy.__version__)"
	echo "repo HEAD: $(git rev-parse HEAD 2>/dev/null)"
} >> "$LOG"

Q=backtest/qibt
STR=strategies
# ---------------------------------------------------------------- probes on the original code / data
run "BT1+BT2 probe" $PY $P/bt01_02_contract_arith.py
run "BT4 probe" $PY $P/bt04_session_halt.py
run "BT6 probe" $PY $P/bt06_roll_jumps.py
run "BT7 probe" $PY $P/bt07_pnl_timing.py
run "BT8 probe" $PY $P/bt08_costs.py
run "BT8 supplementary edge" $PY $P/bt08_costs.py --edge
run "BT9 probe" $PY $P/bt09_sharpe.py
run "BT10 probe" $PY $P/bt10_psr.py
run "BT11 probe" $PY $P/bt11_dsr.py
run "BT12 probe" $PY $P/bt12_mdd.py
run "BT13 probe" $PY $P/bt13_rule_parity.py
run "BT14 probe" $PY $P/bt14_sessions.py
run "BT16 probe" $PY $P/bt16_guards.py
run "BT17 raw re-parse" $PY $P/raw_p1_parse.py "$SW\\raw_p1.pkl"
run "BT17 probe" $PY $P/bt17_integrity.py --raw "$SW\\raw_p1.pkl"
run "BT17 control (clean calendar)" $PY $P/bt17_integrity.py --control
mkdir -p "$S/compile"
run "BT15 compile probe" env OUT="$S/compile/all.dll" bash validation/probes/compile_probe.sh $STR/QS_*.cs indicators/QI_*.cs
run "BT18 run 1" $PY -m qibt.cli run --dataset P1 --costs 1 --out "$SW\\bt18_run1"
run "BT18 run 2" $PY -m qibt.cli run --dataset P1 --costs 1 --out "$SW\\bt18_run2"
run "BT18 run 3 (no cache: raw CSV re-read)" $PY -m qibt.cli run --dataset P1 --costs 1 --no-cache --out "$SW\\bt18_run3"
run "BT18 diff run1 vs run2" $PY $P/bt18_diff_runs.py "$SW\\bt18_run1" "$SW\\bt18_run2"
run "BT18 diff run1 vs run3" $PY $P/bt18_diff_runs.py "$SW\\bt18_run1" "$SW\\bt18_run3"
run "BT18 run1 vs committed results/ (byte compare)" bash -c "for f in metrics_P1.csv daily_pnl_P1.csv ranking.csv; do cmp '$S/bt18_run1/'\$f results/\$f && echo \"\$f identical\"; done"
run "XCHECK costs 1" $PY $P/xcheck_ranking.py --pkl "$SW\\raw_p1.pkl" --costs 1
run "XCHECK costs 0" $PY $P/xcheck_ranking.py --pkl "$SW\\raw_p1.pkl" --costs 0
run "XCHECK costs 2" $PY $P/xcheck_ranking.py --pkl "$SW\\raw_p1.pkl" --costs 2
run "XCHECK DSR tie-break on committed results" $PY $P/xcheck_dsr_tiebreak.py
# controls for the cross-check comparisons (scratch copies of results/, never the originals)
mkdir -p "$S/xc_swap" "$S/xc_perturb"
run "XCHECK control: make results copies (ranks 3/4 swapped; RSI14 SR + 2e-6)" $PY -c "
import pandas as pd, shutil, sys
S = sys.argv[1]
for f in ('metrics_P1.csv', 'ranking.csv', 'daily_pnl_P1.csv'):
    shutil.copy('results/' + f, S + '/xc_swap/' + f); shutil.copy('results/' + f, S + '/xc_perturb/' + f)
r = pd.read_csv(S + '/xc_swap/ranking.csv'); r.loc[r['rank'] == 3, 'rank'] = -4; r.loc[r['rank'] == 4, 'rank'] = 3; r.loc[r['rank'] == -4, 'rank'] = 4
r.sort_values('rank').to_csv(S + '/xc_swap/ranking.csv', index=False)
for f in ('metrics_P1.csv', 'ranking.csv'):
    d = pd.read_csv(S + '/xc_perturb/' + f); d.loc[d['module'] == 'RSI14', 'sr'] += 2e-6; d.to_csv(S + '/xc_perturb/' + f, index=False)
print('written', S + '/xc_swap', S + '/xc_perturb')
" "$SW"
run "XCHECK control A: tie-break check on a copy with ranks 3/4 swapped (must pass)" $PY $P/xcheck_dsr_tiebreak.py --results "$SW\\xc_swap"
run "XCHECK control B: re-computation vs a copy with RSI14 SR + 2e-6 (must report it)" $PY $P/xcheck_ranking.py --pkl "$SW\\raw_p1.pkl" --costs 1 --results "$SW\\xc_perturb"

# ---------------------------------------------------------------- falsifiers (module mutants)
mut bt1_pv50 $Q engine.py "POINT_VALUE = 5.0 " "POINT_VALUE = 50.0 "
run "BT1 falsifier" $PY $P/bt01_02_contract_arith.py --only BT1 --qibt-root "$SW\\mut_bt1_pv50"
mut bt2_tick $Q engine.py "TICK_SIZE = 0.25 " "TICK_SIZE = 0.50 "
run "BT2 falsifier" $PY $P/bt01_02_contract_arith.py --only BT2 --qibt-root "$SW\\mut_bt2_tick"
mut bt7_open_t $Q engine.py "gross[1: n - 1] = pt * (o[2:] - o[1: n - 1]) * point_value" "gross[1: n - 1] = pt * (o[1: n - 1] - o[: n - 2]) * point_value"
run "BT7 falsifier A (execute at Open_t)" $PY $P/bt07_pnl_timing.py --qibt-root "$SW\\mut_bt7_open_t"
mut bt7_lookahead $Q engine.py "pt = p[: n - 2] " "pt = p[1: n - 1] "
run "BT7 falsifier B (hold p_{t+1}: look-ahead)" $PY $P/bt07_pnl_timing.py --qibt-root "$SW\\mut_bt7_lookahead"
mut bt8_everybar $Q engine.py "sides[1: n - 1] = np.abs(pt - prev)" "sides[1: n - 1] = np.abs(pt)"
run "BT8 falsifier (cost on every held bar)" $PY $P/bt08_costs.py --qibt-root "$SW\\mut_bt8_everybar"
mut bt9_ddof0 $Q metrics.py "sd = float(np.std(a, ddof=1))" "sd = float(np.std(a, ddof=0))"
run "BT9 falsifier A (ddof=0)" $PY $P/bt09_sharpe.py --qibt-root "$SW\\mut_bt9_ddof0"
mut bt9_365 $Q metrics.py "ANNUALISATION = 252" "ANNUALISATION = 365"
run "BT9 falsifier B (sqrt 365)" $PY $P/bt09_sharpe.py --qibt-root "$SW\\mut_bt9_365"
mut bt10_drop1 $Q metrics.py "(kurt - 1.0) / 4.0" "kurt / 4.0"
run "BT10 falsifier (drop the -1 in (g4-1)/4)" $PY $P/bt10_psr.py --qibt-root "$SW\\mut_bt10_drop1"
mut bt11_swap $Q metrics.py "z = (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / n_trials) + g * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))" "z = g * _N.inv_cdf(1.0 - 1.0 / n_trials) + (1.0 - g) * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))"
run "BT11 falsifier A (swap gamma and 1-gamma)" $PY $P/bt11_dsr.py --qibt-root "$SW\\mut_bt11_swap"
mut bt11_neg $Q metrics.py "return math.sqrt(var_sr) * z" "return -math.sqrt(var_sr) * z"
run "BT11 falsifier B (SR0 sign flipped)" $PY $P/bt11_dsr.py --qibt-root "$SW\\mut_bt11_neg"
mut bt12_end $Q metrics.py "return float(np.max(np.maximum.accumulate(cum) - cum))" "return float(np.max(cum) - cum[-1])"
run "BT12 falsifier (peak minus final equity)" $PY $P/bt12_mdd.py --qibt-root "$SW\\mut_bt12_end"
mut bt14_roll18 $Q data.py "ROLL_HOUR = 17 " "ROLL_HOUR = 18 "
run "BT14 falsifier A (roll 17:00 -> 18:00)" $PY $P/bt14_sessions.py --qibt-root "$SW\\mut_bt14_roll18"
mut bt14_floor $Q data.py 'label = m1s["BarTime"].dt.ceil(' 'label = m1s["BarTime"].dt.floor('
run "BT14 falsifier B (left-labelled 15m: floor)" $PY $P/bt14_sessions.py --qibt-root "$SW\\mut_bt14_floor"
mut bt18_noise $Q engine.py "    return held, gross, sides" "    gross = gross + np.random.default_rng().normal(0.0, 1e-6, n)\n    return held, gross, sides"
run "BT18 falsifier run A" $PY $P/_cli_runner.py --qibt-root "$SW\\mut_bt18_noise" run --dataset P1 --costs 1 --no-cache --rules backtest/rules.yaml --out "$SW\\bt18_mutA"
run "BT18 falsifier run B" $PY $P/_cli_runner.py --qibt-root "$SW\\mut_bt18_noise" run --dataset P1 --costs 1 --no-cache --rules backtest/rules.yaml --out "$SW\\bt18_mutB"
run "BT18 falsifier diff" $PY $P/bt18_diff_runs.py "$SW\\bt18_mutA" "$SW\\bt18_mutB"

# ---------------------------------------------------------------- falsifiers (strategy-file mutants)
mut bt13_rsi45 $STR QS_RSI14.cs "bool goLong  = x < 40.0;" "bool goLong  = x < 45.0;"
run "BT13 falsifier A (RSI14 40 -> 45)" $PY $P/bt13_rule_parity.py --strategies "$SW\\mut_bt13_rsi45\\strategies"
mut bt13_ibsle $STR QS_IBS.cs "bool goLong  = x < 0.20;" "bool goLong  = x <= 0.20;"
run "BT13 falsifier B (IBS < -> <=)" $PY $P/bt13_rule_parity.py --strategies "$SW\\mut_bt13_ibsle\\strategies"
mut bt16_noguard $STR QS_RSI14.cs "\t\t\tif (BacktestOnly && State == State.Realtime) return;\n" ""
run "BT16 falsifier A (guard removed in QS_RSI14)" $PY $P/bt16_guards.py --strategies "$SW\\mut_bt16_noguard\\strategies"
mut bt16_deffalse $STR QS_SMC.cs "BacktestOnly\t\t\t\t= true;" "BacktestOnly\t\t\t\t= false;"
run "BT16 falsifier B (default false in QS_SMC)" $PY $P/bt16_guards.py --strategies "$SW\\mut_bt16_deffalse\\strategies"
mut bt15_typo $STR QS_RSI14.cs 'EnterLong(DefaultQuantity, "QS_L");' 'EnterLongTypo(DefaultQuantity, "QS_L");'
run "BT15 compile baseline (QS_RSI14 alone)" env OUT="$S/compile/rsi14.dll" bash validation/probes/compile_probe.sh $STR/QS_RSI14.cs
run "BT15 compile falsifier (undefined method)" env OUT="$S/compile/rsi14_mut.dll" bash validation/probes/compile_probe.sh "$S/mut_bt15_typo/strategies/QS_RSI14.cs"

# ---------------------------------------------------------------- falsifiers (data mutations)
run "BT4 falsifier A (bar at 16:30)" $PY $P/bt04_session_halt.py --inject halt
run "BT4 falsifier B (Saturday bar)" $PY $P/bt04_session_halt.py --inject saturday
run "BT6 falsifier A (unadjusted jump 4x median range)" $PY $P/bt06_roll_jumps.py --inject jump
run "BT6 falsifier B (ratio adjustment x1.003)" $PY $P/bt06_roll_jumps.py --inject ratio
run "BT17 falsifier (duplicated bar)" $PY $P/bt17_integrity.py --inject dup
echo "done: $LOG"
