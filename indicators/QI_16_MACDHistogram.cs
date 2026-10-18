// ============================================================================
//  QI_16_MACDHistogram - MACD histogram (MACD line minus signal line)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #16
//            (ORIG lines 348, 1399-1402).
//  Concept : MACD histogram (Appel), sign relative to the zero line.
//  Formula : MACD(Close, 12, 26, 9).Diff - NinjaTrader's built-in MACD with
//            fast 12, slow 26, smoothing 9, exactly as ORIG constructed it.
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
	public class QI_16_MACDHistogram : Indicator
	{
		private MACD	macd;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "MACD histogram: MACD(Close, 12, 26, 9).Diff, i.e. MACD line minus signal line. "
											+ "The zero reference line is a neutral boundary only. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_16_MACDHistogram";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				Threshold					= 0;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Bar, "MACD Hist");
				AddLine(Brushes.Gray, 0, "Zero");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = Threshold;
			}
			else if (State == State.DataLoaded)
			{
				// ORIG 348: fast 12, slow 26, smooth 9
				macd			= MACD(Close, 12, 26, 9);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601).
			if (CurrentBar < 50)
				return;

			// ORIG 1400
			Values[0][0] = macd.Diff[0];

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
			get { return "QI 16 MACDHistogram"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Threshold", Description = "Reference line only. Original default 0 (zero line).",
			Order = 1, GroupName = "Parameters")]
		public double Threshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Histogram
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
