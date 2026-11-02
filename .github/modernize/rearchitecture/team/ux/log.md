## [t5] Specified dashboard and replay interactions
- Codebase/domain discoveries: t3 provides explicit live/replay API scope and `run_id`; replay state is passive and has no UI start endpoint. Historical comparison is fixed to live scope. The local acceptance translation for TC-09/10 is API loss/recovery, not ngrok.
- Wrong assumptions and corrections: the original product docs mention Netlify/ngrok; the current local MVP explicitly excludes public hosting, so the UI reports API availability without a tunnel-specific status.
- Debugging dead-ends and what actually worked: context.md, decisions.md, and a pre-existing UX log were absent; upstream t2/t3 plus the product specs supplied the handoff contract.
- Techniques/patterns worth reusing: distinguish global replay-run status from the user-selected dataset scope; always carry the same structured filter snapshot across map and analytic queries; maintain map/table selection parity.
- Learnings consumed: []
