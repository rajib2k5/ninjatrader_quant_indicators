// ============================================================================
//  QI_23_VWAPDistance - Distance of Close from the session VWAP, in ATR(14) units
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #15
//            (UpdateManualVwap + the VWAP Distance channel).
//  Concept : Mean reversion toward the volume-weighted average price of the
//            current session; distance is normalized by ATR(14).
//  Formula : typical = (High + Low + Close) / 3
//            vwap    = sum(typical * Volume) / sum(Volume) over the session,
//                      falling back to Close while sum(Volume) == 0
//            value   = (Close - vwap) / ATR14 on INTRADAY charts when
//                      ATR14 > 0 and vwap > 0, otherwise 0.
//  Deviation: The original reset its accumulators when Time[0].DayOfYear changed
//            (calendar midnight in the chart's time zone). The official VWAP (CME,
//            NinjaTrader) is per trading session, so this file resets on
//            Bars.IsFirstBarOfSession (the chart's session template) instead. The
//            SessionStart series (1 on the first bar of a session) is exposed so a
//            reference implementation can mirror the reset exactly.
//            The original only ran the VWAP update on intraday charts, inside the
//            BarsInProgress == 0 path, after its CurrentBar < 50 guard: on
//            non-intraday charts the Vwap series stays 0 and the plot is 0, and
//            accumulation starts at bar 50 (the first session is partial). Preserved.
//            The intraday flag is evaluated in State.Configure via
//            Bars.BarsType.IsIntraday exactly as the original did.
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
	public class QI_23_VWAPDistance : Indicator
	{
		private bool	isIntraday;
		private ATR		atr14;

		// ── Manual VWAP ──
		private double	cumTypicalPriceVol;
		private double	cumVol;
		private double	manualVwap;
		private Series<double> sessionStartSeries;

		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Session VWAP drawn on price (intraday charts only), with the distance "
											+ "(Close - VWAP) / ATR(14) as a hidden DataBox value (0 on non-intraday charts). "
											+ "VWAP is accumulated from bar typical prices and resets on the first bar of each trading session. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_23_VWAPDistance";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;
				ShowTransparentPlotsInDataBox = true;

				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Line, "VWAP");
				AddPlot(Brushes.Transparent, "VWAP Dist (ATR)");	// DataBox only
			}
			else if (State == State.Configure)
			{
				// Original gate: the VWAP channel is only live on intraday charts.
				isIntraday = Bars.BarsType.IsIntraday;
			}
			else if (State == State.DataLoaded)
			{
				atr14				= ATR(14);

				cumTypicalPriceVol	= 0;
				cumVol				= 0;
				manualVwap			= 0;
				sessionStartSeries	= new Series<double>(this);

				disclaimerDrawn		= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// Recorded for every bar (before the warm-up gate) so references can replay the reset.
			sessionStartSeries[0] = Bars.IsFirstBarOfSession ? 1 : 0;

			if (CurrentBar < 50)
				return;

			// The original only accumulated VWAP in its intraday path.
			if (isIntraday)
				UpdateManualVwap();

			// Plot the VWAP level on price only when it is live; an unset value is simply not drawn,
			// so a non-intraday chart's price scale is never pulled toward 0.
			if (isIntraday && manualVwap > 0)
				Values[0][0] = manualVwap;

			double vwapDist = (isIntraday && atr14[0] > 0 && manualVwap > 0)
				? (Close[0] - manualVwap) / atr14[0] : 0;
			Values[1][0] = vwapDist;

			DrawDisclaimerOnce();
		}

		// ─────────────────────────────────────────────────────────
		//  Manual VWAP
		// ─────────────────────────────────────────────────────────
		private void UpdateManualVwap()
		{
			// Session reset (official VWAP semantics) instead of the original's DayOfYear reset.
			if (Bars.IsFirstBarOfSession)
			{
				cumTypicalPriceVol   = 0;
				cumVol               = 0;
			}

			double typicalPrice = (High[0] + Low[0] + Close[0]) / 3.0;
			cumTypicalPriceVol += typicalPrice * Volume[0];
			cumVol             += Volume[0];

			manualVwap = (cumVol > 0) ? cumTypicalPriceVol / cumVol : Close[0];
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
			get { return "QI 23 VWAPDistance"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Vwap
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> VwapDistance
		{
			get { return Values[1]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> SessionStart
		{
			get { return sessionStartSeries; }
		}

		#endregion
	}
}
