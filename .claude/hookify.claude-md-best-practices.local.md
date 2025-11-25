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

🚫 BLOCKED: CLAUDE.md must be compact (max 60 lines).
Use tables for rules/locations. Sacrifice grammar for brevity. No verbose explanations.
