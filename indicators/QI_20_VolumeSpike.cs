// ============================================================================
//  QI_20_VolumeSpike - Bar volume relative to its 20-bar average
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #20
//            (ORIG lines 1422-1426; volSma20 = SMA(Volume, 20) at 358).
//  Provenance: Standard relative-volume ratio; the 1.5x threshold is a convention.
//  Concept : Volume spike confirmation.
//  Formula : Vol/SMA20 = Volume[0] / SMA(Volume, 20)[0] when the SMA > 0, else 1.0.
//  Quirks  : No CurrentBar guard in ORIG (only the SMA > 0 check); kept as-is.
//            ORIG additionally gated its entire OnBarUpdate on CurrentBar >= 50 (so its
//            logged value was 1.0 before bar 50); that global gate is not reproduced here.
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
	public class QI_20_VolumeSpike : Indicator
	{
		private SMA		volSma20;
		private bool	disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Volume spike: Volume / SMA(Volume, 20). 1.0 when the SMA is 0. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_20_VolumeSpike";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= false;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= false;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				Threshold					= 1.5;
				ShowDisclaimer				= false;

				AddPlot(new Stroke(Brushes.SeaGreen, 2), PlotStyle.Line, "Vol / SMA20");
				AddLine(Brushes.OrangeRed, 1.5, "Upper Threshold");
			}
			else if (State == State.Configure)
			{
				Lines[0].Value = Threshold;
			}
			else if (State == State.DataLoaded)
			{
				volSma20		= SMA(Volume, 20);
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1423-1424, verbatim.
			double volRatio = volSma20[0] > 0 ? Volume[0] / volSma20[0] : 1.0;
			Values[0][0] = volRatio;

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
			get { return "QI 20 VolumeSpike"; }
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
		public Series<double> VolumeSpike
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
