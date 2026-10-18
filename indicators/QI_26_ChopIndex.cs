// ============================================================================
//  QI_26_ChopIndex - Choppiness Index (14) with ADX / volume 2-of-3 regime flag
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plots
//            #25 (CHOP) and #26 (is_market_choppy); ORIG 358-359 for the
//            SMA(Volume, 20) / ADX(14) instances, ORIG 1453-1524 for the math.
//  Provenance: CHOP formula matches NinjaTrader's shipped ChoppinessIndex; the 61.8/38.2 lines are a
//            convention (NinjaTrader ships 62.8/38.2); the 2-of-3 'choppy' state is a heuristic
//            with no published definition.
//  Concept : Choppiness Index, Dreiss (1993).
//  Formula : CHOP = 100 * LOG10( SUM(TrueRange, 14) / (HH(14) - LL(14)) ) / LOG10(14)
//            clamped to 0..100; 50 while CurrentBar < 14 or when HH == LL.
//            TrueRange[i] = High[i] - Low[i], extended by |High[i] - Close[i+1]|
//            and |Low[i] - Close[i+1]| only when i < CurrentBar (ORIG 1466).
//            ADX = ADX(14). VolRatio = Volume / SMA(Volume, 20) (1.0 if SMA <= 0).
//            ChoppyFlag: count = [CHOP > 61.8] + [ADX < 20] + [VolRatio < 0.7];
//            count >= 2 -> 1 ("CHOPPY"), count == 1 -> 0.5 ("CAUTION"),
//            else 0 ("TRENDING").
//  Quirks  : The `i < CurrentBar` true-range guard (ORIG 1466) is preserved
//            verbatim even though it is always true once CurrentBar >= 14.
//            The 61.8 / 20 / 0.7 constants inside the flag logic are ORIG's and
//            are NOT tied to the reference-line properties. ORIG's OnBarUpdate
//            additionally skips all modules while CurrentBar < 50 (ORIG 537/601);
//            this standalone uses ORIG's own 14-bar guard only.
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
	public class QI_26_ChopIndex : Indicator
	{
		private ADX				adx14;
		private SMA				volSma20;
		private Series<double>	choppyFlagSeries;
		private Series<double>	adxSeries;
		private Series<double>	volRatioSeries;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Choppiness Index (14): 100 * log10(sum TR / (HH - LL)) / log10(14), 0..100. "
											+ "Above 61.8 = choppy, below 38.2 = trending. A 2-of-3 regime flag combines "
											+ "CHOP > 61.8, ADX(14) < 20 and Volume < 70% of its 20-SMA; the state is "
											+ "written in the top-right corner. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_26_ChopIndex";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= 38.2;
				UpperThreshold				= 61.8;
				ShowStateText				= true;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Line, "CHOP");
				AddLine(Brushes.DodgerBlue, 38.2, "Lower Threshold");
				AddLine(Brushes.OrangeRed,  61.8, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				volSma20			= SMA(Volume, 20);
				adx14				= ADX(14);
				choppyFlagSeries	= new Series<double>(this);
				adxSeries			= new Series<double>(this);
				volRatioSeries		= new Series<double>(this);
				disclaimerDrawn		= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1456-1480: Choppiness Index.
			// CHOP = 100 * LOG10( SUM(ATR(1), n) / (HH(n) - LL(n)) ) / LOG10(n)
			// >61.8 = Choppy, 38.2-61.8 = Neutral, <38.2 = Trending
			double chopVal = 50;
			int chopPeriod = 14;
			if (CurrentBar >= chopPeriod)
			{
				double sumTR = 0;
				double hh = double.MinValue;
				double ll = double.MaxValue;
				for (int i = 0; i < chopPeriod; i++)
				{
					double trueRange = High[i] - Low[i];
					if (i < CurrentBar)
					{
						trueRange = Math.Max(trueRange, Math.Abs(High[i] - Close[i + 1]));
						trueRange = Math.Max(trueRange, Math.Abs(Low[i] - Close[i + 1]));
					}
					sumTR += trueRange;
					if (High[i] > hh) hh = High[i];
					if (Low[i] < ll) ll = Low[i];
				}
				double range = hh - ll;
				if (range > 0)
					chopVal = 100.0 * Math.Log10(sumTR / range) / Math.Log10(chopPeriod);
				chopVal = Math.Max(0, Math.Min(100, chopVal));
			}
			Values[0][0] = chopVal;

			// ORIG 1482-1488: ADX confirmation and volume filter.
			double adxVal = adx14[0];
			string adxClass = adxVal < 20 ? "Weak" : adxVal < 25 ? "Transition" : "Strong";

			// Volume filter: below 70% of 20-SMA = low volume (chop confirmation)
			double volRatioChop = volSma20[0] > 0 ? Volume[0] / volSma20[0] : 1.0;
			bool lowVolume = volRatioChop < 0.7;

			adxSeries[0]		= adxVal;
			volRatioSeries[0]	= volRatioChop;

			// ORIG 1496-1521: composite 2-of-3 detection.
			// CHOP > 61.8 = choppy, ADX < 20 = weak trend, Vol < 70% avg = low activity
			int chopSignals = 0;
			if (chopVal > 61.8) chopSignals++;
			if (adxVal < 20) chopSignals++;
			if (lowVolume) chopSignals++;

			string marketState;
			double chopFlag;
			Brush stateBrush;
			if (chopSignals >= 2)
			{
				marketState = "CHOPPY";
				chopFlag = 1;
				stateBrush = Brushes.OrangeRed;
			}
			else if (chopSignals == 1)
			{
				marketState = "CAUTION";
				chopFlag = 0.5;
				stateBrush = Brushes.Goldenrod;
			}
			else
			{
				marketState = "TRENDING";
				chopFlag = 0;
				stateBrush = Brushes.LimeGreen;
			}

			choppyFlagSeries[0] = chopFlag;

			if (ShowStateText)
			{
				// Same tag every bar so the text box updates in place.
				string stateText = marketState + " " + chopSignals + "/3"
					+ "\nCHOP " + chopVal.ToString("F1")
					+ " | ADX " + adxVal.ToString("F1") + " (" + adxClass + ")"
					+ " | Vol " + (volRatioChop * 100).ToString("F0") + "% avg"
					+ (lowVolume ? " [LOW]" : "");

				Draw.TextFixed(this, "QI_ChopState", stateText,
					TextPosition.TopRight, stateBrush, new SimpleFont("Arial", 11),
					Brushes.Transparent, Brushes.Transparent, 0);
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
			get { return "QI 26 ChopIndex"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0.0, 100.0)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default 38.2 (trending below).",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 100.0)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 61.8 (choppy above).",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show State Text", Description = "Write the CHOPPY / CAUTION / TRENDING state and n/3 count in the top-right corner.",
			Order = 1, GroupName = "Display")]
		public bool ShowStateText { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 2, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Chop
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> ChoppyFlag
		{
			get { return choppyFlagSeries; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Adx
		{
			get { return adxSeries; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> VolRatio
		{
			get { return volRatioSeries; }
		}

		#endregion
	}
}
