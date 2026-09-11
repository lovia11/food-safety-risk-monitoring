# Real Collector Contract Fixtures

These small JSON files preserve only the fields needed by the offline collector
regression tests. Their shapes were derived from the historical real run
`20260817T181659_batch`, then minimized and sanitized: they contain no account,
session, cookie, local absolute path, product URL, or personal information.

The saved search-page input remains the tracked
`manual_input/taobao_search.html`. Tests must not read `output/`, `archive/`, or
an external `D:\毕业设计\output` directory.

These fixtures verify content-origin attribution, recommendation-area exclusion,
and supported batch-state values. They are test inputs, not product examples or
current operational coverage evidence.
