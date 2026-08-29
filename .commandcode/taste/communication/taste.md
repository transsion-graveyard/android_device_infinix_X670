# Communication Preferences

- Lead with the rank-ordered root causes, not background explanation; tag each with a numbered "Cause #N" label. Confidence: 0.9
- When citing a config value, quote the exact file path + line numbers + raw snippet so the user can verify without re-running the investigation. Confidence: 0.95
- Use markdown headers (###) to separate competing hypotheses and "Contributing factor" sections. Confidence: 0.8
- Spell out the chain of reasoning that connects a config value to the observed symptom (e.g. "X expires after 1s → Y free-falls → SF misses frame deadline"). Confidence: 0.85
- Distinguish "established cause" from "contributing factor" / "what I'd verify" / "likely fix direction" — never blend them. Confidence: 0.9
- End with an explicit confirmation question when offering to take the next action (implement a fix, write a plan, etc.) rather than silently proceeding. Confidence: 0.9
- Uses terse, imperative phrasing for requests (e.g. "run adb", "fix it") without politeness framing — respond directly, don't ask for clarification on obvious shorthand. Confidence: 0.85