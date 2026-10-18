// ============================================================================
//  QI_07_SMA200Trend - SMA(200) overlay with close-to-SMA distance series
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #18
//            (indicator instance ORIG 346, value ORIG 1410-1414).
//  Concept : Long-term trend filter via the 200-period simple moving average.
//  Formula : sma200 = SMA(Close, 200) (plotted on price).
//            Distance = CurrentBar >= 200 ? Close[0] - sma200[0] : 0  (ORIG's
//            DataBox value, exposed as a non-plot series).
//  Quirks  : The 200-bar warm-up guard on Distance is ORIG's own (ORIG 1411)
//            and is preserved; the SMA plot itself is drawn from bar 0 using
//            NinjaTrader's SMA, which averages the available bars until 200.
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
	public class QI_07_SMA200Trend : Indicator
	{
		private SMA				sma200;
		private Series<double>	distanceSeries;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "SMA(Close, 200) on the price panel; the Distance series holds Close - SMA200 "
											+ "once 200 bars are available, else 0. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_07_SMA200Trend";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Line, "SMA 200");
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				sma200			= SMA(Close, 200);
				distanceSeries	= new Series<double>(this);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			Values[0][0] = sma200[0];

			// ORIG 1411-1412: distance from the 200 SMA, 0 until 200 bars exist.
			double sma200Dist = CurrentBar >= 200 ? Close[0] - sma200[0] : 0;
			distanceSeries[0] = sma200Dist;

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
			get { return "QI 07 SMA200Trend"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Sma200
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Distance
		{
			get { return distanceSeries; }
		}

		#endregion
	}
}
