---
name: claude-md-best-practices
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: CLAUDE\.md$
  - field: new_text
    operator: regex_match
    pattern: (?s).{3000,}
action: warn
---

CLAUDE.md: Keep compact (max 60 lines), use tables for rules/locations, sacrifice grammar for brevity. No verbose explanations or long code samples.
