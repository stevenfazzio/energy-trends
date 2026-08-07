# Hand-entered series

For numbers that exist only in a PDF or a press release. One CSV per series,
one row per observation, with the citation that backs it alongside.

```csv
date,line,value,source,url,note
2024-01-01,Global data centres,415,IEA,https://www.iea.org/reports/...,Electricity 2024, Annex A
```

Required columns: `date`, `line`, `value`, `source`, `url`. `note` is free text.
`line` is the legend label, so several lines share one file. The loader raises
on a row with no URL — if a number cannot be traced to a published release, it
does not belong here.

Read it from a source module with `manual.series("your-file-name")`, which
returns one `Line` per distinct `line` value.

Nothing lives here yet. The two candidates are global data centre consumption
and primary aluminium smelting, neither of which has a free machine-readable
feed; see the "Not here yet" section of the top-level README.
