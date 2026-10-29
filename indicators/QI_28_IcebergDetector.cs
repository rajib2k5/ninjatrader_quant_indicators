// ============================================================================
//  QI_28_IcebergDetector - Probable iceberg (hidden-size) orders at the best bid/ask
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
//  Spec    : validation/iceberg/spec.md (FROZEN 2026-10-28), sections 0-7. The
//            detection rules live in IcebergEngine (bottom of this file), which is
//            plain C# with no NinjaTrader types so a console harness can drive it
//            and diff its records against the independent Python reference.
//  Concept : A resting order that keeps trading at one best-bid/ask price while
//            its displayed size is refilled after each absorbed trade has more size
//            than it shows. Traded volume >= HiddenRatio x the largest displayed
//            size, with >= MinRefills refills and >= MinVolume traded, flags the
//            level. Depth is market-by-price, so every flag is a PROBABLE iceberg.
//  Data    : needs best bid/ask WITH displayed sizes, which NinjaTrader supplies
//            live and in Market Replay (Playback) only; historical Tick Replay has
//            trades with bid/ask prices but no sizes (research-report.md, R8).
//            Detection therefore runs only in State.Realtime; on historical bars
//            the indicator draws one fixed notice and leaves its plots unset.
//  Output  : price labels "Iceberg bid 7012.25 ~340 hidden (6 refills, 82%)" with a
//            short horizontal line at the level (updated with the end reason when
//            the level ends) and four DataBox-only plots per bar: IcebergBidVolume,
//            IcebergAskVolume (sum of hidden_est of levels finalized in the bar),
//            IcebergCount (levels flagged in the bar), MaxConfidence (largest conf
//            of any record emitted in the bar, 0 if none).
// ============================================================================
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
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
using NinjaTrader.NinjaScript.Indicators.QuantIndicators.Engines;
#endregion

// This namespace holds Indicators in this folder and is required. Do not change it.
namespace NinjaTrader.NinjaScript.Indicators
{
	public class QI_28_IcebergDetector : Indicator
	{
		private const string HistoricalNotice =
			"Iceberg detection runs on live or Market Replay data (historical Tick Replay has no bid/ask sizes).";

		// OnMarketData and OnBarUpdate may run on different threads: everything below
		// that both touch (engine, seq, per-bar accumulators, level start times) is
		// read and written only while holding 'sync'. Drawing happens after the lock
		// is released, from jobs prepared inside it.
		private readonly object sync = new object();
		private IcebergEngine	engine;
		private long			seq;

		// per-bar accumulators (realtime only)
		private double			accBidHidden;
		private double			accAskHidden;
		private int				accCount;
		private double			accMaxConf;

		// drawing anchors of the current engine level on each side
		private long			bidStartSeq;
		private long			askStartSeq;
		private DateTime		bidStartTime;
		private DateTime		askStartTime;
		private DateTime		bidFlagTime;
		private DateTime		askFlagTime;
		private DateTime		lastEventTime;

		private bool			noticeDrawn;
		private bool			disclaimerDrawn;

		private sealed class DrawJob
		{
			public string	Tag;
			public string	Text;
			public bool		IsBid;
			public double	Price;
			public DateTime	LineStart;
			public DateTime	LineEnd;
			public DateTime	LabelTime;
		}

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Labels probable iceberg orders at the best bid/ask: a price level that keeps trading "
											+ "while its displayed size is refilled, until traded volume exceeds HiddenRatio x the "
											+ "largest displayed size. Needs bid/ask sizes, so it detects only on live or Market Replay "
											+ "data, never on historical bars. "
											+ "Educational use only - not financial advice.";
				Name						= "QI_28_IcebergDetector";
				// OnEachTick is NOT used for detection (that runs in OnMarketData, independent of
				// Calculate). It is chosen for two bar-side jobs: (1) spec section 7 resets the engine via
				// Bars.IsFirstBarOfSession "on the first tick of a new session" - only a per-tick
				// OnBarUpdate sees that tick, and NinjaTrader calls OnBarUpdate before OnMarketData for
				// the same tick, so the R event precedes the new session's trades; (2) the DataBox
				// values of the forming bar update live instead of only at bar close. OnBarUpdate does
				// a handful of assignments, so the per-tick cost is negligible.
				Calculate					= Calculate.OnEachTick;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= false;
				ScaleJustification			= ScaleJustification.Right;
				// Market-data events skipped while suspended cannot be recovered (there is no
				// historical bid/ask size to rebuild from), so the indicator is never suspended.
				IsSuspendedWhileInactive	= false;
				ShowTransparentPlotsInDataBox = true;

				HiddenRatio					= 2.0;
				MinRefills					= 2;
				MinVolume					= 20;
				MinRefillSize				= 1;
				ShowLabels					= true;
				BidBrush					= Brushes.DeepSkyBlue;
				AskBrush					= Brushes.Orange;
				ShowDisclaimer				= false;

				AddPlot(Brushes.Transparent, "IcebergBidVolume");	// DataBox only
				AddPlot(Brushes.Transparent, "IcebergAskVolume");	// DataBox only
				AddPlot(Brushes.Transparent, "IcebergCount");		// DataBox only
				AddPlot(Brushes.Transparent, "MaxConfidence");		// DataBox only
			}
			else if (State == State.DataLoaded)
			{
				lock (sync)
				{
					engine			= new IcebergEngine(HiddenRatio, MinRefills, MinVolume, MinRefillSize);
					seq				= 0;
					ResetAccumulators();
					bidStartSeq		= -1;
					askStartSeq		= -1;
					bidStartTime	= DateTime.MinValue;
					askStartTime	= DateTime.MinValue;
					bidFlagTime		= DateTime.MinValue;
					askFlagTime		= DateTime.MinValue;
					lastEventTime	= DateTime.MinValue;
				}
				noticeDrawn		= false;
				disclaimerDrawn	= false;
			}
		}

		protected override void OnBarUpdate()
		{
			DrawDisclaimerOnce();

			if (State == State.Historical)
			{
				// No bid/ask sizes on historical bars: detect nothing, leave plots unset.
				DrawNoticeOnce();
				return;
			}
			if (State != State.Realtime)
				return;

			List<DrawJob> jobs = null;
			lock (sync)
			{
				if (IsFirstTickOfBar)
				{
					// Events that arrived after the previous bar's last OnBarUpdate belong to it.
					if (CurrentBar >= 1)
						WriteAccumulators(1);
					ResetAccumulators();

					if (Bars.IsFirstBarOfSession)
					{
						seq++;
						engine.OnReset(seq);
						List<IcebergRecord> recs = engine.LastRecords;
						Accumulate(recs);
						DateTime end = lastEventTime != DateTime.MinValue ? lastEventTime : Time[0];
						jobs = MakeJobs(recs, end);
						UpdateLevelStarts(end);
					}
				}
				WriteAccumulators(0);
			}
			RunJobs(jobs);
		}

		protected override void OnMarketData(MarketDataEventArgs e)
		{
			// Detection only on live / Market Replay data (Playback runs in State.Realtime).
			if (State != State.Realtime)
				return;

			List<DrawJob> jobs;
			lock (sync)
			{
				if (engine == null)
					return;

				switch (e.MarketDataType)
				{
					case MarketDataType.Bid:
						seq++;
						engine.OnBid(seq, e.Price, e.Volume);
						break;
					case MarketDataType.Ask:
						seq++;
						engine.OnAsk(seq, e.Price, e.Volume);
						break;
					case MarketDataType.Last:
						seq++;
						engine.OnTrade(seq, e.Price, e.Volume, KnownPrice(e.Bid), KnownPrice(e.Ask));
						break;
					default:
						return;
				}

				lastEventTime = e.Time;
				List<IcebergRecord> recs = engine.LastRecords;
				Accumulate(recs);
				jobs = MakeJobs(recs, e.Time);
				UpdateLevelStarts(e.Time);
			}
			RunJobs(jobs);
		}

		// NinjaTrader reports 0 for a bid/ask price that is not known yet; the engine's
		// "unknown" is NaN (spec section 7).
		private static double KnownPrice(double p)
		{
			return (double.IsNaN(p) || p == 0.0) ? double.NaN : p;
		}

		// ─────────────────────────────────────────────────────────
		//  Per-bar accumulators (call with 'sync' held)
		// ─────────────────────────────────────────────────────────
		private void ResetAccumulators()
		{
			accBidHidden	= 0;
			accAskHidden	= 0;
			accCount		= 0;
			accMaxConf		= 0;
		}

		private void Accumulate(List<IcebergRecord> recs)
		{
			foreach (IcebergRecord r in recs)
			{
				if (r.IsFlag)
					accCount++;
				else if (r.IsBid)
					accBidHidden += r.HiddenEst;
				else
					accAskHidden += r.HiddenEst;
				if (r.Conf > accMaxConf)
					accMaxConf = r.Conf;
			}
		}

		private void WriteAccumulators(int barsAgo)
		{
			Values[0][barsAgo] = accBidHidden;
			Values[1][barsAgo] = accAskHidden;
			Values[2][barsAgo] = accCount;
			Values[3][barsAgo] = accMaxConf;
		}

		// ─────────────────────────────────────────────────────────
		//  Labels (jobs prepared with 'sync' held, drawn after)
		// ─────────────────────────────────────────────────────────
		private void UpdateLevelStarts(DateTime now)
		{
			long b = engine.LevelStartSeq(true);
			if (b != bidStartSeq) { bidStartSeq = b; bidStartTime = now; }
			long a = engine.LevelStartSeq(false);
			if (a != askStartSeq) { askStartSeq = a; askStartTime = now; }
		}

		private List<DrawJob> MakeJobs(List<IcebergRecord> recs, DateTime now)
		{
			if (recs.Count == 0)
				return null;

			List<DrawJob> jobs = new List<DrawJob>(recs.Count);
			foreach (IcebergRecord r in recs)
			{
				bool isBid = r.IsBid;
				long curStart = isBid ? bidStartSeq : askStartSeq;
				DateTime start = (curStart == r.StartSeq) ? (isBid ? bidStartTime : askStartTime) : now;

				DateTime labelTime;
				if (r.IsFlag)
				{
					labelTime = now;
					if (isBid) bidFlagTime = now; else askFlagTime = now;
				}
				else
				{
					DateTime ft = isBid ? bidFlagTime : askFlagTime;
					labelTime = ft != DateTime.MinValue ? ft : now;
				}

				string text = "Iceberg " + r.Side + " " + Instrument.MasterInstrument.FormatPrice(r.Price)
					+ " ~" + r.HiddenEst.ToString(CultureInfo.InvariantCulture) + " hidden ("
					+ r.Refills.ToString(CultureInfo.InvariantCulture) + " refills, "
					+ ((int)Math.Round(r.Conf * 100.0)).ToString(CultureInfo.InvariantCulture) + "%)";
				if (!r.IsFlag)
					text += " - " + r.Reason;

				jobs.Add(new DrawJob
				{
					Tag			= "QI28_" + r.Side + "_" + r.StartSeq.ToString(CultureInfo.InvariantCulture),
					Text		= text,
					IsBid		= isBid,
					Price		= r.Price,
					LineStart	= start,
					LineEnd		= now,
					LabelTime	= labelTime
				});
			}
			return jobs;
		}

		private void RunJobs(List<DrawJob> jobs)
		{
			// CurrentBar < 0: market data before the first bar exists (nothing to anchor to yet).
			if (jobs == null || !ShowLabels || CurrentBar < 0)
				return;

			SimpleFont font = new SimpleFont("Arial", 10);
			foreach (DrawJob j in jobs)
			{
				Brush brush = j.IsBid ? BidBrush : AskBrush;
				Draw.Line(this, j.Tag + "_line", false, j.LineStart, j.Price, j.LineEnd, j.Price,
					brush, DashStyleHelper.Solid, 2);
				Draw.Text(this, j.Tag + "_text", false, j.Text, j.LabelTime, j.Price, j.IsBid ? -12 : 12,
					brush, font, TextAlignment.Left, Brushes.Transparent, Brushes.Transparent, 0);
			}
		}

		private void DrawNoticeOnce()
		{
			if (noticeDrawn)
				return;

			Draw.TextFixed(this, "QI28_HistoricalNotice", HistoricalNotice,
				TextPosition.TopLeft, Brushes.Gray, new SimpleFont("Arial", 10),
				Brushes.Transparent, Brushes.Transparent, 0);
			noticeDrawn = true;
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
			get { return "QI 28 IcebergDetector"; }
		}

		#region Properties

		[NinjaScriptProperty]
		[Range(0.0, 1000.0)]
		[Display(Name = "Hidden Ratio", Description = "Flag when traded volume >= this x the largest displayed size. Default 2.0.",
			Order = 1, GroupName = "Parameters")]
		public double HiddenRatio { get; set; }

		[NinjaScriptProperty]
		[Range(0, int.MaxValue)]
		[Display(Name = "Min Refills", Description = "Minimum displayed-size refills after absorbed trades. Default 2.",
			Order = 2, GroupName = "Parameters")]
		public int MinRefills { get; set; }

		[NinjaScriptProperty]
		[Range(0, int.MaxValue)]
		[Display(Name = "Min Volume", Description = "Minimum volume traded at the level. Default 20.",
			Order = 3, GroupName = "Parameters")]
		public int MinVolume { get; set; }

		[NinjaScriptProperty]
		[Range(0, int.MaxValue)]
		[Display(Name = "Min Refill Size", Description = "Minimum displayed-size increase that counts as a refill. Default 1.",
			Order = 4, GroupName = "Parameters")]
		public int MinRefillSize { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Labels", Description = "Draw a label and a short line at each flagged level.",
			Order = 1, GroupName = "Display")]
		public bool ShowLabels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 2, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[XmlIgnore]
		[Display(Name = "Bid Color", Description = "Color for bid-side labels. Default DeepSkyBlue.",
			Order = 1, GroupName = "Colors")]
		public Brush BidBrush { get; set; }
		[Browsable(false)]
		public string BidBrushSerialize
		{ get { return Serialize.BrushToString(BidBrush); } set { BidBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Ask Color", Description = "Color for ask-side labels. Default Orange.",
			Order = 2, GroupName = "Colors")]
		public Brush AskBrush { get; set; }
		[Browsable(false)]
		public string AskBrushSerialize
		{ get { return Serialize.BrushToString(AskBrush); } set { AskBrush = Serialize.StringToBrush(value); } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> IcebergBidVolume
		{
			get { return Values[0]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> IcebergAskVolume
		{
			get { return Values[1]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> IcebergCount
		{
			get { return Values[2]; }
		}

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> MaxConfidence
		{
			get { return Values[3]; }
		}

		#endregion
	}
}

// ============================================================================
//  IcebergEngine - spec sections 3-6, NinjaTrader-free.
//  Uses only System, System.Collections.Generic and System.Globalization (all in
//  mscorlib), so a plain net48 console program can construct and drive it without
//  loading any NinjaTrader assembly.
// ============================================================================
namespace NinjaTrader.NinjaScript.Indicators.QuantIndicators.Engines
{
	/// <summary>One emitted record (spec section 6) in structured form; Csv is the contract line.</summary>
	public sealed class IcebergRecord
	{
		/// <summary>"FLAG" or "FINAL".</summary>
		public string	Kind			{ get; internal set; }
		/// <summary>"bid" or "ask".</summary>
		public string	Side			{ get; internal set; }
		public double	Price			{ get; internal set; }
		/// <summary>FLAG: the triggering event. FINAL: the event that caused finalization (end_seq).</summary>
		public long		Seq				{ get; internal set; }
		/// <summary>start_seq of the level (also set on FLAG, where the CSV line omits it).</summary>
		public long		StartSeq		{ get; internal set; }
		public long		Traded			{ get; internal set; }
		public long		ShownMax		{ get; internal set; }
		/// <summary>traded - shown_max (also set on FLAG, where the CSV line omits it).</summary>
		public long		HiddenEst		{ get; internal set; }
		public int		Refills			{ get; internal set; }
		/// <summary>FINAL only (0 on FLAG).</summary>
		public double	MedianRefill	{ get; internal set; }
		/// <summary>FINAL only: held, broken or open (null on FLAG).</summary>
		public string	Reason			{ get; internal set; }
		public double	Conf			{ get; internal set; }
		public string	Csv				{ get; internal set; }

		public bool		IsFlag			{ get { return Kind == "FLAG"; } }
		public bool		IsBid			{ get { return Side == "bid"; } }

		public override string ToString() { return Csv; }
	}

	public class IcebergEngine
	{
		/// <summary>Two prices are equal when |a - b| &lt; 1e-9 (spec section 1).</summary>
		public const double PriceEpsilon = 1e-9;

		private sealed class Level
		{
			public double		Price;
			public long			StartSeq;
			public long			ShownMax;
			public long			LastShown;
			public long			Traded;
			public int			Refills;
			public List<long>	RefillSizes = new List<long>();
			public bool			Pending;
			public bool			Flagged;
			public double		FlagConf;
		}

		private readonly double	hiddenRatio;
		private readonly int	minRefills;
		private readonly long	minVolume;
		private readonly long	minRefillSize;

		private Level bid;
		private Level ask;
		private List<IcebergRecord> current = new List<IcebergRecord>();

		public IcebergEngine(double hiddenRatio, int minRefills, long minVolume, long minRefillSize)
		{
			this.hiddenRatio	= hiddenRatio;
			this.minRefills		= minRefills;
			this.minVolume		= minVolume;
			this.minRefillSize	= minRefillSize;
			LastRecords			= new List<IcebergRecord>();
		}

		public double	HiddenRatio		{ get { return hiddenRatio; } }
		public int		MinRefills		{ get { return minRefills; } }
		public long		MinVolume		{ get { return minVolume; } }
		public long		MinRefillSize	{ get { return minRefillSize; } }

		/// <summary>Trades that were neither clearly seller- nor buyer-initiated (cumulative, never reset).</summary>
		public long Unclassified { get; private set; }

		/// <summary>Structured form of the records returned by the most recent On* call (same order).</summary>
		public List<IcebergRecord> LastRecords { get; private set; }

		/// <summary>start_seq of the current level on that side, or -1 when there is none.</summary>
		public long LevelStartSeq(bool bidSide)
		{
			Level lv = bidSide ? bid : ask;
			return lv == null ? -1 : lv.StartSeq;
		}

		/// <summary>Price of the current level on that side, or NaN when there is none.</summary>
		public double LevelPrice(bool bidSide)
		{
			Level lv = bidSide ? bid : ask;
			return lv == null ? double.NaN : lv.Price;
		}

		// ── public event API (spec section 7) ──────────────────────────────────

		public List<string> OnBid(long seq, double price, long size)
		{
			Begin();
			Quote(true, seq, price, size);
			return End();
		}

		public List<string> OnAsk(long seq, double price, long size)
		{
			Begin();
			Quote(false, seq, price, size);
			return End();
		}

		/// <summary>bid/ask are the best bid/ask PRICES at the trade; double.NaN = unknown.</summary>
		public List<string> OnTrade(long seq, double price, long volume, double bid, double ask)
		{
			Begin();
			Trade(seq, price, volume, bid, ask);
			return End();
		}

		public List<string> OnReset(long seq)
		{
			Begin();
			// R event: finalize both current levels with reason "open" (bid before ask).
			if (bid != null) FinalizeLevel(bid, true, seq, "open");
			bid = null;
			if (ask != null) FinalizeLevel(ask, false, seq, "open");
			ask = null;
			return End();
		}

		// ── section 3: per-side level state ────────────────────────────────────

		private static bool PriceEq(double a, double b)
		{
			return Math.Abs(a - b) < PriceEpsilon;
		}

		private void SetLevel(bool isBid, Level lv)
		{
			if (isBid) bid = lv; else ask = lv;
		}

		private void Quote(bool isBid, long seq, double q, long s)
		{
			Level lv = isBid ? bid : ask;

			// 1. no current level, or a different price
			if (lv == null || !PriceEq(q, lv.Price))
			{
				if (lv != null)
				{
					// 1a. bid: q > p held, q < p broken; ask mirrored.
					string reason = isBid ? (q > lv.Price ? "held" : "broken")
										  : (q < lv.Price ? "held" : "broken");
					FinalizeLevel(lv, isBid, seq, reason);
				}

				// 1b. a new level only when s > 0; otherwise no current level.
				Level fresh = null;
				if (s > 0)
				{
					fresh = new Level();
					fresh.Price		= q;
					fresh.StartSeq	= seq;
					fresh.ShownMax	= s;
					fresh.LastShown	= s;
					fresh.Traded	= 0;
					fresh.Refills	= 0;
					fresh.Pending	= false;
					fresh.Flagged	= false;
				}
				SetLevel(isBid, fresh);
				return;
			}

			// 2. same price
			if (s == 0)
			{
				// 2a. displayed size gone: broken, no current level.
				FinalizeLevel(lv, isBid, seq, "broken");
				SetLevel(isBid, null);
				return;
			}
			if (s < 0)
				return;	// outside the spec's domain (size >= 0): no rule applies

			// 2b. refill: size grew after an absorbed trade by at least MinRefillSize.
			if (s > lv.LastShown && lv.Pending && (s - lv.LastShown) >= minRefillSize)
			{
				lv.Refills += 1;
				lv.RefillSizes.Add(s);
				lv.Pending = false;
			}

			// 2c. all s > 0 cases.
			lv.LastShown = s;
			if (s > lv.ShownMax)
				lv.ShownMax = s;
			EvaluateFlag(lv, isBid, seq);
		}

		private void Trade(long seq, double x, long v, double b, double a)
		{
			bool bKnown = !double.IsNaN(b);
			bool aKnown = !double.IsNaN(a);
			bool sellerInitiated = bKnown && (x < b || PriceEq(x, b));
			bool buyerInitiated  = aKnown && (x > a || PriceEq(x, a));

			// neither, or both (crossed book): unclassified, nothing else happens.
			if (sellerInitiated == buyerInitiated)
			{
				Unclassified++;
				return;
			}

			if (sellerInitiated)
			{
				if (bid != null && PriceEq(x, bid.Price))
				{
					bid.Traded += v;
					bid.Pending = true;
					EvaluateFlag(bid, true, seq);
				}
			}
			else
			{
				if (ask != null && PriceEq(x, ask.Price))
				{
					ask.Traded += v;
					ask.Pending = true;
					EvaluateFlag(ask, false, seq);
				}
			}
			// trades at other prices change nothing.
		}

		// ── section 4: flag rule ───────────────────────────────────────────────

		private double Conf(Level lv)
		{
			double c = 0.4 + 0.15 * (lv.Refills - minRefills) + 0.1 * ((double)lv.Traded / lv.ShownMax - hiddenRatio);
			if (c < 0.4) return 0.4;
			if (c > 1.0) return 1.0;
			return c;
		}

		private void EvaluateFlag(Level lv, bool isBid, long seq)
		{
			if (lv.Flagged || lv.ShownMax <= 0)
				return;
			if ((double)lv.Traded >= hiddenRatio * lv.ShownMax
				&& lv.Refills >= minRefills
				&& lv.Traded >= minVolume)
			{
				lv.Flagged	= true;
				lv.FlagConf	= Conf(lv);

				IcebergRecord r = new IcebergRecord();
				r.Kind		= "FLAG";
				r.Side		= isBid ? "bid" : "ask";
				r.Price		= lv.Price;
				r.Seq		= seq;
				r.StartSeq	= lv.StartSeq;
				r.Traded	= lv.Traded;
				r.ShownMax	= lv.ShownMax;
				r.HiddenEst	= lv.Traded - lv.ShownMax;
				r.Refills	= lv.Refills;
				r.Conf		= lv.FlagConf;
				r.Csv		= string.Join(",", new string[] {
					"FLAG", r.Side, F4(r.Price), I(r.Seq), I(r.Traded), I(r.ShownMax), I(r.Refills), F4(r.Conf) });
				current.Add(r);
			}
		}

		// ── section 5: finalize ────────────────────────────────────────────────

		private void FinalizeLevel(Level lv, bool isBid, long endSeq, string reason)
		{
			if (!lv.Flagged)
				return;	// unflagged levels are discarded silently

			IcebergRecord r = new IcebergRecord();
			r.Kind			= "FINAL";
			r.Side			= isBid ? "bid" : "ask";
			r.Price			= lv.Price;
			r.Seq			= endSeq;
			r.StartSeq		= lv.StartSeq;
			r.Traded		= lv.Traded;
			r.ShownMax		= lv.ShownMax;
			r.HiddenEst		= lv.Traded - lv.ShownMax;
			r.Refills		= lv.Refills;
			r.MedianRefill	= Median(lv.RefillSizes);
			r.Reason		= reason;
			r.Conf			= Conf(lv);
			r.Csv			= string.Join(",", new string[] {
				"FINAL", r.Side, F4(r.Price), I(r.StartSeq), I(r.Seq), I(r.Traded), I(r.ShownMax), I(r.HiddenEst),
				I(r.Refills), F4(r.MedianRefill), r.Reason, F4(r.Conf) });
			current.Add(r);
		}

		private static double Median(List<long> values)
		{
			int n = values.Count;
			if (n == 0)
				return 0.0;
			List<long> sorted = new List<long>(values);
			sorted.Sort();
			if (n % 2 == 1)
				return sorted[n / 2];
			return (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0;
		}

		// ── section 6: formatting ──────────────────────────────────────────────

		private static string F4(double v)
		{
			return v.ToString("F4", CultureInfo.InvariantCulture);
		}

		private static string I(long v)
		{
			return v.ToString(CultureInfo.InvariantCulture);
		}

		private void Begin()
		{
			current = new List<IcebergRecord>();
		}

		private List<string> End()
		{
			LastRecords = current;
			List<string> lines = new List<string>(current.Count);
			foreach (IcebergRecord r in current)
				lines.Add(r.Csv);
			return lines;
		}
	}
}
