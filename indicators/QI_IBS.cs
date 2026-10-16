// ============================================================================
//  QI_IBS - Internal Bar Strength (where the close sits in the daily range)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #1.
//  Provenance: IBS = (C-L)/(H-L) per the practitioner literature (Pagonidis 2013); the primary post was
//            unreachable during the audit, so the definition is cited as secondary.
//  Concept : Internal Bar Strength, Pagonidis (2013).
//  Formula : IBS = (Close - Low) / (High - Low) of the DAILY bar, 0.5 when range = 0.
//            On intraday charts a 1-day data series is added and IBS is read from
//            the forming daily bar, so the value always reflects the full session.
//  Quirk   : like the original, nothing is plotted until bar 50 (its global warm-up).
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
	public class QI_IBS : Indicator
	{
		private double	dailyIBS;
		private bool	useDailySeries;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Internal Bar Strength: IBS = (Close - Low) / (High - Low) of the DAILY bar, 0..1. "
											+ "On intraday charts a 1-day series is added so IBS reflects the full session range. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_IBS";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= 0.20;
				UpperThreshold				= 0.80;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Line, "IBS");
				AddLine(Brushes.DodgerBlue, 0.20, "Lower Threshold");
				AddLine(Brushes.OrangeRed,  0.80, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				// Intraday chart -> add a Daily series so IBS is measured on the full session bar.
				useDailySeries = Bars.BarsType.IsIntraday;
				if (useDailySeries)
					AddDataSeries(Data.BarsPeriodType.Day, 1);

				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				dailyIBS		= 0.5;
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			if (useDailySeries)
			{
				// Same warm-up gate as the original (it returned before any work until bar 50).
				if (CurrentBars[0] < 50 || CurrentBars[1] < 1)
					return;

				// Daily series closed a bar: recompute from the completed daily bar.
				if (BarsInProgress == 1)
				{
					double range = High[0] - Low[0];
					dailyIBS = (range > 0) ? (Close[0] - Low[0]) / range : 0.5;
					return;
				}

				if (BarsInProgress != 0)
					return;

				// Primary (intraday) bar: keep IBS current from the forming daily bar.
				double liveRange = Highs[1][0] - Lows[1][0];
				if (liveRange > 0)
					dailyIBS = (Closes[1][0] - Lows[1][0]) / liveRange;

				Values[0][0] = dailyIBS;
			}
			else
			{
				if (CurrentBar < 50)
					return;

				double range = High[0] - Low[0];
				Values[0][0] = (range > 0) ? (Close[0] - Low[0]) / range : 0.5;
			}

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
			get { return "QI IBS"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0.01, 0.99)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default 0.20.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0.01, 0.99)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 0.80.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> IBS
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
