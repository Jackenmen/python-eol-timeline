#!/usr/bin/env python
# vim:fileencoding=utf-8
# (c) 2021 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import argparse
import collections
import itertools
import sys
import toml


PROLOGUE = """
<html>
  <head>
    <meta charset="utf-8"/>
    <title>{title}</title>
  </head>
  <body>
    <script type="text/javascript"
            src="https://www.gstatic.com/charts/loader.js">
    </script>

    <script type="text/javascript">
      google.charts.load("current", {packages:["timeline"]});
      google.charts.setOnLoadCallback(drawChart);
      function drawChart() {

        var container = document.getElementById('timeline');
        var chart = new google.visualization.Timeline(container);
        var dataTable = new google.visualization.DataTable();
        dataTable.addColumn({ type: 'string', id: 'Row' });
        dataTable.addColumn({ type: 'string', id: 'State' });
        dataTable.addColumn({ type: 'date', id: 'Start' });
        dataTable.addColumn({ type: 'date', id: 'End' });
        dataTable.addRows([
"""

EPILOGUE = """
        ]);

        var options = {
          avoidOverlappingGridLines: false
        };

        chart.draw(dataTable, options);
      }
    </script>
    <div id="timeline" style="height: 100%"></div>
  </body>
</html>
"""


def jsdate(dt):
    return f"{dt.year}, {dt.month - 1}, {dt.day}"


def print_row(row_label, bars, f):
    prev = None
    for label, start_date in bars:
        if prev is not None:
            print(
                f"          [ {row_label!r}, {prev[0]!r}, "
                f"new Date({jsdate(prev[1])}), "
                f"new Date({jsdate(start_date)}) ],",
                file=f,
            )
        prev = (label, start_date)


def version_key(version):
    return tuple(int(x) for x in version.split("."))


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "toml",
        type=argparse.FileType(encoding="utf-8"),
        help="Input TOML file",
    )
    argp.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w", encoding="utf-8"),
        required=True,
        help="Output HTML file",
    )
    args = argp.parse_args()

    data = toml.load(args.toml)
    args.toml.close()

    with args.output as f:
        print(PROLOGUE.replace("{title}", "Python release timeline"), file=f)

        max_eol = None
        all_rows = collections.defaultdict(list)
        versions = frozenset(itertools.chain.from_iterable(data.values()))
        for version in sorted(versions, key=version_key):
            vdata = data.get("upstream", {}).get(version)
            if vdata is not None:
                bars = []
                if "dev" in vdata:
                    bars.append(("dev", vdata["dev"]))
                bars.extend(
                    [
                        ("\N{GREEK SMALL LETTER ALPHA}", vdata["alpha1"]),
                        ("\N{GREEK SMALL LETTER BETA}", vdata["beta1"]),
                        ("rc", vdata["rc1"]),
                        ("stable", vdata["final"]),
                    ]
                )
                if "last-bugfix" in vdata:
                    bars.append(("security", vdata["last-bugfix"]))
                if "eol" in vdata and vdata["eol"] != vdata["last-bugfix"]:
                    bars.append(("eol", vdata["eol"]))
                if "eol" in vdata:
                    if max_eol is None:
                        max_eol = bars[-1][1]
                    else:
                        max_eol = max(max_eol, bars[-1][1])
                else:
                    assert max_eol is not None
                    bars.append(("future", max_eol))
                all_rows[version].append((version, bars))

        for version in sorted(versions, key=version_key):
            for label, bars in all_rows[version]:
                print_row(label, bars, f)

        print(EPILOGUE, file=f)


if __name__ == "__main__":
    sys.exit(main())
