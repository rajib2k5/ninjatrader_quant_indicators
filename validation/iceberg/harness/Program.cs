// IcebergHarness - feeds a spec section-1 event stream CSV through IcebergEngine and prints every record.
// Usage: IcebergHarness.exe STREAM.csv [--hidden-ratio X] [--min-refills N] [--min-volume N] [--min-refill-size N]
// stdout: one section-6 record per line, in emission order. stderr: "unclassified=<n>".
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using NinjaTrader.NinjaScript.Indicators.QuantIndicators.Engines;

namespace IcebergHarnessApp
{
	public static class Program
	{
		private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

		private static double Num(string s)
		{
			s = s.Trim();
			return s.Length == 0 ? double.NaN : double.Parse(s, NumberStyles.Float, Inv);
		}

		private static long Int(string s)
		{
			s = s.Trim();
			long v;
			if (long.TryParse(s, NumberStyles.Integer, Inv, out v))
				return v;
			return (long)Math.Round(double.Parse(s, NumberStyles.Float, Inv));
		}

		public static int Main(string[] args)
		{
			string path = null;
			double hiddenRatio = 2.0;
			int minRefills = 2;
			long minVolume = 20, minRefillSize = 1;
			for (int i = 0; i < args.Length; i++)
			{
				string a = args[i];
				if (a == "--hidden-ratio") hiddenRatio = double.Parse(args[++i], NumberStyles.Float, Inv);
				else if (a == "--min-refills") minRefills = int.Parse(args[++i], Inv);
				else if (a == "--min-volume") minVolume = long.Parse(args[++i], Inv);
				else if (a == "--min-refill-size") minRefillSize = long.Parse(args[++i], Inv);
				else if (path == null) path = a;
				else { Console.Error.WriteLine("unexpected argument: " + a); return 2; }
			}
			if (path == null)
			{
				Console.Error.WriteLine("usage: IcebergHarness STREAM.csv [--hidden-ratio X] [--min-refills N] [--min-volume N] [--min-refill-size N]");
				return 2;
			}

			IcebergEngine engine = new IcebergEngine(hiddenRatio, minRefills, minVolume, minRefillSize);
			bool header = true;
			int lineNo = 0;
			foreach (string raw in File.ReadLines(path))
			{
				lineNo++;
				string line = raw.Trim();
				if (line.Length == 0)
					continue;
				if (header)
				{
					header = false;
					if (line.StartsWith("seq", StringComparison.OrdinalIgnoreCase))
						continue;
				}

				string[] f = line.Split(',');
				if (f.Length < 2)
				{
					Console.Error.WriteLine("line " + lineNo + ": too few fields");
					return 3;
				}
				string[] g = new string[6];
				for (int k = 0; k < 6; k++)
					g[k] = k < f.Length ? f[k] : "";

				long seq = Int(g[0]);
				string type = g[1].Trim();
				List<string> recs;
				switch (type)
				{
					case "B": recs = engine.OnBid(seq, Num(g[2]), Int(g[3])); break;
					case "A": recs = engine.OnAsk(seq, Num(g[2]), Int(g[3])); break;
					case "T": recs = engine.OnTrade(seq, Num(g[2]), Int(g[3]), Num(g[4]), Num(g[5])); break;
					case "R": recs = engine.OnReset(seq); break;
					default:
						Console.Error.WriteLine("line " + lineNo + ": unknown type '" + type + "'");
						return 3;
				}
				foreach (string r in recs)
					Console.WriteLine(r);
			}
			Console.Error.WriteLine("unclassified=" + engine.Unclassified.ToString(Inv));
			return 0;
		}
	}
}
