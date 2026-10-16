// ============================================================================
//  QI_OvernightGap - Open-to-prior-close gap in percent
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #9
//            (gap calc ORIG 1571, value ORIG 1348-1351).
//  Concept : Overnight gap, MDPI (2025).
//  Formula : Gap % = (Open[0] - Close[1]) / Close[1] * 100, and 0 on bar 0.
//  Quirks  : ORIG has no divide-by-zero guard on Close[1]; preserved as-is.
//            ORIG's OnBarUpdate skips every module while CurrentBar < 50
//            (ORIG 537/601); this standalone has no warm-up need, so it plots
//            from bar 1 with the identical formula.
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
	public class QI_OvernightGap : Indicator
	{
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Overnight gap: (Open[0] - Close[1]) / Close[1] * 100, in percent; 0 on the first bar. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_OvernightGap";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= -0.3;
				UpperThreshold				= 0.3;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Bar, "Gap %");
				AddLine(Brushes.DodgerBlue, -0.3, "Lower Threshold");
				AddLine(Brushes.OrangeRed,   0.3, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1571: overnight gap in percent, 0 on bar 0.
			double overnightGapPct = CurrentBar >= 1 ? (Open[0] - Close[1]) / Close[1] * 100.0 : 0;
			Values[0][0] = overnightGapPct;

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
			get { return "QI OvernightGap"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(-100.0, 0.0)]
		[Display(Name = "Lower Threshold", Description = "Reference line only (percent). Original default -0.3.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 100.0)]
		[Display(Name = "Upper Threshold", Description = "Reference line only (percent). Original default 0.3.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> GapPct
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
