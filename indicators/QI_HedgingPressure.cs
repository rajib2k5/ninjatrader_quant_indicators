// ============================================================================
//  QI_HedgingPressure - Hedging Pressure composite score (-100 to +100)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #0
//            (ComputeHedgingPressure, Clamp, HP zone names, DrawHpTimeframeLines).
//  Provenance: NOT the hedging pressure of Basu & Miffre (2013), which is built from CFTC Commitments-of-
//            Traders positioning; this is a price/ATR/volume composite that borrows the name
//            (validation/channel-a-algo-2.md M15). Name kept by the user's decision.
//  Concept : A four-component proxy for hedger positioning built only from price
//            and volume: basis deviation from SMA20 in ATR units, short-vs-long
//            SMA slope divergence, volume/price divergence and range compression.
//            Each component is clamped to +/-25, the composite to +/-100.
//  Formula : basisScore = clamp((Close - SMA20) / ATR14 * -25, -25, 25)
//            termScore  = clamp((slope(SMA5) - slope(SMA20)) / ATR14 * -50, -25, 25)
//            vpScore    = clamp(dir * volRatio * 10, -25, 25) when volRatio > 1.2
//                         and |Close - Open| / ATR14 < 0.5 (dir = sign of candle)
//            rcScore    = clamp(dir * (1 - rangeRatio) * 50, -25, 25) when
//                         rangeRatio < 0.6 and volRatio > 1.3 (dir = Close vs SMA20)
//            HP         = clamp(basis + term + vp + rc, -100, 100); 0 when
//                         ATR14 <= 0 or SMA20 <= 0.
//  Zones   : <= -35 "Strong Short HP", <= -15 "Mod Short HP", < 15 "Neutral HP",
//            < 35 "Mod Long HP", else "Strong Long HP" (hard-coded in the original;
//            the +/-35 reference lines are configurable, the +/-15 zone lines are not).
//  Lines   : Daily/Weekly/Monthly HP price lines are drawn on the PRICE panel at
//            SMA20 + (HP / 100) * 2 * ATR14, where Weekly HP is the 5-bar and
//            Monthly HP the 20-bar simple average of the stored score series.
//  Quirks  : The original only computed HP from bar 50 onward (CurrentBar < 50
//            returns), so the stored score series is 0 before that; preserved.
//            The HP Daily Line Color property is kept for parity but the daily
//            line is drawn Green (score >= 0) / Red (score < 0) as in the original.
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
	public class QI_HedgingPressure : Indicator
	{
		// ── Hedging Pressure components ──
		private SMA		sma20hp;
		private SMA		closeSma5;
		private SMA		closeSma20;
		private SMA		rangeSma20;
		private SMA		volSma20;
		private ATR		atr14;
		private Series<double> hpScoreSeries;

		// ── HP multi-timeframe rolling averages (redraw suppression) ──
		private double	lastDailyHpLine;
		private double	lastWeeklyHpLine;
		private double	lastMonthlyHpLine;

		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Hedging Pressure: a four-component composite score (-100 to +100) built from "
											+ "basis deviation, SMA slope divergence, volume/price divergence and range compression. "
											+ "Daily/Weekly/Monthly HP price lines and the score panel are drawn on the price chart; "
											+ "the score itself is a hidden DataBox value. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_HedgingPressure";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;
				ShowTransparentPlotsInDataBox = true;

				ShowHpLines					= true;
				ShowDisclaimer				= false;

				HpDailyLineBrush			= Brushes.Yellow;
				HpWeeklyLineBrush			= Brushes.Orange;
				HpMonthlyLineBrush			= Brushes.DarkOrange;

				AddPlot(Brushes.Transparent, "HP Score");	// DataBox only (same scale trick as the original)
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				lastDailyHpLine		= double.NaN;
				lastWeeklyHpLine	= double.NaN;
				lastMonthlyHpLine	= double.NaN;
				disclaimerDrawn		= false;

				atr14		= ATR(14);
				volSma20	= SMA(Volume, 20);

				// HP indicators
				sma20hp		= SMA(Close, 20);
				closeSma5	= SMA(Close, 5);
				closeSma20	= SMA(Close, 20);
				rangeSma20	= SMA(Range(), 20);
				hpScoreSeries = new Series<double>(this);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 50)
				return;

			double hpScore = ComputeHedgingPressure();
			hpScoreSeries[0] = hpScore;
			Values[0][0] = hpScore;

			ProcessHpZone(hpScore);

			DrawDisclaimerOnce();
		}

		// ─────────────────────────────────────────────────────────
		//  Hedging Pressure Composite Score (-100 to +100)
		// ─────────────────────────────────────────────────────────
		private double ComputeHedgingPressure()
		{
			if (atr14[0] <= 0 || sma20hp[0] <= 0)
				return 0;

			double basisDev = (Close[0] - sma20hp[0]) / atr14[0];
			double basisScore = Clamp(basisDev * -25.0, -25, 25);

			double shortSlope = (closeSma5[0] > 0 && CurrentBar > 5)
				? (closeSma5[0] - closeSma5[1]) / atr14[0] : 0;
			double longSlope = (closeSma20[0] > 0 && CurrentBar > 20)
				? (closeSma20[0] - closeSma20[1]) / atr14[0] : 0;
			double slopeDiff = shortSlope - longSlope;
			double termScore = Clamp(slopeDiff * -50.0, -25, 25);

			double priceChangePct = (atr14[0] > 0)
				? Math.Abs(Close[0] - Open[0]) / atr14[0] : 1.0;
			double volRatio = (volSma20[0] > 0) ? Volume[0] / volSma20[0] : 1.0;
			double vpDivergence = 0;
			if (volRatio > 1.2 && priceChangePct < 0.5)
			{
				double direction = (Close[0] < Open[0]) ? -1.0 : 1.0;
				vpDivergence = direction * volRatio * 10.0;
			}
			double vpScore = Clamp(vpDivergence, -25, 25);

			double rangeRatio = (rangeSma20[0] > 0)
				? (High[0] - Low[0]) / rangeSma20[0] : 1.0;
			double rcScore = 0;
			if (rangeRatio < 0.6 && volRatio > 1.3)
			{
				double direction = (Close[0] < sma20hp[0]) ? -1.0 : 1.0;
				rcScore = Clamp(direction * (1.0 - rangeRatio) * 50.0, -25, 25);
			}

			double composite = basisScore + termScore + vpScore + rcScore;
			return Clamp(composite, -100, 100);
		}

		private static double Clamp(double value, double min, double max)
		{
			if (value < min) return min;
			if (value > max) return max;
			return value;
		}

		// ─────────────────────────────────────────────────────────
		//  HP Zone classification and timeframe lines
		//  Zone boundaries are the original's hard-coded -35/-15/15/35.
		//  Zone panel colors are the original's fixed defaults
		//  (Cyan for short-HP zones, Yellow for long-HP zones, Gray neutral).
		// ─────────────────────────────────────────────────────────
		private void ProcessHpZone(double hpScore)
		{
			string zoneName;
			Brush zoneBrush;

			if (hpScore <= -35)      { zoneName = "Strong Short HP"; zoneBrush = Brushes.Cyan; }
			else if (hpScore <= -15) { zoneName = "Mod Short HP";    zoneBrush = Brushes.Cyan; }
			else if (hpScore < 15)   { zoneName = "Neutral HP";      zoneBrush = Brushes.Gray; }
			else if (hpScore < 35)   { zoneName = "Mod Long HP";     zoneBrush = Brushes.Yellow; }
			else                     { zoneName = "Strong Long HP";  zoneBrush = Brushes.Yellow; }

			// ── Draw Daily / Weekly / Monthly HP lines ──
			if (ShowHpLines)
				DrawHpTimeframeLines(hpScore, zoneName, zoneBrush);
		}

		// ─────────────────────────────────────────────────────────
		//  Draw 3 horizontal lines: Daily / Weekly / Monthly HP
		// ─────────────────────────────────────────────────────────
		private void DrawHpTimeframeLines(double dailyHpScore, string zoneName, Brush zoneBrush)
		{
			double atr = atr14[0];
			double fairValue = sma20hp[0];
			if (atr <= 0 || fairValue <= 0) return;

			double dailyPrice = fairValue + (dailyHpScore / 100.0) * 2.0 * atr;

			double weeklyHpAvg = dailyHpScore;
			if (CurrentBar >= 5)
			{
				double sum = 0;
				int count = Math.Min(5, CurrentBar);
				for (int i = 0; i < count; i++)
					sum += hpScoreSeries[i];
				weeklyHpAvg = sum / count;
			}
			double weeklyPrice = fairValue + (weeklyHpAvg / 100.0) * 2.0 * atr;

			double monthlyHpAvg = dailyHpScore;
			if (CurrentBar >= 20)
			{
				double sum = 0;
				int count = Math.Min(20, CurrentBar);
				for (int i = 0; i < count; i++)
					sum += hpScoreSeries[i];
				monthlyHpAvg = sum / count;
			}
			double monthlyPrice = fairValue + (monthlyHpAvg / 100.0) * 2.0 * atr;

			// Daily HP line: Green = bullish (score > 0), Red = bearish (score < 0)
			Brush dailyHpBrush = dailyHpScore >= 0 ? Brushes.Green : Brushes.Red;

			double minMove = 0.25;
			bool needRedraw = double.IsNaN(lastDailyHpLine)
				|| Math.Abs(dailyPrice - lastDailyHpLine) > minMove
				|| Math.Abs(weeklyPrice - lastWeeklyHpLine) > minMove
				|| Math.Abs(monthlyPrice - lastMonthlyHpLine) > minMove;

			if (needRedraw)
			{
				lastDailyHpLine   = dailyPrice;
				lastWeeklyHpLine  = weeklyPrice;
				lastMonthlyHpLine = monthlyPrice;

				Draw.HorizontalLine(this, "HP_Daily", dailyPrice,
					dailyHpBrush, DashStyleHelper.Solid, 2);

				Draw.HorizontalLine(this, "HP_Weekly", weeklyPrice,
					HpWeeklyLineBrush, DashStyleHelper.Dash, 2);

				Draw.HorizontalLine(this, "HP_Monthly", monthlyPrice,
					HpMonthlyLineBrush, DashStyleHelper.DashDot, 2);
			}

			string labelText =
				  "Daily  HP: " + dailyHpScore.ToString("F0").PadLeft(4)
				+ "  |  Weekly HP: " + weeklyHpAvg.ToString("F0").PadLeft(4)
				+ "  |  Monthly HP: " + monthlyHpAvg.ToString("F0").PadLeft(4)
				+ "\n[" + zoneName + "]";

			Draw.TextFixed(this, "HP_ScorePanel", labelText, TextPosition.TopRight,
				zoneBrush, new SimpleFont("Consolas", 11) { Bold = true },
				Brushes.Transparent, Brushes.Black, 80);

			// Labels redrawn every bar so they track the rightmost bar
			SimpleFont priceFont = new SimpleFont("Arial", 9);

			string dailyMomentum = dailyHpScore >= 0 ? " (Bullish)" : " (Bearish)";
			Draw.Text(this, "HP_DailyLbl", false,
				"Daily HP " + dailyHpScore.ToString("F0") + dailyMomentum + " @ " + dailyPrice.ToString("F2"),
				0, dailyPrice, 5,
				dailyHpBrush, priceFont, TextAlignment.Right,
				Brushes.Transparent, Brushes.Transparent, 0);

			Draw.Text(this, "HP_WeeklyLbl", false,
				"Weekly HP " + weeklyHpAvg.ToString("F0") + " @ " + weeklyPrice.ToString("F2"),
				0, weeklyPrice, 5,
				HpWeeklyLineBrush, priceFont, TextAlignment.Right,
				Brushes.Transparent, Brushes.Transparent, 0);

			Draw.Text(this, "HP_MonthlyLbl", false,
				"Monthly HP " + monthlyHpAvg.ToString("F0") + " @ " + monthlyPrice.ToString("F2"),
				0, monthlyPrice, 5,
				HpMonthlyLineBrush, priceFont, TextAlignment.Right,
				Brushes.Transparent, Brushes.Transparent, 0);
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
			get { return "QI HedgingPressure"; }
		}

		#region Properties


		[NinjaScriptProperty]
		[Display(Name = "Show HP Lines", Description = "Draw Daily (green/red), Weekly (orange), Monthly (dark orange) HP lines on the price panel.",
			Order = 3, GroupName = "Parameters")]
		public bool ShowHpLines { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[XmlIgnore]
		[Display(Name = "HP Daily Line Color", Description = "Fallback color. Daily HP dynamically shows Green (bullish) or Red (bearish).",
			Order = 1, GroupName = "Colors")]
		public Brush HpDailyLineBrush { get; set; }
		[Browsable(false)]
		public string HpDailyLineBrushSerialize
		{ get { return Serialize.BrushToString(HpDailyLineBrush); } set { HpDailyLineBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "HP Weekly Line Color", Description = "Weekly hedging pressure line. Default Orange.",
			Order = 2, GroupName = "Colors")]
		public Brush HpWeeklyLineBrush { get; set; }
		[Browsable(false)]
		public string HpWeeklyLineBrushSerialize
		{ get { return Serialize.BrushToString(HpWeeklyLineBrush); } set { HpWeeklyLineBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "HP Monthly Line Color", Description = "Monthly hedging pressure line. Default DarkOrange.",
			Order = 3, GroupName = "Colors")]
		public Brush HpMonthlyLineBrush { get; set; }
		[Browsable(false)]
		public string HpMonthlyLineBrushSerialize
		{ get { return Serialize.BrushToString(HpMonthlyLineBrush); } set { HpMonthlyLineBrush = Serialize.StringToBrush(value); } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> HPScore
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
