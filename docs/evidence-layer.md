# Deterministic evidence access

Register output once, then inspect deterministic summaries and request bounded original lines when needed. Registration stores a path and SHA-256 reference; stdin is saved privately under the data directory. Every summary and fetch recomputes the hash. Changed sources return `stale_source`; missing sources return `source_unavailable`.

Summaries distinguish detected totals from displayed details. `counts` contains only counts for recognized patterns, `detection_scope` names those patterns, and `detection_notes` describes the limits. An undetected test count is `null`. Log counts are matches of recognized ERROR/WARN header patterns only; zero matches does not establish absence. Unrecognized error formats may go undetected.

Status is `fail` when failed or error test counts are positive, an ERROR header pattern is found, or a build failure marker (`BUILD FAILURE` or `status=FAIL`) appears. Status is `pass` only when `BUILD SUCCESS` or test totals are present and failed, errors, and log_errors are all explicitly zero. Otherwise status is `unknown`. `recovery` identifies the source and a fetch command for omitted evidence.

Fetch supports inclusive 1-based `N:M` ranges (at most 200 requested lines), error events (20 maximum), or pattern matches (50 maximum), with bounded context and a 32 KB response ceiling. Over-cap requests fail explicitly. When a line range runs past EOF, `truncated.lines` is true. Error and pattern fetches report `total_errors_in_source` or `total_matches_in_source`; `truncated.lines` is true when fewer matching events were returned than exist in the source, including when zero events are shown. Context lines do not change those source totals.

Example transcript (identifiers shortened):

```text
$ ldf source register build-output.txt
{"ref_id":"a1b2c3d4e5f6","sha256":"…","bytes":840,"line_count":12,...}
$ ldf source summarize a1b2c3d4e5f6
{"status":"fail","counts":{"tests_total":8,"passed":7,"failed":1,"errors":0,"skipped":0,"log_errors":1,"log_warns":0},"detection_scope":"last Maven surefire totals line; ERROR/WARN header patterns run over the whole file","detection_notes":"Log counts are matches of recognized ERROR/WARN header patterns only; 0 matches does not establish absence.","first_failure":{"name":"test failed","line":9},"display":{"shown_event_count":1,"total_event_count":1,"complete":true},"recovery":{"ref_id":"a1b2c3d4e5f6","fetch_hint":"ldf source fetch a1b2c3d4e5f6 --errors all"},"source":{"sha256":"…","line_count":12,"bytes":840}}
$ ldf source fetch a1b2c3d4e5f6 --lines 8:10
{"ref_id":"a1b2c3d4e5f6","lines":[{"line":8,"text":"..."}],"truncated":{"lines":true,"bytes":false}}
```
