// ============================================================================
//  QI_19_VolumeDelta - Close-direction volume delta, 20-bar cumulative sum and 10-bar SMA
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plots #21 and #22
//            (ORIG lines 1428-1443; volDelta series and volDeltaSma = SMA(volDelta, 10) at
//            357-360; per-bar delta in UpdateVolumeDelta, lines 1623-1634).
//  Provenance: Close-vs-prior-close signed volume is a proxy; true volume delta needs bid/ask (or at
//            least close-vs-open) classification. No authoritative definition for this form.
//  Concept : Close-direction volume delta as an order-flow proxy.
//  Formula : VolDelta[0]  = +Volume[0] if Close[0] > Close[1], -Volume[0] if Close[0] < Close[1],
//                           0 if unchanged; 0 on bar 0.
//            CumDelta20   = sum of VolDelta[0..19] only when CurrentBar > 20, else 0.
//            DeltaSMA10   = SMA(VolDelta, 10)[0] only when CurrentBar >= 10, else 0.
//  Quirks  : The cumulative guard is CurrentBar > 20 (strict), the SMA guard is >= 10; both
//            kept verbatim. ORIG gated its entire OnBarUpdate on CurrentBar >= 50 (ORIG 601),
//            so its volDelta series stayed 0 before bar 50 (affecting the 20-bar sum on bars
//            50-69 and the SMA on bars 50-58); the same gate is kept here. On INTRADAY charts
//            ORIG's gate also waits for its hidden daily series (ORIG 537); this standalone
//            does not, so the first ~20 bars after ORIG starts can differ on intraday charts.
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
	public class QI_19_VolumeDelta : Indicator
	{
		private Series<double>	volDelta;
		private SMA				volDeltaSma;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Volume delta: +Volume on an up close, -Volume on a down close, 0 otherwise; "
											+ "plus the 20-bar cumulative sum (0 until bar 21) and SMA(10) of the delta (0 until bar 10). "
											+ "Educational use only - not financial advice.";
				Name						= "QI_19_VolumeDelta";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Gray,       2), PlotStyle.Bar,  "Vol Delta");
				AddPlot(new Stroke(Brushes.DodgerBlue, 2), PlotStyle.Line, "CumDelta 20");
				AddPlot(new Stroke(Brushes.Goldenrod,  2), PlotStyle.Line, "Delta SMA 10");
				AddLine(Brushes.DimGray, 0, "Zero");
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				volDelta		= new Series<double>(this);
				volDeltaSma		= SMA(volDelta, 10);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601): volDelta stays 0 before bar 50.
			if (CurrentBar < 50)
				return;

			// Mirrors ORIG UpdateVolumeDelta (1623-1634): runs every bar BEFORE the value calc.
			UpdateVolumeDelta();
			Values[0][0] = volDelta[0];

			// ORIG 1429-1435, verbatim.
			double cumDelta = 0;
			if (CurrentBar > 20)
			{
				for (int i = 0; i < 20; i++)
					cumDelta += volDelta[i];
			}
			Values[1][0] = cumDelta;

			// ORIG 1440-1441, verbatim.
			double vdSmaVal = CurrentBar >= 10 ? volDeltaSma[0] : 0;
			Values[2][0] = vdSmaVal;

			DrawDisclaimerOnce();
		}

		// ORIG 1623-1634, verbatim.
		private void UpdateVolumeDelta()
		{
			if (CurrentBar < 1) { volDelta[0] = 0; return; }

			double priceChange = Close[0] - Close[1];
			if (priceChange > 0)
				volDelta[0] = Volume[0];
			else if (priceChange < 0)
				volDelta[0] = -Volume[0];
			else
				volDelta[0] = 0;
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
			get { return "QI 19 VolumeDelta"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> VolDelta
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> CumDelta20
		{
			get { return Values[1]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> DeltaSMA10
		{
			get { return Values[2]; }
		}

		#endregion
	}
}
