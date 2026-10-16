// ============================================================================
//  QI_BollingerPctB - Bollinger %B (close position inside the bands, scaled +/-100)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #10
//            (ORIG lines 349, 1353-1360).
//  Concept : Bollinger Bands %B (Bollinger 2001), centred at 0 and scaled so that
//            the upper band = +100 and the lower band = -100.
//  Formula : boll = Bollinger(Close, 2, 20)   (numStdDev = 2, period = 20)
//            bandwidth = Upper - Lower
//            %B = (Close - mid) / (bandwidth * 0.5) * 100, or 0 when bandwidth <= 0.
//  Deviation: ORIG's "mid" variable read boll[0] = Bollinger.Values[0], which is the UPPER
//            band, so ORIG's value was (Close - Upper)/half-width*100 (0 at the upper band,
//            -200 at the lower). This file uses boll.Middle[0]; its value equals ORIG + 100.
//            This is the only deliberate formula change in the repository.
//  Quirks  : (1) ORIG classified bars by band touch with a 0.001 * ATR(14) tolerance
//                (ORIG 1358-1359), not by the %B value; the +/-100 reference lines
//                here mark the bands themselves and that ATR tolerance is dropped.
//            (2) ORIG does not write any DataBox value until CurrentBar >= 50 (its
//                module-wide warm-up gate at ORIG 537/601); preserved here.
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
	public class QI_BollingerPctB : Indicator
	{
		private Bollinger	boll;
		private bool		disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Bollinger(Close, 2, 20) bands drawn on price, plus %B = (Close - middle) / (half bandwidth) * 100 "
											+ "as a hidden DataBox value (+100 = upper band, -100 = lower band, 0 when bandwidth is zero). "
											+ "Educational use only - not financial advice.";
				Name						= "QI_BollingerPctB";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;
				ShowTransparentPlotsInDataBox = true;

				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.DodgerBlue, 1), PlotStyle.Line, "Upper");
				AddPlot(new Stroke(Brushes.Goldenrod,  1), PlotStyle.Line, "Middle");
				AddPlot(new Stroke(Brushes.DodgerBlue, 1), PlotStyle.Line, "Lower");
				AddPlot(Brushes.Transparent, "%B");		// DataBox only (same scale trick as the original)
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				// ORIG 349: numStdDev = 2, period = 20
				boll			= Bollinger(Close, 2, 20);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601).
			if (CurrentBar < 50)
				return;

			// ORIG 1354-1357
			// DEVIATION from ORIG 1354: ORIG read boll[0], which is Bollinger.Values[0] = the UPPER
			// band (see @Bollinger.cs), so its "%B" was 0 at the upper band and -200 at the lower.
			// The middle band is used here so the value is the standard -100..+100 %B.
			double bollMid = boll.Middle[0];
			double bollBandWidth = boll.Upper[0] - boll.Lower[0];
			double bollPct = bollBandWidth > 0 ? (Close[0] - bollMid) / (bollBandWidth * 0.5) * 100.0 : 0;
			Values[0][0] = boll.Upper[0];
			Values[1][0] = bollMid;
			Values[2][0] = boll.Lower[0];
			Values[3][0] = bollPct;

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
			get { return "QI BollingerPctB"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Upper
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Middle
		{
			get { return Values[1]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Lower
		{
			get { return Values[2]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> PctB
		{
			get { return Values[3]; }
		}

		#endregion
	}
}
