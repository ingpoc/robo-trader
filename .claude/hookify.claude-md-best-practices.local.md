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

⚠️ **CLAUDE.md exceeds best practices**

Keep CLAUDE.md files compact (max 60 lines, ~2500 chars). Use tables for rules/locations. Sacrifice grammar for brevity - no verbose explanations or long code samples.

Rationale: Compact CLAUDE.md is easier to remember and update.
