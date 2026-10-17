#!/usr/bin/env bash
# run_data_falsifiers_pinned.sh - re-run the P1-data probes (BT4, BT6, BT17) and their data falsifiers
# pinned to a given qibt package root (e.g. a sha256-verified copy of the audited version) and to
# Channel B's own raw re-parse of P1 (raw_p1.pkl, shown identical to the audited loaded P1), so the
# result does not depend on whatever backtest/qibt or backtest/data hold at run time.
# Usage (from the repo root): bash .../run_data_falsifiers_pinned.sh SCRATCH_DIR QIBT_ROOT
set -u
S="$1"; SW="$(cygpath -w "$S")"; R="$(cygpath -w "$2")"
P=validation/probes/channel_b_backtest
LOG="$S/channel_b_pinned.log"
: > "$LOG"
PY="python -I -B"
run() {
	local id="$1"; shift
	{ echo "################ $id"; echo "\$ $*"; "$@" 2>&1; echo "rc=$?"; } >> "$LOG"
}
echo "date: $(date)" >> "$LOG"
X=(--qibt-root "$R" --pkl "$SW\\raw_p1.pkl")
run "PINNED BT4 probe" $PY $P/bt04_session_halt.py "${X[@]}"
run "PINNED BT4 falsifier A (bar at 16:30)" $PY $P/bt04_session_halt.py "${X[@]}" --inject halt
run "PINNED BT4 falsifier B (Saturday bar)" $PY $P/bt04_session_halt.py "${X[@]}" --inject saturday
run "PINNED BT6 probe" $PY $P/bt06_roll_jumps.py "${X[@]}"
run "PINNED BT6 falsifier A (unadjusted jump 4x median range)" $PY $P/bt06_roll_jumps.py "${X[@]}" --inject jump
run "PINNED BT6 falsifier B (ratio adjustment x1.003)" $PY $P/bt06_roll_jumps.py "${X[@]}" --inject ratio
run "PINNED BT17 probe" $PY $P/bt17_integrity.py "${X[@]}"
run "PINNED BT17 falsifier (duplicated bar)" $PY $P/bt17_integrity.py "${X[@]}" --inject dup
run "PINNED BT17 control (clean calendar)" $PY $P/bt17_integrity.py --qibt-root "$R" --control
# cross-check pinned to the same v1 copy, against the v1 results (moved to results/v1_last_trade)
if [ -d results/v1_last_trade ]; then RES=results/v1_last_trade; else RES=results; fi
run "PINNED XCHECK costs 1" $PY $P/xcheck_ranking.py "${X[@]}" --costs 1 --results "$RES"
run "PINNED XCHECK DSR tie-break" $PY $P/xcheck_dsr_tiebreak.py --results "$RES"
echo "done: $LOG"
