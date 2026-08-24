# hee-gen-manpages(1)

hee-gen-manpages -- real 0-token man-page generator. Mechanically
extracts each tool's own --help/-h output (or, for shell scripts
without one, its header comment block) into man/<tool>.1.md.
No LLM reasoning per tool -- pure extraction, so this scales to all
42+ tooling/bin/* entries at zero per-tool token cost. Re-run any
time tools change; output is deterministic from the tool's own
--help text, never hand-authored here.

*(no --help/-h output -- generated from the script's own header comment)*
