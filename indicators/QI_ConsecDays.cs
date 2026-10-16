// ============================================================================
//  QI_ConsecDays - Consecutive up/down close streak (signed)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #8
//            (streak update ORIG 1552-1568, value ORIG 1342-1346).
//  Concept : Consecutive-day streaks, Connors.
//  Formula : Close[0] > Close[1] -> consecUp++, consecDown = 0
//            Close[0] < Close[1] -> consecDown++, consecUp = 0
//            Close[0] == Close[1] -> both counters unchanged (ORIG 1566)
//            Streak = consecUp > 0 ? consecUp : -consecDown
//  Quirks  : On bar 0 ORIG writes 0 and returns (ORIG 1555); preserved. ORIG's
//            OnBarUpdate skips every module while CurrentBar < 50 (ORIG 601), so its
//            counters only start accumulating at bar 50; the same gate is kept here,
//            so daily charts match exactly. On INTRADAY charts ORIG's gate also waits
//            for its hidden daily series (CurrentBars[1] < 1 at ORIG 537), i.e. until
//            the second daily bar; this standalone does not add that series, so on
//            intraday charts the streak can differ from ORIG until the first
//            close-to-close reversal after ORIG starts, then matches.
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
	public class QI_ConsecDays : Indicator
	{
		private int		consecUpDays;
		private int		consecDownDays;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Consecutive close streak: +n after n consecutive higher closes, -n after n consecutive "
											+ "lower closes; an unchanged close leaves both counters as they are. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_ConsecDays";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= -3;
				UpperThreshold				= 3;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Bar, "Streak");
				AddLine(Brushes.DodgerBlue, -3, "Lower Threshold");
				AddLine(Brushes.OrangeRed,   3, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				consecUpDays	= 0;
				consecDownDays	= 0;
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601): the counters only start at bar 50.
			if (CurrentBar < 50)
				return;

			// ORIG 1555-1568: streak update.
			if (CurrentBar < 1) { Values[0][0] = 0; return; }
			if (Close[0] > Close[1])
			{
				consecUpDays++;
				consecDownDays = 0;
			}
			else if (Close[0] < Close[1])
			{
				consecDownDays++;
				consecUpDays = 0;
			}
			// else: unchanged, keep counts

			// ORIG 1343-1344: signed streak value.
			int streak = consecUpDays > 0 ? consecUpDays : -consecDownDays;
			Values[0][0] = streak;

			DrawDisclaimerOnce();
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
			get { return "QI ConsecDays"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(-50, -1)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default -3 (three consecutive lower closes).",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(1, 50)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 3 (three consecutive higher closes).",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Streak
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
