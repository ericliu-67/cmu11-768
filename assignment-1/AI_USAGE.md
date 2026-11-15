# AI usage disclosure

This file records assistance visible in this workspace session. Any earlier AI use must be added by the author before a course submission.

- Codex inspected the assignment and existing student implementations, helped configure Modal and the DeepSeek endpoint, and repaired three defects in context compaction: a method/docstring indentation error, a misspelled task attribute, and the transcript-renderer method invocation. Codex ran offline tests, orchestrated live agent runs and fresh-sandbox patch replay, inspected trajectories, and wrote the token-usage analysis and evaluation summary.
- DeepSeek official API model `deepseek-flash` (documented as DeepSeek-V4.1-Flash-1017 at run time) powered the assignment CodeAgent. It generated the chess-app repair and the Django repairs through the assignment's sandbox tools. It also generated working-memory summaries for the compacted run. Both Django trajectories and their patches are retained.
- Web browsing was used to check official provider documentation. Shell/Python tools were used to run tests and compute metrics from recorded API usage. No instructor/private tests were available.
- Existing modifications to `base.py` and `code_agent.py` predated this evaluation session; this disclosure does not establish their authorship.
