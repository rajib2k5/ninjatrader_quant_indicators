// ============================================================================
//  QI_RVZScore - Realized-volatility z-score of ATR(14) over a 20-bar window
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #5
//            (ORIG UpdateNewAlphas lines 1573-1593; atr14 = ATR(14) at line 347).
//  Concept : Realized-volatility spike z-score ("DthetaSpike" concept).
//  Formula : lookback = Math.Min(20, CurrentBar)
//            mean     = average of ATR14[0..lookback-1]
//            std      = POPULATION std of the same window (sum of squares / lookback)
//            z        = (ATR14[0] - mean) / std, or 0 when std == 0
//            The value is 0 until CurrentBar >= 25.
//  Quirks  : lookback = Math.Min(20, CurrentBar) is kept verbatim even though the
//            CurrentBar >= 25 guard makes it always 20. ORIG additionally gated its
//            entire OnBarUpdate on CurrentBar >= 50 (so its logged value was 0 before
//            bar 50); only the per-signal guard is kept here, as in the template.
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
	public class QI_RVZScore : Indicator
	{
		private ATR		atr14;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Realized-volatility z-score: (ATR14 - mean) / population std of ATR14 over the "
											+ "last 20 bars. 0 until bar 25 and 0 when the std is zero. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_RVZScore";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= -1.5;
				UpperThreshold				= 2.0;
				ShowDisclaimer				= true;

				AddPlot(new Stroke(Brushes.MediumPurple, 2), PlotStyle.Line, "RV Z-Score");
				AddLine(Brushes.DodgerBlue, -1.5, "Lower Threshold");
				AddLine(Brushes.OrangeRed,   2.0, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				atr14			= ATR(14);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1573-1593, verbatim.
			double rvZ = 0;
			if (CurrentBar >= 25)
			{
				double atrMean = 0;
				int lookback = Math.Min(20, CurrentBar);
				for (int i = 0; i < lookback; i++)
					atrMean += atr14[i];
				atrMean /= lookback;
				double atrSumSq = 0;
				for (int i = 0; i < lookback; i++)
				{
					double diff = atr14[i] - atrMean;
					atrSumSq += diff * diff;
				}
				double atrStd = Math.Sqrt(atrSumSq / lookback);
				rvZ = atrStd > 0 ? (atr14[0] - atrMean) / atrStd : 0;
			}
			else
			{
				rvZ = 0;
			}

			Values[0][0] = rvZ;

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
			get { return "QI RVZScore"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(-10.0, 10.0)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default -1.5.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(-10.0, 10.0)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 2.0.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> RVZScore
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
