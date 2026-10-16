// ============================================================================
//  QI_VRPProxy - Volatility risk premium proxy: ATR(5) / ATR(14)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #13
//            (ORIG lines 1373-1377; atr14 = ATR(14) at 347, atr5 = ATR(5) at 414).
//  Provenance: ATR5/ATR14 is a practitioner proxy; the variance risk premium proper is implied minus
//            realized variance. No authoritative source for this proxy.
//  Concept : Short-vs-long realized volatility ratio ("DeltaInvariantVol" concept).
//  Formula : VRP = ATR5[0] / ATR14[0] when CurrentBar >= 20 && ATR14[0] > 0, else 1.0.
//  Quirks  : ORIG additionally gated its entire OnBarUpdate on CurrentBar >= 50 (so its
//            logged value was 1.0 before bar 50); only the per-signal guard is kept here.
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
	public class QI_VRPProxy : Indicator
	{
		private ATR		atr5;
		private ATR		atr14;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Volatility risk premium proxy: ATR(5) / ATR(14). 1.0 until bar 20 or when ATR14 is 0. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_VRPProxy";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= 0.7;
				UpperThreshold				= 1.5;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Teal, 2), PlotStyle.Line, "ATR5/ATR14");
				AddLine(Brushes.DodgerBlue, 0.7, "Lower Threshold");
				AddLine(Brushes.OrangeRed,  1.5, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				atr5			= ATR(5);
				atr14			= ATR(14);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1374-1375, verbatim.
			double vrpVal = CurrentBar >= 20 && atr14[0] > 0 ? atr5[0] / atr14[0] : 1.0;
			Values[0][0] = vrpVal;

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
			get { return "QI VRPProxy"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0.0, 10.0)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default 0.7.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 10.0)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 1.5.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> VRPProxy
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
