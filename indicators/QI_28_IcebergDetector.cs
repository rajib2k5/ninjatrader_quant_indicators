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
//  Output  : one table in a box at the lower right of the price panel, newest row
//            first (validation/iceberg/table-spec.md): detected time, side, price,
//            ~hidden, traded, shown, refills, confidence, status and end time. The
//            box never covers other QI_28 boxes, TextFixed notes of any script, the
//            chart labels, the copyright text or the axes. At each flagged price a
//            short line and a "#n" tag link the level to its table row. Four
//            DataBox-only plots per bar: IcebergBidVolume,
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
// SharpDX names that would clash with WPF ones (Brush, Factory, Color, Point) are aliased.
using DxBrush		= SharpDX.Direct2D1.Brush;
using RectangleF	= SharpDX.RectangleF;
using Vector2		= SharpDX.Vector2;
using TextFormat	= SharpDX.DirectWrite.TextFormat;
using TextLayout	= SharpDX.DirectWrite.TextLayout;
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

		private bool			disclaimerDrawn;

		// the table behind the box (guarded by 'sync')
		private IcebergTable	table;

		// Boxes of every QI_28 instance, so a later instance on the same panel stacks above an
		// earlier one. OnRender of different chart windows can run on different UI threads.
		private static readonly object							registryLock	= new object();
		private static readonly List<QI_28_IcebergDetector>	registry		= new List<QI_28_IcebergDetector>();
		private ChartPanel		lastPanel;		// guarded by registryLock
		private BoxRect?		lastBox;		// guarded by registryLock
		private List<BoxRect>	lastTextFixed	= new List<BoxRect>();

		// SharpDX brushes: created on first use per render target, disposed when it changes
		private DxBrush			dxBackground, dxBorder, dxText, dxMuted, dxBid, dxAsk;

		private const float		BoxPad		= 6f;
		private const float		CellPadX	= 6f;
		private const float		LineGap		= 2f;
		private const double	BoxMargin	= 8;
		private const double	BoxGap		= 6;

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
				ShowTable					= true;
				MaxTableRows				= 8;
				TableFontSize				= 11;
				TableOpacity				= 85;
				ShowLevelLines				= true;
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
					table			= new IcebergTable();
				}
				disclaimerDrawn	= false;
			}
			else if (State == State.Terminated)
			{
				lock (registryLock)
					registry.Remove(this);
				DisposeDx();
			}
		}

		protected override void OnBarUpdate()
		{
			DrawDisclaimerOnce();

			if (State == State.Historical)
			{
				// No bid/ask sizes on historical bars: detect nothing, leave plots unset.
				// The notice is shown inside the table box (OnRender).
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
						jobs = ApplyRecords(recs, end);
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
				jobs = ApplyRecords(recs, e.Time);
				UpdateLevelStarts(e.Time);
			}
			RunJobs(jobs);
			if (jobs != null)
				ForceRefresh();		// repaint the table box
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
		//  Table rows and level lines (prepared with 'sync' held, drawn after)
		// ─────────────────────────────────────────────────────────
		private void UpdateLevelStarts(DateTime now)
		{
			long b = engine.LevelStartSeq(true);
			if (b != bidStartSeq) { bidStartSeq = b; bidStartTime = now; }
			long a = engine.LevelStartSeq(false);
			if (a != askStartSeq) { askStartSeq = a; askStartTime = now; }
		}

		// Applies every record to the table and returns the level-line jobs ("#n" = table row id).
		private List<DrawJob> ApplyRecords(List<IcebergRecord> recs, DateTime now)
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

				int id = table.Apply(r, now);
				if (id == 0)
					continue;		// FINAL of a row already dropped by the capacity limit
				string text = "#" + id.ToString(CultureInfo.InvariantCulture);

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
			if (jobs == null || !ShowLevelLines || CurrentBar < 0)
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

		private void DrawDisclaimerOnce()
		{
			if (!ShowDisclaimer || disclaimerDrawn)
				return;

			Draw.TextFixed(this, "QI_Disclaimer", "Educational use only - not financial advice",
				TextPosition.BottomLeft, Brushes.Gray, new SimpleFont("Arial", 9),
				Brushes.Transparent, Brushes.Transparent, 0);
			disclaimerDrawn = true;
		}

		// ─────────────────────────────────────────────────────────
		//  Table box (validation/iceberg/table-spec.md sections 3-5)
		// ─────────────────────────────────────────────────────────
		public override void OnRenderTargetChanged()
		{
			// SharpDX brushes belong to one render target: drop them, they are recreated on the next OnRender.
			DisposeDx();
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (IsInHitTest || RenderTarget == null || ChartPanel == null || chartControl == null)
				return;
			if (!ShowTable)
			{
				SetLastBox(null);
				return;
			}

			// Rows are updated in place by FINAL records on the data thread, so their text is
			// built while 'sync' is held; nothing below reads a row object.
			List<string[]> cells;
			List<bool> isBid;
			int total;
			lock (sync)
			{
				if (table == null)
					return;
				List<IcebergTableRow> rows = table.Rows(MaxTableRows);
				total	= table.Count;
				cells	= new List<string[]>(rows.Count);
				isBid	= new List<bool>(rows.Count);
				foreach (IcebergTableRow r in rows)
				{
					cells.Add(IcebergTable.Cells(r, p => Instrument.MasterInstrument.FormatPrice(p)));
					isBid.Add(r.Side == "bid");
				}
			}

			try
			{
				EnsureDx(chartControl);
			}
			catch (Exception)
			{
				DisposeDx();
				return;
			}
			BoxRect panel = new BoxRect(ChartPanel.X, ChartPanel.Y, ChartPanel.W, ChartPanel.H);
			List<BoxRect> occupied = Occupied(panel);

			List<string> top = new List<string> { IcebergTable.Title };
			if (State != State.Realtime)
			{
				// spec.md section 0 notice, verbatim, split in two lines so the box stays narrow
				int cut = HistoricalNotice.IndexOf(" (", StringComparison.Ordinal);
				top.Add(HistoricalNotice.Substring(0, cut));
				top.Add(HistoricalNotice.Substring(cut + 1));
			}
			string[] header		= IcebergTable.Header;
			bool[] rightAligned	= IcebergTable.RightAligned;

			List<TextLayout> made = new List<TextLayout>();
			try
			{
				using (TextFormat fmt = new SimpleFont("Consolas", TableFontSize).ToDirectWriteTextFormat())
				{
					Func<string, TextLayout> make = text =>
					{
						TextLayout l = new TextLayout(NinjaTrader.Core.Globals.DirectWriteFactory, text, fmt, 4000f, 400f);
						made.Add(l);
						return l;
					};

					List<TextLayout> topL = new List<TextLayout>();
					foreach (string t in top)
						topL.Add(make(t));
					TextLayout[] headL = new TextLayout[header.Length];
					for (int c = 0; c < header.Length; c++)
						headL[c] = make(header[c]);
					List<TextLayout[]> cellL = new List<TextLayout[]>(cells.Count);
					foreach (string[] row in cells)
					{
						TextLayout[] l = new TextLayout[row.Length];
						for (int c = 0; c < row.Length; c++)
							l[c] = make(row[c]);
						cellL.Add(l);
					}
					TextLayout emptyL	= make(IcebergTable.EmptyText);
					TextLayout widestFooterL = make(IcebergTable.Footer(Math.Max(total, 1)));

					float lineH = headL[0].Metrics.Height;
					foreach (TextLayout l in made)
						lineH = Math.Max(lineH, l.Metrics.Height);
					lineH += LineGap;

					float[] colW = new float[header.Length];
					for (int c = 0; c < header.Length; c++)
					{
						colW[c] = headL[c].Metrics.Width;
						foreach (TextLayout[] l in cellL)
							colW[c] = Math.Max(colW[c], l[c].Metrics.Width);
						colW[c] += 2 * CellPadX;
					}
					float contentW = cells.Count > 0 ? colW.Sum() : emptyL.Metrics.Width;
					foreach (TextLayout l in topL)
						contentW = Math.Max(contentW, l.Metrics.Width);
					contentW = Math.Max(contentW, widestFooterL.Metrics.Width);
					double boxW = contentW + 2 * BoxPad;

					// Fewest rows dropped until the box fits without overlap (spec section 3).
					for (int n = cells.Count; n >= 0; n--)
					{
						int notShown = total - n;
						int bodyLines = cells.Count == 0 ? 1 : 1 + n;
						int lines = top.Count + bodyLines + (notShown > 0 ? 1 : 0);
						double boxH = 2 * BoxPad + lines * lineH + 3;		// +3: rule under the header
						BoxRect? placed = BoxLayout.Place(panel, boxW, boxH, occupied, BoxMargin, BoxGap);
						if (!placed.HasValue)
							continue;

						DrawBox(placed.Value, topL, headL, cellL, isBid, n, notShown > 0 ? make(IcebergTable.Footer(notShown)) : null,
							cells.Count == 0 ? emptyL : null, colW, rightAligned, lineH);
						SetLastBox(placed);
						return;
					}
					SetLastBox(null);		// not even the title fits: draw nothing this frame
				}
			}
			finally
			{
				foreach (TextLayout l in made)
					l.Dispose();
			}
		}

		private void DrawBox(BoxRect b, List<TextLayout> topL, TextLayout[] headL, List<TextLayout[]> cellL,
			List<bool> isBid, int n, TextLayout footerL, TextLayout emptyL, float[] colW, bool[] rightAligned, float lineH)
		{
			RectangleF rect = new RectangleF((float)b.X, (float)b.Y, (float)b.W, (float)b.H);
			RenderTarget.FillRectangle(rect, dxBackground);
			RenderTarget.DrawRectangle(rect, dxBorder, 1f);

			float x0 = rect.X + BoxPad;
			float y = rect.Y + BoxPad;
			for (int i = 0; i < topL.Count; i++)
			{
				RenderTarget.DrawTextLayout(new Vector2(x0, y), topL[i], i == 0 ? dxText : dxMuted);
				y += lineH;
			}

			if (emptyL != null)
			{
				RenderTarget.DrawTextLayout(new Vector2(x0, y), emptyL, dxMuted);
				y += lineH;
			}
			else
			{
				DrawCells(headL, x0, y, colW, rightAligned, null);
				y += lineH;
				RenderTarget.FillRectangle(new RectangleF(x0, y, rect.Width - 2 * BoxPad, 1f), dxBorder);
				y += 3;
				for (int i = 0; i < n; i++)
				{
					DrawCells(cellL[i], x0, y, colW, rightAligned, isBid[i] ? dxBid : dxAsk);
					y += lineH;
				}
			}

			if (footerL != null)
				RenderTarget.DrawTextLayout(new Vector2(x0, y), footerL, dxMuted);
		}

		// sideBrush colours the Side and Price columns of a data row; null for the header.
		private void DrawCells(TextLayout[] l, float x0, float y, float[] colW, bool[] rightAligned, DxBrush sideBrush)
		{
			float x = x0;
			for (int c = 0; c < l.Length; c++)
			{
				float tx = rightAligned[c] ? x + colW[c] - CellPadX - l[c].Metrics.Width : x + CellPadX;
				DxBrush brush = (sideBrush != null && (c == 2 || c == 3)) ? sideBrush : dxText;
				RenderTarget.DrawTextLayout(new Vector2(tx, y), l[c], brush);
				x += colW[c];
			}
		}

		// Everything the box must not cover (spec section 4).
		private List<BoxRect> Occupied(BoxRect panel)
		{
			List<BoxRect> occ = PanelReserve.Strips(panel, ChartPanel.IsYAxisDisplayedOverlay);

			lock (registryLock)
			{
				if (!registry.Contains(this))
					registry.Add(this);
				foreach (QI_28_IcebergDetector other in registry)
				{
					if (other == this)
						break;		// only instances registered earlier; later ones stack above this one
					if (other.lastPanel == ChartPanel && other.lastBox.HasValue)
						occ.Add(other.lastBox.Value);
				}
			}

			// TextFixed notes of any script or the user. DrawObjects.ToList() is NinjaTrader's thread-safe
			// copy (Draw.* also runs on data threads). If the copy fails, the previous frame's estimates are
			// reused; an object that cannot be measured is skipped.
			List<IDrawingTool> drawn = null;
			try
			{
				drawn = DrawObjects.ToList();
			}
			catch (Exception)
			{
			}
			if (drawn != null)
			{
				List<BoxRect> fixedBoxes = new List<BoxRect>();
				foreach (IDrawingTool d in drawn)
				{
					TextFixed tf = d as TextFixed;
					if (tf == null || string.IsNullOrEmpty(tf.DisplayText) || tf.Font == null)
						continue;
					try
					{
						using (TextFormat f = tf.Font.ToDirectWriteTextFormat())
						using (TextLayout l = new TextLayout(NinjaTrader.Core.Globals.DirectWriteFactory, tf.DisplayText, f,
							(float)panel.W, (float)panel.H))
						{
							BoxRect? r = PanelReserve.ForTextFixed(tf.TextPosition.ToString(), panel,
								l.Metrics.Width, l.Metrics.Height, tf.YPixelOffset);
							if (r.HasValue)
								fixedBoxes.Add(r.Value);
						}
					}
					catch (Exception)
					{
					}
				}
				lastTextFixed = fixedBoxes;
			}
			occ.AddRange(lastTextFixed);
			return occ;
		}

		private void SetLastBox(BoxRect? box)
		{
			lock (registryLock)
			{
				lastBox		= box;
				lastPanel	= box.HasValue ? ChartPanel : null;
			}
		}

		private void EnsureDx(ChartControl chartControl)
		{
			if (dxText != null)
				return;
			Brush background	= chartControl.Properties.ChartBackground ?? Brushes.Black;
			Brush text			= chartControl.Properties.ChartText ?? Brushes.White;
			dxBackground		= background.ToDxBrush(RenderTarget);
			dxBackground.Opacity = TableOpacity / 100f;
			dxBorder			= text.ToDxBrush(RenderTarget);
			dxBorder.Opacity	= 0.5f;
			dxMuted				= text.ToDxBrush(RenderTarget);
			dxMuted.Opacity		= 0.75f;
			dxBid				= (BidBrush ?? Brushes.DeepSkyBlue).ToDxBrush(RenderTarget);
			dxAsk				= (AskBrush ?? Brushes.Orange).ToDxBrush(RenderTarget);
			dxText				= text.ToDxBrush(RenderTarget);	// last: marks the set as complete
		}

		private void DisposeDx()
		{
			DxBrush[] all = { dxBackground, dxBorder, dxText, dxMuted, dxBid, dxAsk };
			foreach (DxBrush b in all)
				if (b != null)
					b.Dispose();
			dxBackground = dxBorder = dxText = dxMuted = dxBid = dxAsk = null;
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

		[Display(Name = "Show Table", Description = "Show the iceberg table in a box at the lower right of the price panel.",
			Order = 1, GroupName = "Display")]
		public bool ShowTable { get; set; }

		[Range(1, 50)]
		[Display(Name = "Max Table Rows", Description = "Newest rows shown in the table (fewer if the panel is too short). Default 8.",
			Order = 2, GroupName = "Display")]
		public int MaxTableRows { get; set; }

		[Range(8, 24)]
		[Display(Name = "Table Font Size", Description = "Font size of the table text. Default 11.",
			Order = 3, GroupName = "Display")]
		public int TableFontSize { get; set; }

		[Range(10, 100)]
		[Display(Name = "Table Opacity %", Description = "Opacity of the table background. Default 85.",
			Order = 4, GroupName = "Display")]
		public int TableOpacity { get; set; }

		[Display(Name = "Show Level Lines", Description = "Draw a short line and a #n tag (the table row) at each flagged level.",
			Order = 5, GroupName = "Display")]
		public bool ShowLevelLines { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Disclaimer", Description = "Draw the educational-use disclaimer on the chart.",
			Order = 6, GroupName = "Display")]
		public bool ShowDisclaimer { get; set; }

		[XmlIgnore]
		[Display(Name = "Bid Color", Description = "Color for bid rows and lines. Default DeepSkyBlue.",
			Order = 1, GroupName = "Colors")]
		public Brush BidBrush { get; set; }
		[Browsable(false)]
		public string BidBrushSerialize
		{ get { return Serialize.BrushToString(BidBrush); } set { BidBrush = Serialize.StringToBrush(value); } }

		[XmlIgnore]
		[Display(Name = "Ask Color", Description = "Color for ask rows and lines. Default Orange.",
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

	/// <summary>An axis-aligned rectangle in RenderTarget pixels (Y grows downward). Overlap is strict.</summary>
	public struct BoxRect : IEquatable<BoxRect>
	{
		public readonly double X, Y, W, H;

		public BoxRect(double x, double y, double w, double h) { X = x; Y = y; W = w; H = h; }

		public double Right		{ get { return X + W; } }
		public double Bottom	{ get { return Y + H; } }

		/// <summary>True when the interiors intersect; touching edges do not overlap.</summary>
		public bool Overlaps(BoxRect o)
		{
			return X < o.Right && o.X < Right && Y < o.Bottom && o.Y < Bottom;
		}

		public BoxRect Inflate(double d) { return new BoxRect(X - d, Y - d, W + 2 * d, H + 2 * d); }

		public bool Equals(BoxRect o) { return X == o.X && Y == o.Y && W == o.W && H == o.H; }
		public override bool Equals(object o) { return o is BoxRect && Equals((BoxRect)o); }
		public override int GetHashCode() { return X.GetHashCode() ^ (Y.GetHashCode() * 31) ^ (W.GetHashCode() * 17) ^ H.GetHashCode(); }
		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "[{0},{1} {2}x{3}]", X, Y, W, H);
		}
	}

	/// <summary>Bottom-right placement that avoids occupied rectangles (table-spec.md section 3).</summary>
	public static class BoxLayout
	{
		public static BoxRect? Place(BoxRect panel, double w, double h, IList<BoxRect> occupied, double margin, double gap)
		{
			if (w > panel.W - 2 * margin || h > panel.H - 2 * margin)
				return null;

			double x = panel.Right - margin - w;
			double y = panel.Bottom - margin - h;
			// Each pass moves the box strictly upward past every rectangle it hits, so at most
			// occupied.Count + 1 passes are needed.
			for (int pass = 0; pass <= occupied.Count; pass++)
			{
				BoxRect grown = new BoxRect(x, y, w, h).Inflate(gap);
				double minTop = double.PositiveInfinity;
				foreach (BoxRect o in occupied)
					if (grown.Overlaps(o) && o.Y < minTop)
						minTop = o.Y;
				if (double.IsPositiveInfinity(minTop))
					return new BoxRect(x, y, w, h);
				y = minTop - gap - h;
				if (y < panel.Y + margin)
					return null;
			}
			return null;
		}
	}

	/// <summary>
	/// Areas the table must not cover (table-spec.md section 4, amendment A2). The TextFixed geometry follows the
	/// vendor @Text.cs of NinjaTrader 8.1.8.4: text 10.5 px from the panel edges (BottomLeft x2 on the last panel,
	/// TopLeft +21 for labels, TopRight up to +42 for the scroll arrow) and a box padding p that is 3 or 5, so each
	/// estimate is the union of every case.
	/// </summary>
	public static class PanelReserve
	{
		public const double TopStrip		= 48;
		public const double CopyrightH		= 24;
		public const double CopyrightMaxW	= 360;
		public const double OverlayAxisW	= 80;

		/// <param name="position">A NinjaTrader TextPosition name: BottomLeft, BottomRight, Center, TopLeft or TopRight.</param>
		public static BoxRect? ForTextFixed(string position, BoxRect panel, double w, double h, double yPixelOffset)
		{
			double o = Math.Abs(yPixelOffset);
			switch (position)
			{
				case "BottomRight":
					return Span(panel.Right - 10.5 - w - 5, panel.Right - 5.5, panel.Bottom - 10.5 - h - 5 - o, panel.Bottom - 5.5 + o);
				case "BottomLeft":
					return Span(panel.X + 5.5, panel.X + 10.5 + w + 5, panel.Bottom - 21 - h - 5 - o, panel.Bottom - 5.5 + o);
				case "TopLeft":
					return Span(panel.X + 5.5, panel.X + 10.5 + w + 5, panel.Y + 21 - 5 - o, panel.Y + 21 + h + 5 + o);
				case "TopRight":
					return Span(panel.Right - 10.5 - w - 5, panel.Right - 5.5, panel.Y + 10 - 5 - o, panel.Y + 42 + h + 5 + o);
				case "Center":
					return new BoxRect(panel.X + (panel.W - w) / 2 - 5, panel.Y + (panel.H - h) / 2 - 5 - o, w + 10, h + 10 + 2 * o);
				default:
					return null;
			}
		}

		/// <summary>The fixed strips: top (labels, scroll arrow), bottom-left copyright, and the overlay Y-axis when shown.</summary>
		public static List<BoxRect> Strips(BoxRect panel, bool yAxisOverlay)
		{
			List<BoxRect> s = new List<BoxRect>
			{
				new BoxRect(panel.X, panel.Y, panel.W, TopStrip),
				new BoxRect(panel.X, panel.Bottom - CopyrightH, Math.Min(CopyrightMaxW, panel.W / 2), CopyrightH)
			};
			if (yAxisOverlay)
				s.Add(new BoxRect(panel.Right - OverlayAxisW, panel.Y, OverlayAxisW, panel.H));
			return s;
		}

		private static BoxRect Span(double x0, double x1, double y0, double y1)
		{
			return new BoxRect(x0, y0, x1 - x0, y1 - y0);
		}
	}

	/// <summary>One table row: a flagged level, updated in place when it ends.</summary>
	public sealed class IcebergTableRow
	{
		public int			Id			{ get; internal set; }
		public DateTime		Detected	{ get; internal set; }
		public string		Side		{ get; internal set; }
		public double		Price		{ get; internal set; }
		public long			StartSeq	{ get; internal set; }
		public long			Hidden		{ get; internal set; }
		public long			Traded		{ get; internal set; }
		public long			Shown		{ get; internal set; }
		public int			Refills		{ get; internal set; }
		public double		Conf		{ get; internal set; }
		/// <summary>active, held, broken or open.</summary>
		public string		Status		{ get; internal set; }
		public DateTime?	Ended		{ get; internal set; }
	}

	/// <summary>The rows behind the on-chart table (table-spec.md section 2). Not thread-safe; the caller locks.</summary>
	public sealed class IcebergTable
	{
		public const int Capacity = 500;
		public const string Title = "QI 28 Iceberg levels (probable) - newest first";
		public const string EmptyText = "No probable iceberg levels yet.";

		private static readonly string[] header =
			{ "#", "Detected", "Side", "Price", "Hidden", "Traded", "Shown", "Refills", "Conf", "Status", "Ended" };
		private static readonly bool[] rightAligned =
			{ true, false, false, true, true, true, true, true, true, false, false };

		private readonly List<IcebergTableRow> rows = new List<IcebergTableRow>();
		private int nextId = 1;

		public static string[] Header		{ get { return (string[])header.Clone(); } }
		public static bool[] RightAligned	{ get { return (bool[])rightAligned.Clone(); } }

		public int Count { get { return rows.Count; } }

		public static string Footer(int notShown)
		{
			return "+" + notShown.ToString(CultureInfo.InvariantCulture) + " older not shown";
		}

		/// <summary>Applies one record; returns the row id it created or updated, 0 if none.</summary>
		public int Apply(IcebergRecord r, DateTime t)
		{
			if (r.IsFlag)
			{
				IcebergTableRow added = new IcebergTableRow
				{
					Id = nextId++, Detected = t, Side = r.Side, Price = r.Price, StartSeq = r.StartSeq,
					Hidden = r.HiddenEst, Traded = r.Traded, Shown = r.ShownMax, Refills = r.Refills, Conf = r.Conf,
					Status = "active", Ended = null
				};
				rows.Add(added);
				if (rows.Count > Capacity)
					rows.Remove(Oldest());
				return added.Id;
			}
			foreach (IcebergTableRow row in rows)
			{
				if (row.Status != "active" || row.Side != r.Side || row.StartSeq != r.StartSeq)
					continue;
				row.Hidden	= r.HiddenEst;
				row.Traded	= r.Traded;
				row.Shown	= r.ShownMax;
				row.Refills	= r.Refills;
				row.Conf	= r.Conf;
				row.Status	= r.Reason;
				row.Ended	= t;
				return row.Id;
			}
			return 0;
		}

		/// <summary>At most max rows, newest Detected first, ties by higher Id.</summary>
		public List<IcebergTableRow> Rows(int max)
		{
			List<IcebergTableRow> sorted = new List<IcebergTableRow>(rows);
			sorted.Sort(NewestFirst);
			if (max < sorted.Count)
				sorted.RemoveRange(Math.Max(max, 0), sorted.Count - Math.Max(max, 0));
			return sorted;
		}

		public static string[] Cells(IcebergTableRow r, Func<double, string> formatPrice)
		{
			CultureInfo inv = CultureInfo.InvariantCulture;
			string ended = "-";
			if (r.Ended.HasValue)
				ended = r.Ended.Value.Date == r.Detected.Date
					? r.Ended.Value.ToString("HH:mm:ss", inv)
					: r.Ended.Value.ToString("MM-dd HH:mm:ss", inv);
			return new[]
			{
				"#" + r.Id.ToString(inv),
				r.Detected.ToString("MM-dd HH:mm:ss", inv),
				r.Side,
				formatPrice(r.Price),
				"~" + r.Hidden.ToString(inv),
				r.Traded.ToString(inv),
				r.Shown.ToString(inv),
				r.Refills.ToString(inv),
				((long)Math.Round(r.Conf * 100.0, MidpointRounding.AwayFromZero)).ToString(inv) + "%",
				r.Status,
				ended
			};
		}

		private static int NewestFirst(IcebergTableRow a, IcebergTableRow b)
		{
			int c = b.Detected.CompareTo(a.Detected);
			return c != 0 ? c : b.Id.CompareTo(a.Id);
		}

		private IcebergTableRow Oldest()
		{
			IcebergTableRow o = rows[0];
			foreach (IcebergTableRow r in rows)
				if (NewestFirst(r, o) > 0)
					o = r;
			return o;
		}
	}
}
