// ============================================================================
//  QI_KeyLevels - Structural price levels: Prev Day RTH H/L, Monthly H/L,
//                 30-min ORB H/L, Asian session H/L (overlay, no plots)
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
//  Lineage : split out of the "IBSFade" multi-strategy indicator (UpdateKeyLevels,
//            UpdatePrevDayHighLow, UpdateMonthlyHighLow, UpdateOrb,
//            UpdateAsianSession, the IsIn*Window helpers and DrawKeyLevelLines).
//  Provenance: RTH 08:30-16:00 CT equals NinjaTrader's 'CME US Index Futures RTH' session template, not a
//            CME definition (CME publishes Globex 17:00-16:00 CT only); the 30-minute opening range
//            and the 17:00-02:00 CT 'Asian session' are conventions without an official source.
//  Concept : Previous business day RTH high/low (8:30-16:00 CST), current calendar
//            month high/low, 30-minute opening range (8:30-9:00 CST; Crabel-style
//            opening range), and Asian session high/low (17:00-02:00 CST).
//  Time    : Bar time is converted from Core.Globals.GeneralOptions.TimeZoneInfo
//            to "Central Standard Time" (Windows id) for every window test.
//  Quirks  : Weekend bars (Saturday/Sunday CST) are skipped so Friday's values
//            persist. The ORB lines show the CURRENT day's range (live during
//            8:30-9:00, frozen after); prevOrbHigh/Low are tracked but never drawn,
//            exactly as in the original. Lines are only redrawn when a level moves
//            by more than one tick (0.25 when TickSize is 0); labels are redrawn
//            every bar so they track the rightmost bar. The original started
//            updating levels only from bar 50 (CurrentBar < 50 returns); preserved.
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
	public class QI_KeyLevels : Indicator
	{
		// ── Key Levels: Timezone ──
		private TimeZoneInfo cstZone;

		// ── Key Levels: Previous Day High/Low (RTH 8:30-16:00 CST) ──
		private double		prevDayHigh;
		private double		prevDayLow;
		private DateTime	prevDayDate;
		private double		todayRthHigh;
		private double		todayRthLow;
		private DateTime	todayRthDate;
		private bool		todayRthStarted;

		// ── Key Levels: Monthly High/Low ──
		private double		klMonthlyHigh;
		private double		klMonthlyLow;
		private int			klCurrentMonth;

		// ── Key Levels: ORB (8:30-9:00 CST, 30-min Opening Range Breakout) ──
		private double		orbHigh;
		private double		orbLow;
		private bool		orbComplete;
		private DateTime	orbDate;
		private double		prevOrbHigh;
		private double		prevOrbLow;

		// ── Key Levels: redraw suppression ──
		private double		lastPrevDayHighLine;
		private double		lastPrevDayLowLine;
		private double		lastKlMonthlyHighLine;
		private double		lastKlMonthlyLowLine;
		private double		lastOrbHighLine;
		private double		lastOrbLowLine;

		// ── Asian Session tracking ──
		private double		asianHigh;
		private double		asianLow;
		private bool		asianComplete;
		private DateTime	asianDate;
		private double		lastAsianHighLine;
		private double		lastAsianLowLine;

		private bool		disclaimerDrawn;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Key Levels: previous business day RTH (8:30-16:00 CST) high/low, current month high/low, "
											+ "30-min opening range (8:30-9:00 CST) high/low and Asian session (17:00-02:00 CST) high/low, "
											+ "drawn as horizontal lines with labels. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_KeyLevels";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				// Key Levels toggles
				ShowPrevDayLevels			= true;
				ShowMonthlyLevels			= true;
				ShowOrbLevels				= true;
				ShowAsianSessionLevels		= true;
				ShowDisclaimer				= false;

				// Colors
				PrevDayHighBrush			= Brushes.White;
				PrevDayLowBrush				= Brushes.Coral;
				MonthlyHighBrush			= Brushes.DodgerBlue;
				MonthlyLowBrush				= Brushes.Violet;
				OrbHighBrush				= Brushes.Turquoise;
				OrbLowBrush					= Brushes.Plum;
				AsianHighBrush				= Brushes.MediumSpringGreen;
				AsianLowBrush				= Brushes.Salmon;
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				// ── Key Levels initialization ──
				cstZone				= TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");

				prevDayHigh			= double.MinValue;
				prevDayLow			= double.MaxValue;
				prevDayDate			= DateTime.MinValue;
				todayRthHigh		= double.MinValue;
				todayRthLow			= double.MaxValue;
				todayRthDate		= DateTime.MinValue;
				todayRthStarted		= false;

				klMonthlyHigh		= double.MinValue;
				klMonthlyLow		= double.MaxValue;
				klCurrentMonth		= 0;

				orbHigh				= double.MinValue;
				orbLow				= double.MaxValue;
				orbComplete			= false;
				orbDate				= DateTime.MinValue;
				prevOrbHigh			= double.MinValue;
				prevOrbLow			= double.MaxValue;

				lastPrevDayHighLine		= double.NaN;
				lastPrevDayLowLine		= double.NaN;
				lastKlMonthlyHighLine	= double.NaN;
				lastKlMonthlyLowLine	= double.NaN;
				lastOrbHighLine			= double.NaN;
				lastOrbLowLine			= double.NaN;

				asianHigh				= double.MinValue;
				asianLow				= double.MaxValue;
				asianComplete			= false;
				asianDate				= DateTime.MinValue;
				lastAsianHighLine		= double.NaN;
				lastAsianLowLine		= double.NaN;

				disclaimerDrawn			= false;
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 50)
				return;

			// ── Key Levels: update prev day / monthly / ORB / Asian lines ──
			UpdateKeyLevels();

			DrawDisclaimerOnce();
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels dispatcher
		// ─────────────────────────────────────────────────────────
		private void UpdateKeyLevels()
		{
			DateTime cstTime = TimeZoneInfo.ConvertTime(Time[0],
				Core.Globals.GeneralOptions.TimeZoneInfo, cstZone);

			if (ShowPrevDayLevels)
				UpdatePrevDayHighLow(cstTime);

			if (ShowMonthlyLevels)
				UpdateMonthlyHighLow(cstTime);

			if (ShowOrbLevels)
				UpdateOrb(cstTime);

			if (ShowAsianSessionLevels)
				UpdateAsianSession(cstTime);

			DrawKeyLevelLines();
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels: Previous Business Day RTH High/Low
		//  RTH = 8:30 AM – 4:00 PM CST
		//  On weekends, Friday's values persist
		// ─────────────────────────────────────────────────────────
		private void UpdatePrevDayHighLow(DateTime cstTime)
		{
			// Skip weekends — keep Friday's values
			if (cstTime.DayOfWeek == DayOfWeek.Saturday
				|| cstTime.DayOfWeek == DayOfWeek.Sunday)
				return;

			// Detect new trading day (CST date changed)
			if (cstTime.Date != todayRthDate)
			{
				// If we had a valid RTH session, roll it into "previous"
				if (todayRthStarted
					&& todayRthHigh > double.MinValue
					&& todayRthLow < double.MaxValue)
				{
					prevDayHigh = todayRthHigh;
					prevDayLow  = todayRthLow;
					prevDayDate = todayRthDate;
				}

				// Reset today's tracking
				todayRthHigh    = double.MinValue;
				todayRthLow     = double.MaxValue;
				todayRthDate    = cstTime.Date;
				todayRthStarted = false;
			}

			// Check if current bar falls within RTH: 8:30 AM – 4:00 PM CST
			if (IsInRthWindow(cstTime))
			{
				todayRthStarted = true;
				if (High[0] > todayRthHigh) todayRthHigh = High[0];
				if (Low[0]  < todayRthLow)  todayRthLow  = Low[0];
			}
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels: Current Calendar Month High/Low
		// ─────────────────────────────────────────────────────────
		private void UpdateMonthlyHighLow(DateTime cstTime)
		{
			int barMonth = cstTime.Month;

			// Detect month change — reset
			if (barMonth != klCurrentMonth)
			{
				klMonthlyHigh  = double.MinValue;
				klMonthlyLow   = double.MaxValue;
				klCurrentMonth = barMonth;
			}

			// Always update with current bar
			if (High[0] > klMonthlyHigh) klMonthlyHigh = High[0];
			if (Low[0]  < klMonthlyLow)  klMonthlyLow  = Low[0];
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels: 30-Min ORB (8:30 – 9:00 AM CST)
		//
		//  Research basis: 30-min ORB recommended for index futures
		//  - Academic study (2019): shorter probing times optimal for US markets
		//  - Toby Crabel: opening range defines daily bias
		//  - Practitioner consensus: captures institutional order flow
		//
		//  On weekends, Friday's ORB values persist
		//  During live trading, lines update in real-time during 8:30-9:00
		// ─────────────────────────────────────────────────────────
		private void UpdateOrb(DateTime cstTime)
		{
			// Skip weekends — keep Friday's ORB values
			if (cstTime.DayOfWeek == DayOfWeek.Saturday
				|| cstTime.DayOfWeek == DayOfWeek.Sunday)
				return;

			// Detect new trading day
			if (cstTime.Date != orbDate)
			{
				// If previous day had a completed ORB, archive it
				if (orbComplete
					&& orbHigh > double.MinValue
					&& orbLow < double.MaxValue)
				{
					prevOrbHigh = orbHigh;
					prevOrbLow  = orbLow;
				}

				// Reset for new day
				orbHigh     = double.MinValue;
				orbLow      = double.MaxValue;
				orbComplete = false;
				orbDate     = cstTime.Date;
			}

			// ORB window: 8:30 AM – 9:00 AM CST
			if (IsInOrbWindow(cstTime) && !orbComplete)
			{
				if (High[0] > orbHigh) orbHigh = High[0];
				if (Low[0]  < orbLow)  orbLow  = Low[0];
			}

			// Mark ORB complete once past 9:00 AM CST on the ORB date
			if (!orbComplete && cstTime.Date == orbDate)
			{
				TimeSpan t = cstTime.TimeOfDay;
				if (t >= new TimeSpan(9, 0, 0) && orbHigh > double.MinValue)
				{
					orbComplete = true;
				}
			}
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels: Time window helpers
		// ─────────────────────────────────────────────────────────
		private bool IsInRthWindow(DateTime cstTime)
		{
			// RTH: 8:30 AM CST (inclusive) to 4:00 PM CST (exclusive)
			TimeSpan t = cstTime.TimeOfDay;
			return t >= new TimeSpan(8, 30, 0) && t < new TimeSpan(16, 0, 0);
		}

		private bool IsInOrbWindow(DateTime cstTime)
		{
			// ORB: 8:30 AM CST (inclusive) to 9:00 AM CST (exclusive)
			TimeSpan t = cstTime.TimeOfDay;
			return t >= new TimeSpan(8, 30, 0) && t < new TimeSpan(9, 0, 0);
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels: Asian Session High/Low
		//  Asian Session: 5:00 PM – 2:00 AM CST (Globex open through Tokyo close)
		//  Resets each trading day at 5:00 PM CST
		// ─────────────────────────────────────────────────────────
		private void UpdateAsianSession(DateTime cstTime)
		{
			if (cstTime.DayOfWeek == DayOfWeek.Saturday
				|| cstTime.DayOfWeek == DayOfWeek.Sunday)
				return;

			// Asian session spans midnight: 5:00 PM to 2:00 AM CST
			// Use the "trading date" concept: bars from 5:00 PM onward belong to the NEXT calendar date
			DateTime tradingDate = cstTime.TimeOfDay >= new TimeSpan(17, 0, 0)
				? cstTime.Date.AddDays(1)
				: cstTime.Date;

			// Detect new trading day → freeze previous session's levels
			if (tradingDate != asianDate)
			{
				asianHigh     = double.MinValue;
				asianLow      = double.MaxValue;
				asianComplete = false;
				asianDate     = tradingDate;
			}

			// Track high/low during the Asian window
			if (IsInAsianWindow(cstTime) && !asianComplete)
			{
				if (High[0] > asianHigh) asianHigh = High[0];
				if (Low[0]  < asianLow)  asianLow  = Low[0];
			}

			// Mark complete once past 2:00 AM CST
			if (!asianComplete && asianDate == tradingDate)
			{
				TimeSpan t = cstTime.TimeOfDay;
				if (t >= new TimeSpan(2, 0, 0) && t < new TimeSpan(17, 0, 0)
					&& asianHigh > double.MinValue)
				{
					asianComplete = true;
				}
			}
		}

		private bool IsInAsianWindow(DateTime cstTime)
		{
			// Asian Session: 5:00 PM CST to 2:00 AM CST (spans midnight)
			TimeSpan t = cstTime.TimeOfDay;
			return t >= new TimeSpan(17, 0, 0) || t < new TimeSpan(2, 0, 0);
		}

		// ─────────────────────────────────────────────────────────
		//  Key Levels: Draw all horizontal lines + labels
		//
		//  Previous Day High/Low → DashDotDot
		//  Monthly High/Low      → DashDot
		//  ORB High/Low          → Dot
		//  Asian High/Low        → DashDotDot
		// ─────────────────────────────────────────────────────────
		private void DrawKeyLevelLines()
		{
			double minMove = TickSize > 0 ? TickSize : 0.25;
			SimpleFont labelFont = new SimpleFont("Arial", 9);

			// ── Previous Day High/Low ──
			if (ShowPrevDayLevels
				&& prevDayHigh > double.MinValue
				&& prevDayLow < double.MaxValue)
			{
				bool needRedraw = double.IsNaN(lastPrevDayHighLine)
					|| Math.Abs(prevDayHigh - lastPrevDayHighLine) > minMove
					|| Math.Abs(prevDayLow - lastPrevDayLowLine) > minMove;

				if (needRedraw)
				{
					lastPrevDayHighLine = prevDayHigh;
					lastPrevDayLowLine  = prevDayLow;

					Draw.HorizontalLine(this, "KL_PrevDayHigh", prevDayHigh,
						PrevDayHighBrush, DashStyleHelper.DashDotDot, 2);
					Draw.HorizontalLine(this, "KL_PrevDayLow", prevDayLow,
						PrevDayLowBrush, DashStyleHelper.DashDotDot, 2);
				}

				// Labels redrawn every bar so they track the rightmost bar
				Draw.Text(this, "KL_PrevDayHighLbl", false,
					"Prev Day High - $" + prevDayHigh.ToString("F2"),
					0, prevDayHigh, 5,
					PrevDayHighBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);

				Draw.Text(this, "KL_PrevDayLowLbl", false,
					"Prev Day Low - $" + prevDayLow.ToString("F2"),
					0, prevDayLow, -5,
					PrevDayLowBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);
			}

			// ── Monthly High/Low ──
			if (ShowMonthlyLevels
				&& klMonthlyHigh > double.MinValue
				&& klMonthlyLow < double.MaxValue)
			{
				bool needRedraw = double.IsNaN(lastKlMonthlyHighLine)
					|| Math.Abs(klMonthlyHigh - lastKlMonthlyHighLine) > minMove
					|| Math.Abs(klMonthlyLow - lastKlMonthlyLowLine) > minMove;

				if (needRedraw)
				{
					lastKlMonthlyHighLine = klMonthlyHigh;
					lastKlMonthlyLowLine  = klMonthlyLow;

					Draw.HorizontalLine(this, "KL_MonthlyHigh", klMonthlyHigh,
						MonthlyHighBrush, DashStyleHelper.DashDot, 2);
					Draw.HorizontalLine(this, "KL_MonthlyLow", klMonthlyLow,
						MonthlyLowBrush, DashStyleHelper.DashDot, 2);
				}

				// Labels redrawn every bar so they track the rightmost bar
				Draw.Text(this, "KL_MonthlyHighLbl", false,
					"Monthly High - $" + klMonthlyHigh.ToString("F2"),
					0, klMonthlyHigh, 5,
					MonthlyHighBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);

				Draw.Text(this, "KL_MonthlyLowLbl", false,
					"Monthly Low - $" + klMonthlyLow.ToString("F2"),
					0, klMonthlyLow, -5,
					MonthlyLowBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);
			}

			// ── ORB High/Low ──
			// Show current day's ORB (updates live during 8:30-9:00, frozen after)
			if (ShowOrbLevels
				&& orbHigh > double.MinValue
				&& orbLow < double.MaxValue)
			{
				bool needRedraw = double.IsNaN(lastOrbHighLine)
					|| Math.Abs(orbHigh - lastOrbHighLine) > minMove
					|| Math.Abs(orbLow - lastOrbLowLine) > minMove;

				if (needRedraw)
				{
					lastOrbHighLine = orbHigh;
					lastOrbLowLine  = orbLow;

					Draw.HorizontalLine(this, "KL_OrbHigh", orbHigh,
						OrbHighBrush, DashStyleHelper.Dot, 2);
					Draw.HorizontalLine(this, "KL_OrbLow", orbLow,
						OrbLowBrush, DashStyleHelper.Dot, 2);
				}

				// Labels redrawn every bar so they track the rightmost bar
				Draw.Text(this, "KL_OrbHighLbl", false,
					"ORB High - $" + orbHigh.ToString("F2"),
					0, orbHigh, 5,
					OrbHighBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);

				Draw.Text(this, "KL_OrbLowLbl", false,
					"ORB Low - $" + orbLow.ToString("F2"),
					0, orbLow, -5,
					OrbLowBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);
			}

			// ── Asian Session High/Low ──
			if (ShowAsianSessionLevels
				&& asianHigh > double.MinValue
				&& asianLow < double.MaxValue)
			{
				bool needRedraw = double.IsNaN(lastAsianHighLine)
					|| Math.Abs(asianHigh - lastAsianHighLine) > minMove
					|| Math.Abs(asianLow - lastAsianLowLine) > minMove;

				if (needRedraw)
				{
					lastAsianHighLine = asianHigh;
					lastAsianLowLine  = asianLow;

					Draw.HorizontalLine(this, "KL_AsianHigh", asianHigh,
						AsianHighBrush, DashStyleHelper.DashDotDot, 2);
					Draw.HorizontalLine(this, "KL_AsianLow", asianLow,
						AsianLowBrush, DashStyleHelper.DashDotDot, 2);
				}

				// Labels redrawn every bar so they track the rightmost bar
				Draw.Text(this, "KL_AsianHighLbl", false,
					"Asian High - $" + asianHigh.ToString("F2"),
					0, asianHigh, 5,
					AsianHighBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);

				Draw.Text(this, "KL_AsianLowLbl", false,
					"Asian Low - $" + asianLow.ToString("F2"),
					0, asianLow, -5,
					AsianLowBrush, labelFont, TextAlignment.Right,
					Brushes.Transparent, Brushes.Transparent, 0);
			}
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
			get { return "QI KeyLevels"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "Show Previous Day Levels",
			Description = "Draw previous business day RTH (8:30-16:00 CST) high/low horizontal lines.",
			Order = 1, GroupName = "Key Levels")]
		public bool ShowPrevDayLevels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Monthly Levels",
			Description = "Draw current calendar month high/low horizontal lines.",
			Order = 2, GroupName = "Key Levels")]
		public bool ShowMonthlyLevels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show ORB Levels",
			Description = "Draw 30-min Opening Range Breakout (8:30-9:00 CST) high/low horizontal lines.",
			Order = 3, GroupName = "Key Levels")]
		public bool ShowOrbLevels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Asian Session Levels",
			Description = "Draw Asian session (5:00 PM - 2:00 AM CST) high/low horizontal lines.",
			Order = 4, GroupName = "Key Levels")]
		public bool ShowAsianSessionLevels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 1, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[XmlIgnore]
		[Display(Name = "Prev Day High Color", Description = "Previous day RTH high line. Default White.",
			Order = 1, GroupName = "Colors")]
		public Brush PrevDayHighBrush { get; set; }
		[Browsable(false)]
		public string PrevDayHighBrushSerialize
		{ get { return Serialize.BrushToString(PrevDayHighBrush); } set { PrevDayHighBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Prev Day Low Color", Description = "Previous day RTH low line. Default Coral.",
			Order = 2, GroupName = "Colors")]
		public Brush PrevDayLowBrush { get; set; }
		[Browsable(false)]
		public string PrevDayLowBrushSerialize
		{ get { return Serialize.BrushToString(PrevDayLowBrush); } set { PrevDayLowBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Monthly High Color", Description = "Current month high line. Default DodgerBlue.",
			Order = 3, GroupName = "Colors")]
		public Brush MonthlyHighBrush { get; set; }
		[Browsable(false)]
		public string MonthlyHighBrushSerialize
		{ get { return Serialize.BrushToString(MonthlyHighBrush); } set { MonthlyHighBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Monthly Low Color", Description = "Current month low line. Default Violet.",
			Order = 4, GroupName = "Colors")]
		public Brush MonthlyLowBrush { get; set; }
		[Browsable(false)]
		public string MonthlyLowBrushSerialize
		{ get { return Serialize.BrushToString(MonthlyLowBrush); } set { MonthlyLowBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "ORB High Color", Description = "Opening range high line. Default Turquoise.",
			Order = 5, GroupName = "Colors")]
		public Brush OrbHighBrush { get; set; }
		[Browsable(false)]
		public string OrbHighBrushSerialize
		{ get { return Serialize.BrushToString(OrbHighBrush); } set { OrbHighBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "ORB Low Color", Description = "Opening range low line. Default Plum.",
			Order = 6, GroupName = "Colors")]
		public Brush OrbLowBrush { get; set; }
		[Browsable(false)]
		public string OrbLowBrushSerialize
		{ get { return Serialize.BrushToString(OrbLowBrush); } set { OrbLowBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Asian High Color", Description = "Asian session high line. Default MediumSpringGreen.",
			Order = 7, GroupName = "Colors")]
		public Brush AsianHighBrush { get; set; }
		[Browsable(false)]
		public string AsianHighBrushSerialize
		{ get { return Serialize.BrushToString(AsianHighBrush); } set { AsianHighBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Asian Low Color", Description = "Asian session low line. Default Salmon.",
			Order = 8, GroupName = "Colors")]
		public Brush AsianLowBrush { get; set; }
		[Browsable(false)]
		public string AsianLowBrushSerialize
		{ get { return Serialize.BrushToString(AsianLowBrush); } set { AsianLowBrush = Serialize.StringToBrush(value); } }

		#endregion
	}
}
