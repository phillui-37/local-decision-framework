# Deterministic evidence access

Register output once, then inspect deterministic summaries and request bounded original lines when needed. Registration stores a path and SHA-256 reference; stdin is saved privately under the data directory. Every summary and fetch recomputes the hash. Changed sources return `stale_source`; missing sources return `source_unavailable`.

Summaries distinguish detected totals from displayed details. `counts` contains only counts for recognized patterns, `detection_scope` names those patterns, and `display` gives shown and whole-source event counts separately. An undetected count is `null`; zero means zero matches within the stated detection scope and never proves absence. Error headers are counted, not stack frames. `recovery` identifies the source and a fetch command for omitted evidence.

Fetch supports inclusive 1-based `N:M` ranges (at most 200 lines), error events (20 maximum), or pattern matches (50 maximum), with bounded context and a 32 KB response ceiling. Over-limit requests fail explicitly rather than silently truncating output.

Example transcript (identifiers shortened):

```text
$ ldf source register build-output.txt
{"ref_id":"a1b2c3d4e5f6","sha256":"…","bytes":840,"line_count":12,...}
$ ldf source summarize a1b2c3d4e5f6
{"status":"fail","counts":{"tests_total":8,"passed":7,"failed":1,"errors":0,"skipped":0,"log_errors":1,"log_warns":null},"detection_scope":"last Maven surefire totals line; ERROR/WARN header lines; not stack-trace frames","first_failure":{"name":"test failed","line":9},"display":{"shown_event_count":1,"total_event_count":1,"complete":true},"recovery":{"ref_id":"a1b2c3d4e5f6","fetch_hint":"ldf source fetch a1b2c3d4e5f6 --errors all"},"source":{"sha256":"…","line_count":12,"bytes":840}}
$ ldf source fetch a1b2c3d4e5f6 --lines 8:10
{"ref_id":"a1b2c3d4e5f6","lines":[{"line":8,"text":"..."}],"truncated":{"lines":false,"bytes":false}}
```
