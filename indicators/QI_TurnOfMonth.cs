// ============================================================================
//  QI_TurnOfMonth - Turn-of-Month calendar window flag (last 4 + first 3 days)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator, DataBox plot #7
//            (ORIG 370 for the CST zone, ORIG 1332-1340 for the window test).
//  Concept : Turn-of-the-Month seasonality, Hensel & Ziemba.
//  Formula : Bar time is converted from the platform time zone to US Central
//            (TimeZoneInfo "Central Standard Time", exactly as ORIG). With
//            dom = day of month and dim = DateTime.DaysInMonth(year, month):
//                window = dom >= (dim - 3) || dom <= 3
//            Plot = 1 inside the window, 0 otherwise.
//  Quirks  : ORIG's OnBarUpdate returns before any module runs while
//            CurrentBar < 50 (ORIG 537/601); this standalone has no warm-up
//            need, so it plots from bar 0. The window test itself is unchanged.
//            Optional ShadeWindow paints BackBrush on window bars (display only).
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
	public class QI_TurnOfMonth : Indicator
	{
		private TimeZoneInfo	cstZone;
		private Brush			shadeBrush;
		private bool			disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Turn-of-Month window flag: 1 when the US Central calendar day is within the "
											+ "last 4 or first 3 days of the month (dom >= DaysInMonth-3 or dom <= 3), else 0. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_TurnOfMonth";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;		// shades the window bars on the price chart; no sub-panel
				DisplayInDataBox			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;
				ShowTransparentPlotsInDataBox = true;

				ShadeWindow					= true;
				ShowDisclaimer				= false;

				AddPlot(Brushes.Transparent, "Turn-of-Month");	// DataBox only (1 = in window)
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
			// ORIG 1333-1338: convert bar time to US Central, then test the calendar window.
			DateTime cstT = TimeZoneInfo.ConvertTime(Time[0],
				Core.Globals.GeneralOptions.TimeZoneInfo, cstZone);
			int dom = cstT.Day;
			int dim = DateTime.DaysInMonth(cstT.Year, cstT.Month);
			bool tom = dom >= (dim - 3) || dom <= 3;
			Values[0][0] = tom ? 1 : 0;

			if (ShadeWindow && tom)
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
			get { return "QI TurnOfMonth"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Shade Window", Description = "Paint a translucent background on bars inside the turn-of-month window.",
			Order = 1, GroupName = "Display")]
		public bool ShadeWindow { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 2, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> TurnOfMonth
		{
			get { return Values[0]; }
		}

		#endregion
	}
}
