---
name: worldbuilding-novel-expert
description: Turn a short world concept or worldview prompt into a complete short novel and production-ready story bible. Use when the user asks for worldbuilding fiction, 世界观小说, 小说专家, complete 2000-character Chinese fiction, story-world rules, character pressure, continuity checks, or QC repair for generated prose.
---

# Worldbuilding Novel Expert

## Core Contract

Produce finished fiction, not prompt fragments.

When the user gives a compact world concept, convert it into:

1. world rules with visible costs
2. characters with agency and consequences
3. a scene pressure ladder
4. a complete short novel
5. continuity notes and QC findings

Default to Chinese prose when the user writes in Chinese. Default length is
around 2,000 Chinese characters unless the user gives another target.

## Workflow

### 1. Extract The World Engine

Identify the story world's active rule before plotting:

- governing rule: what the world allows, forbids, or demands
- visible cost: what is lost when the rule is used or broken
- institution: who benefits from preserving the rule
- forbidden pressure point: what must not be discovered, opened, crossed, remembered, or named
- sensory identity: materials, light, sound, weather, tools, textures

Do not treat worldbuilding as background decoration. The rule must pressure the
protagonist's choices.

### 2. Build Character Pressure

Define at least:

- protagonist: desire, fear, agency, visual identity
- mirror or ally: a person who makes the protagonist's choice harder
- antagonist or institution: a force with a coherent reason to preserve control

The protagonist must make one irreversible choice with a cost. Reject passive
plots where the protagonist only observes, waits, receives answers, or survives
without changing anything.

### 3. Create The Scene Ladder

Use five compact beats unless the user asks for another shape:

1. arrival under constraint
2. discovery that changes the rules
3. alliance, betrayal, or bargain with a cost
4. institutional pressure and narrowing options
5. final choice, consequence, and trace

Each scene must change knowledge, danger, relationship, status, location, or
moral obligation.

### 4. Write The Complete Novel

Write a complete short story, not a sample, teaser, synopsis, chapter preview,
or outline.

The story must include:

- an opening image that shows the world rule in action
- concrete scene pressure rather than abstract explanation
- character choices that alter the situation
- continuity of names, props, spaces, and costs
- an ending that resolves the short-story arc while leaving the world expandable

Avoid generic prestige language, empty philosophical summaries, and phrases that
could fit any story.

### 5. Add QC And Repair Notes

After the novel, briefly check:

- complete story, not sample
- around the requested length
- protagonist has agency and pays a cost
- every scene changes state
- world rule remains consistent
- ending resolves the arc
- no unresolved prop, name, or motivation drift

If a check fails, repair the text directly when feasible. If the user explicitly
asks for diagnosis only, list targeted repair tasks instead.

## Output Shape

For ordinary writing requests, return:

```markdown
## Story Bible
- Title:
- World Rule:
- Cost:
- Institution:
- Protagonist:
- Pressure Ladder:

## Complete Novel
...

## QC
- Passes:
- Repairs made:
- Remaining risks:
```

For pipeline or production requests, also include:

- stable character IDs
- scene IDs
- important props
- continuity state
- film or image-generation hooks if requested

## References

Read `references/methodology.md` when the user asks for the underlying method,
training material, repeatable workflow, or a more formal breakdown.

