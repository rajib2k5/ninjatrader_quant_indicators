// ============================================================================
//  QI_SMC - Smart Money Concepts / ICT structure pattern detector (5 patterns)
//  Part of ninjatrader_quant_indicators
//
//  DISCLAIMER
//  This software is provided for educational and informational purposes only.
//  It is NOT financial, investment, or trading advice, and nothing it computes
//  or draws is a recommendation to buy or sell any instrument. Trading futures
//  and other leveraged products carries a substantial risk of loss and is not
//  suitable for every investor. Past performance is not indicative of future
//  results. You are solely responsible for any decision you make. See
//  DISCLAIMER.md in the repository root.
//
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plots #29-30.
//  Concept : Smart Money Concepts / ICT: Order Block retest (0.72), Fair Value Gap
//            entry (0.68), Break of Structure (0.60), Change of Character (0.75),
//            Displacement (0.58). Trend direction from HH+HL / LH+LL swing structure.
//  Output  : price-panel labels "SMC <first pattern> (conf%)", two panel plots
//            Confidence (0..1, best confidence of the bar, 0 when nothing fired)
//            and Structure (+1 bullish, -1 bearish, 0 none), plus a non-plot
//            TrendDir series (+1 / -1 / 0, the swing-structure trend each bar).
//  Quirks preserved from ORIG:
//            - Swing points update only once CurrentBar >= SwingLookback*2+5
//              (ORIG gates UpdateSwingPoints inside DetectLiquiditySweeps, 2040)
//              and are confirmed SwingLookback bars after the pivot.
//            - smcTrendDir only changes when BOTH last swing high and low make
//              HH+HL or LH+LL; otherwise it keeps its previous value (0 at start).
//            - Order Blocks: impulse bar = body > 0.75*range AND range > 1.5*ATR14;
//              zones kept max 5 per side, expire after 100 bars; FVG zones max 5
//              per side, expire after 50 bars. A zone is consumed on first touch.
//            - BOS uses the PREVIOUS swing high/low with a shared 5-bar cooldown
//              (lastBosBar), so a bearish BOS on the same bar as a bullish BOS is
//              blocked by the cooldown just set (ORIG 2666-2677).
//            - Direction is first-come: the first pattern to fire sets the
//              direction; later patterns only raise confidence.
//            - The ORIG CurrentBar < 20 guard is kept although the global
//              CurrentBar < 50 guard already covers it.
//            - volSma20 / atrSma50 / volDelta are maintained for parity with the
//              sibling pattern modules; SMC logic reads only ATR(14).
// ============================================================================
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// This namespace holds Indicators in this folder and is required. Do not change it.
namespace NinjaTrader.NinjaScript.Indicators
{
	public class QI_SMC : Indicator
	{
		// ── Local indicator instances ──
		private ATR		atr14;
		private SMA		volSma20;
		private SMA		atrSma50;
		private Series<double> volDelta;

		// ── Swing points ──
		private Series<double> swingHighSeries;
		private Series<double> swingLowSeries;
		private double		lastSwingHigh;
		private int			lastSwingHighBar;
		private double		lastSwingLow;
		private int			lastSwingLowBar;
		private double		prevSwingHigh;
		private int			prevSwingHighBar;
		private double		prevSwingLow;
		private int			prevSwingLowBar;

		// ── SMC/ICT state ──
		private List<double> obBullZoneHigh, obBullZoneLow;
		private List<int>    obBullBar;
		private List<double> obBearZoneHigh, obBearZoneLow;
		private List<int>    obBearBar;
		private List<double> fvgBullTop, fvgBullBottom;
		private List<int>    fvgBullBar;
		private List<double> fvgBearTop, fvgBearBottom;
		private List<int>    fvgBearBar;
		private int			smcTrendDir;		// 1=bullish, -1=bearish, 0=undefined
		private int			lastSmcDir;
		private int			barsSinceLastSmc;
		private int			lastBosBar;

		// ── Exposed non-plot series ──
		private Series<double> trendDirSeries;

		private bool		disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Smart Money Concepts / ICT pattern detector: Order Block retest, Fair Value Gap, "
											+ "Break of Structure, Change of Character and Displacement. "
											+ "Draws pattern-name labels on the price panel and plots Confidence (0..1) "
											+ "and Structure (+1/-1/0). "
											+ "Educational use only - not financial advice.";
				Name						= "QI_SMC";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				SwingLookback				= 20;

				// Display
				TextOffsetTicks				= 15;
				SignalFontSize				= 13;
				DuplicateBarWindow			= 5;
				ShowDisclaimer				= true;

				// Colors
				SmcBullishBrush				= Brushes.DeepSkyBlue;
				SmcBearishBrush				= Brushes.OrangeRed;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Bar, "Confidence");
				AddPlot(new Stroke(Brushes.DodgerBlue, 2), PlotStyle.Bar, "Structure");
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				atr14		= ATR(14);
				volSma20	= SMA(Volume, 20);
				atrSma50	= SMA(atr14, 50);
				volDelta	= new Series<double>(this);

				// ── Swing point initialization ──
				swingHighSeries		= new Series<double>(this);
				swingLowSeries		= new Series<double>(this);
				lastSwingHigh		= double.MinValue;
				lastSwingHighBar	= 0;
				lastSwingLow		= double.MaxValue;
				lastSwingLowBar		= 0;
				prevSwingHigh		= double.MinValue;
				prevSwingHighBar	= 0;
				prevSwingLow		= double.MaxValue;
				prevSwingLowBar		= 0;

				// ── SMC/ICT init ──
				obBullZoneHigh = new List<double>(); obBullZoneLow = new List<double>(); obBullBar = new List<int>();
				obBearZoneHigh = new List<double>(); obBearZoneLow = new List<double>(); obBearBar = new List<int>();
				fvgBullTop = new List<double>(); fvgBullBottom = new List<double>(); fvgBullBar = new List<int>();
				fvgBearTop = new List<double>(); fvgBearBottom = new List<double>(); fvgBearBar = new List<int>();
				smcTrendDir = 0; lastSmcDir = 0; barsSinceLastSmc = int.MaxValue; lastBosBar = 0;

				trendDirSeries		= new Series<double>(this);

				disclaimerDrawn		= false;
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 50)
				return;

			UpdateVolumeDelta();

			Values[0][0] = 0;
			Values[1][0] = 0;

			// ORIG updates swing points inside DetectLiquiditySweeps (gated at
			// CurrentBar < SwingLookback*2+5, ORIG 2040) before ProcessSmcSignals.
			if (CurrentBar >= SwingLookback * 2 + 5)
				UpdateSwingPoints();

			ProcessSmcSignals();

			trendDirSeries[0] = smcTrendDir;

			DrawDisclaimerOnce();
		}

		// ─────────────────────────────────────────────────────────
		//  Volume delta
		// ─────────────────────────────────────────────────────────
		private void UpdateVolumeDelta()
		{
			if (CurrentBar < 1) { volDelta[0] = 0; return; }

			double priceChange = Close[0] - Close[1];
			if (priceChange > 0)
				volDelta[0] = Volume[0];
			else if (priceChange < 0)
				volDelta[0] = -Volume[0];
			else
				volDelta[0] = 0;
		}

		// ─────────────────────────────────────────────────────────
		//  Swing points (N-bar pivots): prev/last swing highs and lows
		//  Equal-level pool bookkeeping and cumulative-delta snapshots from
		//  ORIG 2090-2137 are omitted: neither is read by the SMC logic.
		// ─────────────────────────────────────────────────────────
		private void UpdateSwingPoints()
		{
			swingHighSeries[0] = double.NaN;
			swingLowSeries[0]  = double.NaN;
			int lb = SwingLookback;
			if (CurrentBar < lb * 2) return;

			double candidateHigh = High[lb];
			bool isSwingHigh = true;
			for (int i = 0; i <= lb * 2; i++)
			{ if (i == lb) continue; if (High[i] > candidateHigh) { isSwingHigh = false; break; } }
			if (isSwingHigh)
			{
				swingHighSeries[lb] = candidateHigh;
				prevSwingHigh = lastSwingHigh; prevSwingHighBar = lastSwingHighBar;
				lastSwingHigh = candidateHigh; lastSwingHighBar = CurrentBar - lb;
			}

			double candidateLow = Low[lb];
			bool isSwingLow = true;
			for (int i = 0; i <= lb * 2; i++)
			{ if (i == lb) continue; if (Low[i] < candidateLow) { isSwingLow = false; break; } }
			if (isSwingLow)
			{
				swingLowSeries[lb] = candidateLow;
				prevSwingLow = lastSwingLow; prevSwingLowBar = lastSwingLowBar;
				lastSwingLow = candidateLow; lastSwingLowBar = CurrentBar - lb;
			}
		}

		// ─────────────────────────────────────────────────────────
		//  SMC/ICT Signal Detection (5 patterns)
		//  Order Block, Fair Value Gap, Break of Structure,
		//  Change of Character, Displacement
		// ─────────────────────────────────────────────────────────
		private void ProcessSmcSignals()
		{
			if (CurrentBar < 20) return;
			barsSinceLastSmc++;

			// ── Update trend direction from swing structure ──
			if (lastSwingHigh > double.MinValue && prevSwingHigh > double.MinValue)
			{
				if (lastSwingHigh > prevSwingHigh && lastSwingLow > prevSwingLow)
					smcTrendDir = 1;  // bullish: HH + HL
				else if (lastSwingHigh < prevSwingHigh && lastSwingLow < prevSwingLow)
					smcTrendDir = -1; // bearish: LH + LL
			}

			double body  = Math.Abs(Close[0] - Open[0]);
			double range = High[0] - Low[0];
			double atrVal = atr14[0];

			// ── Maintain Order Block zones ──
			// Detect impulsive candle → record previous candle as OB
			if (CurrentBar >= 2 && range > 0 && body > 0.75 * range && range > 1.5 * atrVal)
			{
				if (Close[0] > Open[0])
				{
					// Bullish impulse → last bearish candle = Bullish OB
					if (Close[1] < Open[1])
					{
						if (obBullZoneHigh.Count >= 5) { obBullZoneHigh.RemoveAt(0); obBullZoneLow.RemoveAt(0); obBullBar.RemoveAt(0); }
						obBullZoneHigh.Add(High[1]); obBullZoneLow.Add(Low[1]); obBullBar.Add(CurrentBar - 1);
					}
				}
				else
				{
					// Bearish impulse → last bullish candle = Bearish OB
					if (Close[1] > Open[1])
					{
						if (obBearZoneHigh.Count >= 5) { obBearZoneHigh.RemoveAt(0); obBearZoneLow.RemoveAt(0); obBearBar.RemoveAt(0); }
						obBearZoneHigh.Add(High[1]); obBearZoneLow.Add(Low[1]); obBearBar.Add(CurrentBar - 1);
					}
				}
			}

			// ── Maintain FVG zones ──
			if (CurrentBar >= 3)
			{
				// Bullish FVG: Low[0] > High[2] (gap up)
				if (Low[0] > High[2])
				{
					if (fvgBullTop.Count >= 5) { fvgBullTop.RemoveAt(0); fvgBullBottom.RemoveAt(0); fvgBullBar.RemoveAt(0); }
					fvgBullTop.Add(Low[0]); fvgBullBottom.Add(High[2]); fvgBullBar.Add(CurrentBar);
				}
				// Bearish FVG: High[0] < Low[2] (gap down)
				if (High[0] < Low[2])
				{
					if (fvgBearTop.Count >= 5) { fvgBearTop.RemoveAt(0); fvgBearBottom.RemoveAt(0); fvgBearBar.RemoveAt(0); }
					fvgBearTop.Add(Low[2]); fvgBearBottom.Add(High[0]); fvgBearBar.Add(CurrentBar);
				}
			}

			// Expire old zones
			for (int i = obBullBar.Count - 1; i >= 0; i--)
				if (CurrentBar - obBullBar[i] > 100) { obBullZoneHigh.RemoveAt(i); obBullZoneLow.RemoveAt(i); obBullBar.RemoveAt(i); }
			for (int i = obBearBar.Count - 1; i >= 0; i--)
				if (CurrentBar - obBearBar[i] > 100) { obBearZoneHigh.RemoveAt(i); obBearZoneLow.RemoveAt(i); obBearBar.RemoveAt(i); }
			for (int i = fvgBullBar.Count - 1; i >= 0; i--)
				if (CurrentBar - fvgBullBar[i] > 50) { fvgBullTop.RemoveAt(i); fvgBullBottom.RemoveAt(i); fvgBullBar.RemoveAt(i); }
			for (int i = fvgBearBar.Count - 1; i >= 0; i--)
				if (CurrentBar - fvgBearBar[i] > 50) { fvgBearTop.RemoveAt(i); fvgBearBottom.RemoveAt(i); fvgBearBar.RemoveAt(i); }

			// ── Check for signals ──
			var patterns = new List<string>();
			double bestConf = 0;
			int smcDir = 0;

			// Pattern 1: OB Retest (conf 0.72)
			for (int i = obBullBar.Count - 1; i >= 0; i--)
			{
				if (Low[0] <= obBullZoneHigh[i] && Low[0] >= obBullZoneLow[i])
				{
					smcDir = 1; bestConf = Math.Max(bestConf, 0.72); patterns.Add("OB Retest");
					obBullZoneHigh.RemoveAt(i); obBullZoneLow.RemoveAt(i); obBullBar.RemoveAt(i);
					break;
				}
			}
			for (int i = obBearBar.Count - 1; i >= 0; i--)
			{
				if (High[0] >= obBearZoneLow[i] && High[0] <= obBearZoneHigh[i])
				{
					if (smcDir == 0) smcDir = -1;
					bestConf = Math.Max(bestConf, 0.72); patterns.Add("OB Retest");
					obBearZoneHigh.RemoveAt(i); obBearZoneLow.RemoveAt(i); obBearBar.RemoveAt(i);
					break;
				}
			}

			// Pattern 2: FVG Entry (conf 0.68)
			for (int i = fvgBullBar.Count - 1; i >= 0; i--)
			{
				if (Low[0] <= fvgBullTop[i] && Close[0] >= fvgBullBottom[i])
				{
					if (smcDir == 0) smcDir = 1;
					bestConf = Math.Max(bestConf, 0.68); patterns.Add("FVG");
					fvgBullTop.RemoveAt(i); fvgBullBottom.RemoveAt(i); fvgBullBar.RemoveAt(i);
					break;
				}
			}
			for (int i = fvgBearBar.Count - 1; i >= 0; i--)
			{
				if (High[0] >= fvgBearBottom[i] && Close[0] <= fvgBearTop[i])
				{
					if (smcDir == 0) smcDir = -1;
					bestConf = Math.Max(bestConf, 0.68); patterns.Add("FVG");
					fvgBearTop.RemoveAt(i); fvgBearBottom.RemoveAt(i); fvgBearBar.RemoveAt(i);
					break;
				}
			}

			// Pattern 3: BOS (conf 0.60)
			if (prevSwingHigh > double.MinValue && Close[0] > prevSwingHigh && CurrentBar - lastBosBar > 5)
			{
				if (smcDir == 0) smcDir = 1;
				bestConf = Math.Max(bestConf, 0.60); patterns.Add("BOS");
				lastBosBar = CurrentBar;
			}
			if (prevSwingLow < double.MaxValue && Close[0] < prevSwingLow && CurrentBar - lastBosBar > 5)
			{
				if (smcDir == 0) smcDir = -1;
				bestConf = Math.Max(bestConf, 0.60); patterns.Add("BOS");
				lastBosBar = CurrentBar;
			}

			// Pattern 4: CHoCH (conf 0.75)
			if (smcTrendDir == 1 && lastSwingLow < double.MaxValue && Close[0] < lastSwingLow)
			{
				if (smcDir == 0) smcDir = -1;
				bestConf = Math.Max(bestConf, 0.75); patterns.Add("CHoCH");
			}
			if (smcTrendDir == -1 && lastSwingHigh > double.MinValue && Close[0] > lastSwingHigh)
			{
				if (smcDir == 0) smcDir = 1;
				bestConf = Math.Max(bestConf, 0.75); patterns.Add("CHoCH");
			}

			// Pattern 5: Displacement (conf 0.58)
			if (range > 0 && body > 0.75 * range && range > 1.5 * atrVal)
			{
				int dispDir = Close[0] > Open[0] ? 1 : -1;
				if (smcDir == 0) smcDir = dispDir;
				bestConf = Math.Max(bestConf, 0.58); patterns.Add("Displacement");
			}

			if (patterns.Count == 0 || smcDir == 0) return;
			if (smcDir == lastSmcDir && barsSinceLastSmc < DuplicateBarWindow) return;

			bestConf = Math.Min(bestConf, 1.0);
			bool isBull = smcDir == 1;
			int confPct = (int)Math.Round(bestConf * 100);
			string label = "SMC " + patterns[0] + " (" + confPct + "%)";

			SimpleFont font = new SimpleFont("Arial", SignalFontSize) { Bold = true };
			double anchor = isBull ? Low[0] : High[0];
			int offset = isBull ? -(TextOffsetTicks + 20) : (TextOffsetTicks + 20);
			Brush brush = isBull ? SmcBullishBrush : SmcBearishBrush;
			string tag = (isBull ? "SMC_Bull_" : "SMC_Bear_") + CurrentBar;
			Draw.Text(this, tag, true, label, 0, anchor, offset,
				brush, font, TextAlignment.Center,
				Brushes.Transparent, Brushes.Transparent, 0);

			// Panel plots: confidence and structure direction for this bar
			Values[0][0] = bestConf;
			Values[1][0] = smcDir;

			lastSmcDir = smcDir;
			barsSinceLastSmc = 0;
		}

		private void DrawDisclaimerOnce()
		{
			if (!ShowDisclaimer || disclaimerDrawn)
				return;

			Draw.TextFixed(this, "QI_Disclaimer", "Educational use only - not financial advice",
				TextPosition.BottomLeft, Brushes.Gray, new SimpleFont("Arial", 9),
				Brushes.Transparent, Brushes.Transparent, 0);
			disclaimerDrawn = true;
		}

		public override string DisplayName
		{
			get { return "QI SMC"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(5, 50)]
		[Display(Name = "Swing Lookback",
			Description = "N-bar pivot point lookback for swing high/low detection. Default 20.",
			Order = 1, GroupName = "Parameters")]
		public int SwingLookback { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Text Offset (pixels)", Description = "Pixel offset from bar high/low.",
			Order = 1, GroupName = "Display")]
		public int TextOffsetTicks { get; set; }

		[NinjaScriptProperty]
		[Range(6, 30)]
		[Display(Name = "Signal Font Size",
			Order = 2, GroupName = "Display")]
		public int SignalFontSize { get; set; }

		[NinjaScriptProperty]
		[Range(1, 50)]
		[Display(Name = "Duplicate Bar Window", Description = "Suppress same-direction label within N bars. Default 5",
			Order = 3, GroupName = "Display")]
		public int DuplicateBarWindow { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 4, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[XmlIgnore]
		[Display(Name = "SMC Bullish Color", Description = "SMC/ICT bullish-structure label color. Default DeepSkyBlue.",
			Order = 1, GroupName = "Colors")]
		public Brush SmcBullishBrush { get; set; }
		[Browsable(false)]
		public string SmcBullishBrushSerialize
		{ get { return Serialize.BrushToString(SmcBullishBrush); } set { SmcBullishBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "SMC Bearish Color", Description = "SMC/ICT bearish-structure label color. Default OrangeRed.",
			Order = 2, GroupName = "Colors")]
		public Brush SmcBearishBrush { get; set; }
		[Browsable(false)]
		public string SmcBearishBrushSerialize
		{ get { return Serialize.BrushToString(SmcBearishBrush); } set { SmcBearishBrush = Serialize.StringToBrush(value); } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Confidence
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Structure
		{
			get { return Values[1]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> TrendDir
		{
			get { return trendDirSeries; }
		}

		#endregion
	}
}
