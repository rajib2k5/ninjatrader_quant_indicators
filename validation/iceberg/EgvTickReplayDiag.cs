// ============================================================================
//  EgvTickReplayDiag - Channel B diagnostic for the iceberg research ledger (R8, R9, R16)
//  Part of ninjatrader_quant_indicators / validation / iceberg.  NOT a trading indicator.
//
//  What it measures (nothing is plotted, nothing is traded):
//    per State bucket (Historical / Realtime / Other):
//      - OnMarketData calls, split by MarketDataType (Ask, Bid, Last, DailyHigh, ...)
//      - Bid and Ask events with Volume > 0 vs Volume <= 0     (R16: are historical sizes present?)
//      - type switches between consecutive events and time regressions
//        (Time earlier than the previous event's Time)          (R8: interleaved, in sequence?)
//      - OnMarketDepth calls                                     (R9: depth in historical / playback?)
//    Prints one summary line at the State.Realtime transition, every 5,000 events
//    (OnMarketData + OnMarketDepth combined), and once at State.Terminated.
//    It also prints the first 5 historical Bid/Ask events verbatim.
//
//  How to run (user):
//    1. Copy into Documents\NinjaTrader 8\bin\Custom\Indicators, compile (F5) in the NinjaScript Editor.
//    2. Chart A: ES or MES, 1-minute (any bars type), Data Series > "Tick Replay" CHECKED, 2-5 days back.
//       Chart B: same but Tick Replay UNCHECKED (control).
//       Chart C (optional, R9): Playback connection on Market Replay data (e.g. GC 04-26, 2026-02-02).
//    3. Add EgvTickReplayDiag, open the NinjaScript Output window, copy the lines that start with "EGV|".
//  Expected-value guide: the header line reports Bars.IsTickReplay and Bars.IsInReplayMode so each
//  run is self-identifying; Hist.Bid/Ask counts of 0 mean no historical bid/ask events at all;
//  Hist.BidVol>0 = 0 with Hist.Bid > 0 means bid events arrive but without sizes.
// ============================================================================
#region Using declarations
using System;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class EgvTickReplayDiag : Indicator
	{
		private const int	Buckets			= 3;	// 0 = Historical, 1 = Realtime, 2 = any other State
		private const int	TypeSlots		= 16;	// MarketDataType enum has 11 values (0..10); headroom
		private const int	PrintEvery		= 5000;
		private const int	SampleCount		= 5;

		private readonly object	sync		= new object();
		private long[,]		dataByType;			// [bucket, (int)MarketDataType]
		private long[]		bidVolPos;			// Bid events with Volume > 0
		private long[]		bidVolNonPos;		// Bid events with Volume <= 0
		private long[]		askVolPos;
		private long[]		askVolNonPos;
		private long[]		lastVolPos;
		private long[]		typeSwitches;		// consecutive OnMarketData events with different MarketDataType
		private long[]		timeRegressions;	// OnMarketData events whose Time is earlier than the previous one
		private long[]		resets;				// OnMarketData events with IsReset == true
		private long[]		depthCalls;
		private long[]		depthBid;
		private long[]		depthAsk;
		private long		totalEvents;
		private int			samplesPrinted;
		private int			prevType;
		private DateTime	prevTime;
		private bool		active;
		private bool		realtimePrinted;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "Diagnostic only: counts OnMarketData events by MarketDataType and State, Bid/Ask "
											+ "events with Volume > 0, and OnMarketDepth calls per State; prints 'EGV|' lines.";
				Name						= "EgvTickReplayDiag";
				Calculate					= Calculate.OnEachTick;
				IsOverlay					= true;
				DisplayInDataBox			= false;
				PaintPriceMarkers			= false;
				IsSuspendedWhileInactive	= false;
			}
			else if (State == State.DataLoaded)
			{
				lock (sync)
				{
					dataByType		= new long[Buckets, TypeSlots];
					bidVolPos		= new long[Buckets];
					bidVolNonPos	= new long[Buckets];
					askVolPos		= new long[Buckets];
					askVolNonPos	= new long[Buckets];
					lastVolPos		= new long[Buckets];
					typeSwitches	= new long[Buckets];
					timeRegressions	= new long[Buckets];
					resets			= new long[Buckets];
					depthCalls		= new long[Buckets];
					depthBid		= new long[Buckets];
					depthAsk		= new long[Buckets];
					totalEvents		= 0;
					samplesPrinted	= 0;
					prevType		= -1;
					prevTime		= DateTime.MinValue;
					realtimePrinted	= false;
					active			= true;
				}
				Print(string.Format("EGV|HEADER|instrument={0}|period={1}|IsTickReplay={2}|IsInReplayMode={3}|bars={4}",
					Instrument != null ? Instrument.FullName : "?",
					BarsPeriod != null ? BarsPeriod.ToString() : "?",
					Bars != null && Bars.IsTickReplay,
					Bars != null && Bars.IsInReplayMode,
					Bars != null ? Bars.Count : -1));
			}
			else if (State == State.Realtime)
			{
				if (active && !realtimePrinted)
				{
					realtimePrinted = true;
					PrintSummary("REALTIME_TRANSITION");
				}
			}
			else if (State == State.Terminated)
			{
				if (active)
				{
					PrintSummary("TERMINATED");
					active = false;
				}
			}
		}

		protected override void OnBarUpdate() { }

		protected override void OnMarketData(MarketDataEventArgs e)
		{
			if (!active || e == null)
				return;
			bool doPrint = false;
			string sample = null;
			lock (sync)
			{
				int b		= Bucket();
				int t		= (int)e.MarketDataType;
				int slot	= (t >= 0 && t < TypeSlots) ? t : TypeSlots - 1;
				dataByType[b, slot]++;

				if (e.MarketDataType == MarketDataType.Bid)
				{
					if (e.Volume > 0) bidVolPos[b]++; else bidVolNonPos[b]++;
				}
				else if (e.MarketDataType == MarketDataType.Ask)
				{
					if (e.Volume > 0) askVolPos[b]++; else askVolNonPos[b]++;
				}
				else if (e.MarketDataType == MarketDataType.Last)
				{
					if (e.Volume > 0) lastVolPos[b]++;
				}

				if (e.IsReset)
					resets[b]++;
				if (prevType >= 0 && prevType != t)
					typeSwitches[b]++;
				if (prevTime != DateTime.MinValue && e.Time < prevTime)
					timeRegressions[b]++;
				prevType = t;
				prevTime = e.Time;

				if (b == 0 && samplesPrinted < SampleCount
					&& (e.MarketDataType == MarketDataType.Bid || e.MarketDataType == MarketDataType.Ask))
				{
					samplesPrinted++;
					sample = string.Format("EGV|SAMPLE|hist#{0}|type={1}|price={2}|volume={3}|time={4:yyyy-MM-dd HH:mm:ss.fff}|bid={5}|ask={6}",
						samplesPrinted, e.MarketDataType, e.Price, e.Volume, e.Time, e.Bid, e.Ask);
				}

				totalEvents++;
				doPrint = totalEvents % PrintEvery == 0;
			}
			if (sample != null)
				Print(sample);
			if (doPrint)
				PrintSummary("EVERY_" + PrintEvery);
		}

		protected override void OnMarketDepth(MarketDepthEventArgs e)
		{
			if (!active || e == null)
				return;
			bool doPrint = false;
			lock (sync)
			{
				int b = Bucket();
				depthCalls[b]++;
				if (e.MarketDataType == MarketDataType.Bid) depthBid[b]++;
				else if (e.MarketDataType == MarketDataType.Ask) depthAsk[b]++;
				totalEvents++;
				doPrint = totalEvents % PrintEvery == 0;
			}
			if (doPrint)
				PrintSummary("EVERY_" + PrintEvery);
		}

		private int Bucket()
		{
			if (State == State.Historical)	return 0;
			if (State == State.Realtime)	return 1;
			return 2;
		}

		private void PrintSummary(string reason)
		{
			string line;
			lock (sync)
			{
				if (dataByType == null)
					return;
				StringBuilder sb = new StringBuilder(512);
				sb.Append("EGV|SUMMARY|").Append(reason).Append("|state=").Append(State).Append("|total=").Append(totalEvents);
				string[] names = { "Hist", "RT", "Other" };
				for (int b = 0; b < Buckets; b++)
				{
					sb.Append('|').Append(names[b]).Append(':');
					sb.Append(" Ask=").Append(dataByType[b, (int)MarketDataType.Ask]);
					sb.Append(" Bid=").Append(dataByType[b, (int)MarketDataType.Bid]);
					sb.Append(" Last=").Append(dataByType[b, (int)MarketDataType.Last]);
					long otherTypes = 0;
					for (int s = 0; s < TypeSlots; s++)
						if (s != (int)MarketDataType.Ask && s != (int)MarketDataType.Bid && s != (int)MarketDataType.Last)
							otherTypes += dataByType[b, s];
					sb.Append(" OtherTypes=").Append(otherTypes);
					sb.Append(" BidVol>0=").Append(bidVolPos[b]).Append(" BidVol<=0=").Append(bidVolNonPos[b]);
					sb.Append(" AskVol>0=").Append(askVolPos[b]).Append(" AskVol<=0=").Append(askVolNonPos[b]);
					sb.Append(" LastVol>0=").Append(lastVolPos[b]);
					sb.Append(" TypeSwitches=").Append(typeSwitches[b]);
					sb.Append(" TimeRegressions=").Append(timeRegressions[b]);
					sb.Append(" Resets=").Append(resets[b]);
					sb.Append(" Depth=").Append(depthCalls[b]);
					sb.Append(" DepthBid=").Append(depthBid[b]).Append(" DepthAsk=").Append(depthAsk[b]);
				}
				line = sb.ToString();
			}
			Print(line);
		}
	}
}
