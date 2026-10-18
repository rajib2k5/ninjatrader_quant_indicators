// ============================================================================
//  QI_11_StochFade - Fast Stochastic %K / %D
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #4
//            (ORIG lines 350, 1298-1301).
//  Concept : Fast Stochastic oscillator (Lane); ORIG only plotted %K.
//  Formula : StochasticsFast(3, 14) - NinjaTrader's built-in with periodD = 3 and
//            periodK = 14, exactly as ORIG constructed it. %K = .K, %D = .D.
//  Quirks  : ORIG does not write any DataBox value until CurrentBar >= 50 (its
//            module-wide warm-up gate at ORIG 537/601); that gate is preserved
//            here, so the plots are empty for the first 50 bars. %D is exposed
//            as a second plot for context; ORIG only displayed %K.
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
	public class QI_11_StochFade : Indicator
	{
		private StochasticsFast	stoch;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Fast Stochastic: StochasticsFast(3, 14) %K and %D, 0..100. "
											+ "Reference lines at 30 / 70 are neutral boundaries only. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_11_StochFade";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				LowerThreshold				= 30;
				UpperThreshold				= 70;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.Goldenrod, 2), PlotStyle.Line, "%K");
				AddPlot(new Stroke(Brushes.Gray,      1), PlotStyle.Line, "%D");
				AddLine(Brushes.DodgerBlue, 30, "Lower Threshold");
				AddLine(Brushes.OrangeRed,  70, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = LowerThreshold;
				Lines[1].Value = UpperThreshold;
			}
			else if (State == State.DataLoaded)
			{
				// ORIG 350: periodD = 3, periodK = 14
				stoch			= StochasticsFast(3, 14);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG module-wide warm-up gate (ORIG 537 / 601).
			if (CurrentBar < 50)
				return;

			// ORIG 1299
			Values[0][0] = stoch.K[0];
			Values[1][0] = stoch.D[0];

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
			get { return "QI 11 StochFade"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Lower Threshold", Description = "Reference line only. Original default 30.",
			Order = 1, GroupName = "Parameters")]
		public double LowerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Upper Threshold", Description = "Reference line only. Original default 70.",
			Order = 2, GroupName = "Parameters")]
		public double UpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> K
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> D
		{
			get { return Values[1]; }
		}

		#endregion
	}
}
