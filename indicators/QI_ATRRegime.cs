// ============================================================================
//  QI_ATRRegime - Volatility regime: ATR(14) relative to its 50-bar average
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #19
//            (ORIG lines 1416-1420; atr14 = ATR(14) at 347, atrSma50 = SMA(atr14, 50) at 409).
//  Provenance: Practitioner heuristic (ATR vs its 50-bar average); no authoritative source.
//  Concept : ATR regime filter (current realized vol vs. its medium-term average).
//  Formula : ATRRegime = ATR14[0] / SMA(ATR14, 50)[0] when CurrentBar >= 50 && the SMA > 0,
//            else 1.0.
//  Quirks  : The SMA is built directly on the ATR indicator instance, as in ORIG.
//            ORIG additionally gated its entire OnBarUpdate on CurrentBar >= 50, which
//            coincides with this module's own guard, so values match from bar 50 on.
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
	public class QI_ATRRegime : Indicator
	{
		private ATR		atr14;
		private SMA		atrSma50;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "ATR regime: ATR(14) / SMA(ATR(14), 50). 1.0 until bar 50 or when the SMA is 0. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_ATRRegime";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				Threshold					= 1.5;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Crimson, 2), PlotStyle.Line, "ATR14 / SMA50(ATR14)");
				AddLine(Brushes.OrangeRed, 1.5, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = Threshold;
			}
			else if (State == State.DataLoaded)
			{
				atr14			= ATR(14);
				atrSma50		= SMA(atr14, 50);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1417-1418, verbatim.
			double atrReg = CurrentBar >= 50 && atrSma50[0] > 0 ? atr14[0] / atrSma50[0] : 1.0;
			Values[0][0] = atrReg;

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
			get { return "QI ATRRegime"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0.0, 10.0)]
		[Display(Name = "Threshold", Description = "Reference line only. Original default 1.5.",
			Order = 1, GroupName = "Parameters")]
		public double Threshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> ATRRegime
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
