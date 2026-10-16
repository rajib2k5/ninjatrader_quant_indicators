// ============================================================================
//  QI_TurnaroundTuesday - Day of week (US Central), 0 = Sunday .. 6 = Saturday
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #11
//            (ORIG 370 for the CST zone, ORIG 1333-1334 for the conversion,
//            ORIG 1362-1366 for the value).
//  Concept : Day-of-the-week effect / "Turnaround Tuesday", French (1980).
//  Formula : Bar time is converted from the platform time zone to US Central
//            (TimeZoneInfo "Central Standard Time", exactly as ORIG), then
//            Plot = (int)cstTime.DayOfWeek  (Sunday = 0 .. Saturday = 6).
//  Quirks  : ORIG's OnBarUpdate skips every module while CurrentBar < 50
//            (ORIG 537/601); this standalone has no warm-up need, so it plots
//            from bar 0. Optional ShadeMonday paints BackBrush on Monday bars
//            (ORIG's highlighted weekday) - display only.
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
	public class QI_TurnaroundTuesday : Indicator
	{
		private TimeZoneInfo	cstZone;
		private Brush			shadeBrush;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Day of week of the bar in US Central time: 0 = Sunday .. 6 = Saturday. "
											+ "Optionally shades Monday bars. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_TurnaroundTuesday";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;		// shades Monday bars on the price chart; no sub-panel
				DisplayInDataBox			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;
				ShowTransparentPlotsInDataBox = true;

				ShadeMonday					= true;
				ShowDisclaimer				= false;

				AddPlot(Brushes.Transparent, "Day of Week");	// DataBox only (0 = Sunday .. 6)
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				cstZone			= TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");

				SolidColorBrush b = new SolidColorBrush(Color.FromArgb(40, 30, 144, 255));
				b.Freeze();
				shadeBrush		= b;

				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			// ORIG 1333-1334: convert bar time to US Central.
			DateTime cstT = TimeZoneInfo.ConvertTime(Time[0],
				Core.Globals.GeneralOptions.TimeZoneInfo, cstZone);

			// ORIG 1363-1364: day of week as integer (Sunday = 0).
			int dow = (int)cstT.DayOfWeek;
			Values[0][0] = dow;

			if (ShadeMonday && cstT.DayOfWeek == DayOfWeek.Monday)
				BackBrush = shadeBrush;

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
			get { return "QI TurnaroundTuesday"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Shade Monday", Description = "Paint a translucent background on Monday (US Central) bars.",
			Order = 1, GroupName = "Display")]
		public bool ShadeMonday { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 2, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> DayOfWeekValue
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
