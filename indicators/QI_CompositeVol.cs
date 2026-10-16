// ============================================================================
//  QI_CompositeVol - Composite volatility score (RV z-score, price z-score, vol-of-vol)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #6
//            (ORIG lines 1308-1330; dependencies at 347 ATR(14), 416-418 SMA(Close,20)
//            and StdDev(Close,20); rvZ at 1573-1593; atrChangeSeries at 1596).
//  Provenance: Unpublished composite ('v5_zscore'); weights and constants have no authoritative source.
//  Concept : "v5_zscore" composite volatility score.
//  Formula : rvZ   = (ATR14 - mean) / population std of ATR14 over the last
//                    Math.Min(20, CurrentBar) bars, 0 until CurrentBar >= 25 (see QI_RVZScore)
//            priceZ = (Close - SMA(Close,20)) / StdDev(Close,20)
//            atrChange[0] = ATR14[0] - ATR14[1]  (0 when CurrentBar < 2)
//            vov    = population std of the last Math.Min(10, CurrentBar) atrChange values
//                     divided by ATR14[0]  (0 when ATR14[0] <= 0)
//            CompositeVol = 0.40*rvZ + 0.35*(-priceZ) + 0.25*((vov - 0.15) / 0.10)
//            The value is 0 unless CurrentBar >= 30 && StdDev(Close,20)[0] > 0.
//  Quirks  : Constants 0.40 / 0.35 / 0.25 / 0.15 / 0.10 (ORIG 1325-1326) are kept verbatim.
//            rvZ and atrChange are computed internally so this file is standalone.
//            ORIG gated its entire OnBarUpdate on CurrentBar >= 50 (ORIG 601), so its
//            rvZ/atrChange series stayed 0 before bar 50 (affecting the vol-of-vol window
//            on bars 50-58); the same gate is kept here so daily charts match exactly.
//            On INTRADAY charts ORIG's gate also waits for its hidden daily series
//            (CurrentBars[1] < 1 at ORIG 537), i.e. until the second daily bar; this
//            standalone does not add that series, so on intraday charts the value can
//            differ from ORIG for the first ~9 bars after ORIG starts, then converges.
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
	public class QI_CompositeVol : Indicator
	{
		private ATR				atr14;
		private SMA				closeSma20z;
		private StdDev			closeStdDev20;
		private Series<double>	rvZscoreSeries;
		private Series<double>	atrChangeSeries;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Composite volatility score: 0.40*RVZ + 0.35*(-PriceZ) + 0.25*((VoV-0.15)/0.10), "
											+ "where RVZ is the ATR14 z-score (20 bars), PriceZ = (Close-SMA20)/StdDev20 and VoV is the "
											+ "population std of the last 10 ATR14 changes divided by ATR14. 0 until bar 30. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_CompositeVol";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= -1.5;
				UpperThreshold				= 1.5;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.DarkOrange, 2), PlotStyle.Line, "CompositeVol");
				AddLine(Brushes.DodgerBlue, -1.5, "Lower Threshold");
				AddLine(Brushes.OrangeRed,   1.5, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				atr14			= ATR(14);
				closeSma20z		= SMA(Close, 20);
				closeStdDev20	= StdDev(Close, 20);
				rvZscoreSeries	= new Series<double>(this);
				atrChangeSeries	= new Series<double>(this);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601): its series stay 0 before bar 50.
			if (CurrentBar < 50)
				return;

			// Mirrors ORIG UpdateNewAlphas (1573-1596): runs every bar BEFORE the value calc.
			UpdateVolSeries();

			// ORIG 1308-1328, verbatim.
			double compVal = 0;
			if (CurrentBar >= 30 && closeStdDev20[0] > 0)
			{
				double cc1 = rvZscoreSeries[0];
				double cc2 = (Close[0] - closeSma20z[0]) / closeStdDev20[0];
				double ccvovMean = 0;
				int ccvLen = Math.Min(10, CurrentBar);
				for (int i = 0; i < ccvLen; i++) ccvovMean += atrChangeSeries[i];
				ccvovMean /= ccvLen;
				double ccvovSumSq = 0;
				for (int i = 0; i < ccvLen; i++)
				{
					double d = atrChangeSeries[i] - ccvovMean;
					ccvovSumSq += d * d;
				}
				double ccvov = atr14[0] > 0 ? Math.Sqrt(ccvovSumSq / ccvLen) / atr14[0] : 0;
				double cc3z = (ccvov - 0.15) / 0.10;
				compVal = 0.40 * cc1 + 0.35 * (-cc2) + 0.25 * cc3z;
			}
			Values[0][0] = compVal;

			DrawDisclaimerOnce();
		}

		// ORIG UpdateNewAlphas 1555 (early return on bar 0, series left at default 0),
		// 1573-1593 (RV z-score) and 1596 (ATR change).
		private void UpdateVolSeries()
		{
			if (CurrentBar < 1)
			{
				rvZscoreSeries[0]	= 0;
				atrChangeSeries[0]	= 0;
				return;
			}

			// ── Realized Vol Z-Score ──
			if (CurrentBar >= 25)
			{
				double atrMean = 0;
				int lookback = Math.Min(20, CurrentBar);
				for (int i = 0; i < lookback; i++)
					atrMean += atr14[i];
				atrMean /= lookback;
				double atrSumSq = 0;
				for (int i = 0; i < lookback; i++)
				{
					double diff = atr14[i] - atrMean;
					atrSumSq += diff * diff;
				}
				double atrStd = Math.Sqrt(atrSumSq / lookback);
				rvZscoreSeries[0] = atrStd > 0 ? (atr14[0] - atrMean) / atrStd : 0;
			}
			else
			{
				rvZscoreSeries[0] = 0;
			}

			// ── ATR change for vol-of-vol ──
			atrChangeSeries[0] = CurrentBar >= 2 ? atr14[0] - atr14[1] : 0;
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
			get { return "QI CompositeVol"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(-10.0, 10.0)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default -1.5.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(-10.0, 10.0)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 1.5.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> CompositeVol
		{
			get { return Values[0]; }
		}

		// Non-plot intermediate: RV z-score component (0 until bar 25).
		[Browsable(false)]
		[XmlIgnore]
		public Series<double> RVZScore
		{
			get { return rvZscoreSeries; }
		}

		// Non-plot intermediate: ATR14[0] - ATR14[1] (0 when CurrentBar < 2).
		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AtrChange
		{
			get { return atrChangeSeries; }
		}

		#endregion
	}
}
