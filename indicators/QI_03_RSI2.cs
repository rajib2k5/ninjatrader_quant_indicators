// ============================================================================
//  QI_03_RSI2 - 2-period Relative Strength Index
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #2
//            (ORIG lines 342, 1272-1275).
//  Concept : Short-term RSI mean reversion, Connors / Alvarez.
//  Formula : RSI(Close, 2, 1) - NinjaTrader's built-in RSI with period 2 and a
//            1-period smoothing, exactly as ORIG constructed it.
//  Quirks  : ORIG does not write any DataBox value until CurrentBar >= 50 (its
//            module-wide warm-up gate at ORIG 537/601); that gate is preserved
//            here, so the plot is empty for the first 50 bars.
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
	public class QI_03_RSI2 : Indicator
	{
		private RSI		rsi2;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "2-period RSI: RSI(Close, 2, 1), 0..100. "
											+ "Reference lines at 25 / 75 are neutral boundaries only. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_03_RSI2";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= 25;
				UpperThreshold				= 75;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Line, "RSI(2)");
				AddLine(Brushes.DodgerBlue, 25, "Lower Threshold");
				AddLine(Brushes.OrangeRed,  75, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				rsi2			= RSI(Close, 2, 1);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601).
			if (CurrentBar < 50)
				return;

			// ORIG 1273
			Values[0][0] = rsi2[0];

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
			get { return "QI 03 RSI2"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default 25.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 75.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> RSI2
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
