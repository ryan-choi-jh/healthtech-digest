# healthtech-digest

Workspace for the **Healthcare Tech Daily Digest** Claude Code Routine. The
Routine's prompt (saved in the Claude UI) does all the work; this repo is the
workspace it clones. The brief is kept in
[`ROUTINE_PROMPT.md`](./ROUTINE_PROMPT.md) as a backup. Setup:
<https://claude.ai/code/routines>.

`state/seen.json` holds the cross-run dedup state — URLs already surfaced, so
the same item isn't repeated day-to-day. The Routine reads it at the start of
each run and commits the updated file back to `main` at the end. This requires
**Allow unrestricted branch pushes** enabled for this repo in the Routine's
**Permissions** tab.
