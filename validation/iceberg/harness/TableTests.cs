// TableTests - tests for the QI_28 table panel's NT-free parts (validation/iceberg/table-spec.md §2-§3, claims P1, P2).
// Compiled together with indicators/QI_28_IcebergDetector.cs into one exe (build_tests.sh), so `internal` record
// setters are reachable. Exit code 0 = all passed; every failure is printed.
// Written before the implementation (TDD): every expected value below comes from the spec, not from the code.
using System;
using System.Collections.Generic;
using System.Globalization;
using NinjaTrader.NinjaScript.Indicators.QuantIndicators.Engines;

namespace IcebergTableTests
{
	public static class Program
	{
		private static int failures, passes;
		private static readonly DateTime T0 = new DateTime(2026, 4, 26, 9, 30, 0);

		private static void Check(bool ok, string what)
		{
			if (ok) passes++;
			else { failures++; Console.WriteLine("FAIL: " + what); }
		}

		private static void Eq<T>(T expected, T got, string what)
		{
			Check(EqualityComparer<T>.Default.Equals(expected, got), what + " expected <" + expected + "> got <" + got + ">");
		}

		private static string P(double p) { return p.ToString("F2", CultureInfo.InvariantCulture); }

		private static IcebergRecord Flag(string side, double price, long startSeq, long traded, long shown, int refills, double conf)
		{
			return new IcebergRecord { Kind = "FLAG", Side = side, Price = price, Seq = startSeq + 5, StartSeq = startSeq,
				Traded = traded, ShownMax = shown, HiddenEst = traded - shown, Refills = refills, Conf = conf };
		}

		private static IcebergRecord Final(string side, double price, long startSeq, long traded, long shown, int refills,
			double conf, string reason)
		{
			return new IcebergRecord { Kind = "FINAL", Side = side, Price = price, Seq = startSeq + 9, StartSeq = startSeq,
				Traded = traded, ShownMax = shown, HiddenEst = traded - shown, Refills = refills, Conf = conf, Reason = reason };
		}

		// ---- P1: table model -------------------------------------------------------------------
		private static void FlagAppendsActiveRow()
		{
			var t = new IcebergTable();
			t.Apply(Flag("bid", 7012.25, 1, 25, 10, 2, 0.45), T0);
			Eq(1, t.Count, "count after one FLAG");
			IcebergTableRow r = t.Rows(10)[0];
			Eq(1, r.Id, "first id");
			Eq("bid", r.Side, "side");
			Eq(7012.25, r.Price, "price");
			Eq(15L, r.Hidden, "hidden = traded - shown");
			Eq(25L, r.Traded, "traded");
			Eq(10L, r.Shown, "shown");
			Eq(2, r.Refills, "refills");
			Eq("active", r.Status, "status");
			Check(r.Ended == null, "ended is none while active");
			Eq(T0, r.Detected, "detected time");
		}

		private static void FinalUpdatesMatchingRow()
		{
			var t = new IcebergTable();
			t.Apply(Flag("bid", 7012.25, 1, 25, 10, 2, 0.45), T0);
			t.Apply(Final("bid", 7012.25, 1, 35, 12, 3, 0.6417, "broken"), T0.AddSeconds(42));
			Eq(1, t.Count, "FINAL does not add a row");
			IcebergTableRow r = t.Rows(10)[0];
			Eq("broken", r.Status, "status from reason");
			Eq(23L, r.Hidden, "final hidden");
			Eq(35L, r.Traded, "final traded");
			Eq(12L, r.Shown, "final shown");
			Eq(3, r.Refills, "final refills");
			Check(r.Ended == T0.AddSeconds(42), "ended time");
			Eq(T0, r.Detected, "detected time unchanged by FINAL");
		}

		private static void FinalWithoutMatchingRowDoesNothing()
		{
			var t = new IcebergTable();
			t.Apply(Flag("bid", 7012.25, 1, 25, 10, 2, 0.45), T0);
			t.Apply(Final("ask", 7012.25, 1, 35, 12, 3, 0.6, "held"), T0.AddSeconds(1));      // other side
			t.Apply(Final("bid", 7012.25, 99, 35, 12, 3, 0.6, "held"), T0.AddSeconds(2));     // other level
			Eq(1, t.Count, "no row added");
			Eq("active", t.Rows(10)[0].Status, "row untouched");
			t.Apply(Final("bid", 7012.25, 1, 35, 12, 3, 0.6, "held"), T0.AddSeconds(3));
			t.Apply(Final("bid", 7012.25, 1, 99, 12, 3, 0.9, "broken"), T0.AddSeconds(4));    // already final
			Eq("held", t.Rows(10)[0].Status, "a finished row is not updated again");
			Eq(35L, t.Rows(10)[0].Traded, "a finished row keeps its final values");
		}

		private static void RowsNewestFirstWithIdTieBreak()
		{
			var t = new IcebergTable();
			t.Apply(Flag("bid", 5000.00, 1, 30, 10, 2, 0.5), T0);
			t.Apply(Flag("ask", 5001.00, 2, 30, 10, 2, 0.5), T0.AddSeconds(30));
			t.Apply(Flag("bid", 4999.75, 3, 30, 10, 2, 0.5), T0.AddSeconds(10));
			t.Apply(Flag("ask", 5002.00, 4, 30, 10, 2, 0.5), T0.AddSeconds(30));   // same time as id 2
			List<IcebergTableRow> rows = t.Rows(10);
			Eq(4, rows.Count, "all rows");
			Eq(4, rows[0].Id, "newest first; tie broken by higher id");
			Eq(2, rows[1].Id, "second");
			Eq(3, rows[2].Id, "third");
			Eq(1, rows[3].Id, "oldest last");
			List<IcebergTableRow> two = t.Rows(2);
			Eq(2, two.Count, "Rows(max) truncates");
			Eq(4, two[0].Id, "truncation keeps the newest");
			Eq(0, t.Rows(0).Count, "Rows(0) is empty");
		}

		private static void CapacityDropsOldest()
		{
			var t = new IcebergTable();
			for (int i = 0; i < IcebergTable.Capacity + 3; i++)
				t.Apply(Flag("bid", 5000 + i, i + 1, 30, 10, 2, 0.5), T0.AddSeconds(i));
			Eq(500, IcebergTable.Capacity, "capacity constant");
			Eq(IcebergTable.Capacity, t.Count, "count capped");
			List<IcebergTableRow> all = t.Rows(int.MaxValue);
			Eq(IcebergTable.Capacity + 3, all[0].Id, "newest kept");
			Eq(4, all[all.Count - 1].Id, "the three oldest dropped");
		}

		private static void HeaderAndCells()
		{
			string[] h = IcebergTable.Header;
			Eq("#|Detected|Side|Price|Hidden|Traded|Shown|Refills|Conf|Status|Ended", string.Join("|", h), "header");
			bool[] right = IcebergTable.RightAligned;
			Eq("1001111110" + "0", string.Join("", Array.ConvertAll(right, b => b ? "1" : "0")), "alignment");

			var t = new IcebergTable();
			t.Apply(Flag("ask", 7013.0, 2, 21, 6, 3, 0.6451), new DateTime(2026, 4, 26, 9, 5, 7));
			string[] c = IcebergTable.Cells(t.Rows(1)[0], P);
			Eq("#1|04-26 09:05:07|ask|7013.00|~15|21|6|3|65%|active|-", string.Join("|", c), "active cells (0.6451 -> 65%)");

			t.Apply(Final("ask", 7013.0, 2, 24, 8, 4, 0.9349, "held"), new DateTime(2026, 4, 26, 9, 6, 1));
			c = IcebergTable.Cells(t.Rows(1)[0], P);
			Eq("#1|04-26 09:05:07|ask|7013.00|~16|24|8|4|93%|held|09:06:01", string.Join("|", c), "final cells, same date");

			var u = new IcebergTable();
			u.Apply(Flag("bid", 5000.5, 1, 30, 10, 2, 1.0), new DateTime(2026, 4, 26, 23, 59, 59));
			u.Apply(Final("bid", 5000.5, 1, 30, 10, 2, 1.0, "open"), new DateTime(2026, 4, 27, 0, 0, 3));
			c = IcebergTable.Cells(u.Rows(1)[0], P);
			Eq("04-27 00:00:03", c[10], "ended on another date shows the date");
			Eq("100%", c[8], "conf 1.0");

			var m = new IcebergTable();       // 0.125 x 100 = 12.5 exactly in binary: away from zero -> 13, not 12
			m.Apply(Flag("bid", 5000.0, 1, 30, 10, 2, 0.125), T0);
			Eq("13%", IcebergTable.Cells(m.Rows(1)[0], P)[8], "conf midpoint rounds away from zero");
		}

		private static void BoxTexts()
		{
			Eq("QI 28 Iceberg levels (probable) - newest first", IcebergTable.Title, "title");
			Eq("No probable iceberg levels yet.", IcebergTable.EmptyText, "empty text");
			Eq("+3 older not shown", IcebergTable.Footer(3), "footer");
		}


		private static void ApplyReturnsRowId()
		{
			var t = new IcebergTable();
			Eq(1, t.Apply(Flag("bid", 5000.0, 1, 30, 10, 2, 0.5), T0), "FLAG returns the new row id");
			Eq(2, t.Apply(Flag("ask", 5001.0, 2, 30, 10, 2, 0.5), T0), "second id");
			Eq(1, t.Apply(Final("bid", 5000.0, 1, 30, 10, 2, 0.5, "held"), T0), "FINAL returns the updated row id");
			Eq(0, t.Apply(Final("bid", 5000.0, 7, 30, 10, 2, 0.5, "held"), T0), "FINAL with no row returns 0");
		}

		// ---- P2: placement -----------------------------------------------------------------------
		private static void PlaceCornerWhenFree()
		{
			var panel = new BoxRect(0, 0, 800, 600);
			BoxRect? r = BoxLayout.Place(panel, 300, 100, new List<BoxRect>(), 8, 4);
			Check(r.HasValue, "fits");
			Eq<BoxRect?>(new BoxRect(492, 492, 300, 100), r, "bottom-right corner position");
		}

		private static void PlaceAboveBlocker()
		{
			var panel = new BoxRect(10, 20, 800, 600);   // right 810, bottom 620
			var occ = new List<BoxRect> { new BoxRect(600, 560, 200, 50) };   // top 560, overlaps the corner spot
			BoxRect? r = BoxLayout.Place(panel, 300, 100, occ, 8, 4);
			Check(r.HasValue, "fits above");
			Eq<BoxRect?>(new BoxRect(502, 456, 300, 100), r, "moved up to blocker top - gap - h = 560-4-100");
		}

		private static void TouchingIsNotOverlap()
		{
			var panel = new BoxRect(0, 0, 800, 600);
			// corner spot is x 492..792, y 492..592; a rect ending exactly gap away to the left does not block
			var occ = new List<BoxRect> { new BoxRect(0, 492, 488, 100) };
			BoxRect? r = BoxLayout.Place(panel, 300, 100, occ, 8, 4);
			Eq<BoxRect?>(new BoxRect(492, 492, 300, 100), r, "edge exactly gap away stays at the corner");
		}

		private static void NoRoomReturnsNone()
		{
			var panel = new BoxRect(0, 0, 400, 300);
			Check(!BoxLayout.Place(panel, 385, 50, new List<BoxRect>(), 8, 4).HasValue, "too wide");
			Check(!BoxLayout.Place(panel, 50, 285, new List<BoxRect>(), 8, 4).HasValue, "too tall");
			var occ = new List<BoxRect> { new BoxRect(0, 0, 400, 300) };
			Check(!BoxLayout.Place(panel, 50, 50, occ, 8, 4).HasValue, "fully covered panel");
		}

		private static void PlaceProperties()
		{
			var rng = new Random(20261029);
			int placed = 0;
			for (int k = 0; k < 20000; k++)
			{
				var panel = new BoxRect(rng.Next(0, 50), rng.Next(0, 50), rng.Next(100, 1600), rng.Next(80, 1000));
				double margin = rng.Next(0, 12), gap = rng.Next(0, 8);
				double w = rng.Next(10, 700), h = rng.Next(10, 500);
				var occ = new List<BoxRect>();
				int n = rng.Next(0, 6);
				for (int i = 0; i < n; i++)
					occ.Add(new BoxRect(panel.X + rng.Next(-50, (int)panel.W), panel.Y + rng.Next(-50, (int)panel.H),
						rng.Next(1, 400), rng.Next(1, 200)));
				BoxRect? r1 = BoxLayout.Place(panel, w, h, occ, margin, gap);
				BoxRect? r2 = BoxLayout.Place(panel, w, h, occ, margin, gap);
				if (!Equals(r1, r2)) { Check(false, "deterministic #" + k); continue; }
				if (!r1.HasValue) continue;
				placed++;
				BoxRect r = r1.Value;
				bool inside = r.X >= panel.X + margin - 1e-9 && r.Y >= panel.Y + margin - 1e-9
					&& r.Right <= panel.Right - margin + 1e-9 && r.Bottom <= panel.Bottom - margin + 1e-9;
				if (!inside) { Check(false, "inside panel #" + k + " " + r); continue; }
				if (Math.Abs(r.Right - (panel.Right - margin)) > 1e-9) { Check(false, "right-aligned #" + k); continue; }
				if (Math.Abs(r.W - w) > 1e-9 || Math.Abs(r.H - h) > 1e-9) { Check(false, "size kept #" + k); continue; }
				bool clash = false;
				foreach (BoxRect o in occ)
					if (r.Inflate(gap).Overlaps(o)) clash = true;
				if (clash) { Check(false, "no overlap #" + k + " " + r); continue; }
				var corner = new BoxRect(panel.Right - margin - w, panel.Bottom - margin - h, w, h);
				bool cornerFree = true;
				foreach (BoxRect o in occ)
					if (corner.Inflate(gap).Overlaps(o)) cornerFree = false;
				if (cornerFree && !r.Equals(corner)) { Check(false, "free corner used #" + k); continue; }
				if (r.Y > corner.Y + 1e-9) { Check(false, "never below the corner #" + k); continue; }
				passes++;
			}
			Check(placed > 5000, "property loop placed enough boxes (" + placed + ")");
		}

		private static void OverlapIsStrict()
		{
			var a = new BoxRect(0, 0, 10, 10);
			Check(!a.Overlaps(new BoxRect(10, 0, 5, 5)), "touching right edge");
			Check(!a.Overlaps(new BoxRect(0, 10, 5, 5)), "touching bottom edge");
			Check(a.Overlaps(new BoxRect(9.5, 9.5, 5, 5)), "corner overlap");
			Check(a.Overlaps(new BoxRect(2, 2, 1, 1)), "contained");
			Eq(new BoxRect(-2, -2, 14, 14), a.Inflate(2), "inflate");
		}


		// ---- P2b: reserved areas (table-spec.md section 4, amendment A2) --------------------------
		private static void TextFixedReserveGeometry()
		{
			var panel = new BoxRect(100, 50, 1000, 600);   // R 1100, B 650; text 200 x 20
			Eq<BoxRect?>(new BoxRect(884.5, 614.5, 210, 30), PanelReserve.ForTextFixed("BottomRight", panel, 200, 20, 0), "BottomRight");
			Eq<BoxRect?>(new BoxRect(105.5, 604, 210, 40.5), PanelReserve.ForTextFixed("BottomLeft", panel, 200, 20, 0), "BottomLeft (x2 copyright room)");
			Eq<BoxRect?>(new BoxRect(105.5, 66, 210, 30), PanelReserve.ForTextFixed("TopLeft", panel, 200, 20, 0), "TopLeft (+21 label room)");
			Eq<BoxRect?>(new BoxRect(884.5, 55, 210, 62), PanelReserve.ForTextFixed("TopRight", panel, 200, 20, 0), "TopRight (10 .. 42 offset)");
			Eq<BoxRect?>(new BoxRect(495, 335, 210, 30), PanelReserve.ForTextFixed("Center", panel, 200, 20, 0), "Center");
			Eq<BoxRect?>(new BoxRect(884.5, 611.5, 210, 36), PanelReserve.ForTextFixed("BottomRight", panel, 200, 20, -3), "|YPixelOffset| widens both ways");
			Check(!PanelReserve.ForTextFixed("Somewhere", panel, 200, 20, 0).HasValue, "unknown position -> none");
		}

		private static void FixedStrips()
		{
			var panel = new BoxRect(100, 50, 1000, 600);
			List<BoxRect> s = PanelReserve.Strips(panel, false);
			Eq(2, s.Count, "top + copyright strips");
			Eq(new BoxRect(100, 50, 1000, 48), s[0], "top strip");
			Eq(new BoxRect(100, 626, 360, 24), s[1], "copyright strip (360 cap)");
			List<BoxRect> o = PanelReserve.Strips(panel, true);
			Eq(3, o.Count, "plus overlay y-axis strip");
			Eq(new BoxRect(1020, 50, 80, 600), o[2], "overlay y-axis strip");
			Eq(new BoxRect(0, 276, 250, 24), PanelReserve.Strips(new BoxRect(0, 0, 500, 300), false)[1], "copyright strip W/2 on narrow panel");
		}

		private static void BoxAvoidsBottomRightTextFixed()
		{
			// end to end: a BottomRight TextFixed (e.g. another script's note) pushes the table above it
			var panel = new BoxRect(0, 0, 1000, 600);
			var occ = PanelReserve.Strips(panel, false);
			occ.Add(PanelReserve.ForTextFixed("BottomRight", panel, 150, 16, 0).Value);   // y 568.5 .. 594.5
			BoxRect? r = BoxLayout.Place(panel, 400, 120, occ, 8, 6);
			Eq<BoxRect?>(new BoxRect(592, 442.5, 400, 120), r, "table sits gap above the TextFixed box (568.5 - 6 - 120)");
		}

		public static int Main()
		{
			FlagAppendsActiveRow();
			FinalUpdatesMatchingRow();
			FinalWithoutMatchingRowDoesNothing();
			RowsNewestFirstWithIdTieBreak();
			CapacityDropsOldest();
			HeaderAndCells();
			BoxTexts();
			ApplyReturnsRowId();
			OverlapIsStrict();
			PlaceCornerWhenFree();
			PlaceAboveBlocker();
			TouchingIsNotOverlap();
			NoRoomReturnsNone();
			PlaceProperties();
			TextFixedReserveGeometry();
			FixedStrips();
			BoxAvoidsBottomRightTextFixed();
			Console.WriteLine("passed=" + passes + " failed=" + failures);
			return failures == 0 ? 0 : 1;
		}
	}
}
