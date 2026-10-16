// ============================================================================
//  QI_EMACross - EMA(20) / EMA(50) overlay with spread series
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #17
//            (indicator instances ORIG 344-345, value ORIG 1404-1408).
//  Concept : Fast/slow exponential moving average relationship.
//  Formula : ema20 = EMA(Close, 20), ema50 = EMA(Close, 50) (plotted on price).
//            Spread = ema20[0] - ema50[0]  (ORIG's DataBox value, exposed as a
//            non-plot series).
//  Quirks  : ORIG has no warm-up guard of its own for this value beyond the
//            global CurrentBar < 50 return in OnBarUpdate (ORIG 537/601); this
//            standalone writes from bar 0 using NinjaTrader's own EMA seeding.
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
	public class QI_EMACross : Indicator
	{
		private EMA				ema20;
		private EMA				ema50;
		private Series<double>	spreadSeries;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "EMA(Close, 20) and EMA(Close, 50) on the price panel; the Spread series holds "
											+ "EMA20 - EMA50. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_EMACross";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.DodgerBlue, 2), PlotStyle.Line, "EMA 20");
				AddPlot(new Stroke(Brushes.OrangeRed,  2), PlotStyle.Line, "EMA 50");
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				ema20			= EMA(Close, 20);
				ema50			= EMA(Close, 50);
				spreadSeries	= new Series<double>(this);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			Values[0][0] = ema20[0];
			Values[1][0] = ema50[0];

			// ORIG 1405-1406: EMA spread.
			double emaDiff = ema20[0] - ema50[0];
			spreadSeries[0] = emaDiff;

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
			get { return "QI EMACross"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Ema20
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Ema50
		{
			get { return Values[1]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Spread
		{
			get { return spreadSeries; }
		}

		#endregion
	}
}
