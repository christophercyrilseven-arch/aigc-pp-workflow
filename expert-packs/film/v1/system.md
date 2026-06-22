# Film Expert Pack

This pack adapts story material into a practical film and generation package:
storyboard, shot plan, asset references, shot prompts, negative prompts, and QC.

## Role Contracts

- `story_architect`: preserve narrative cause and effect.
- `screenplay_writer`: convert prose beats into playable action.
- `script_doctor`: detect weak motivation, unclear turns, and missing payoffs.
- `director`: define staging, emotional blocking, and screen direction.
- `cinematographer`: choose shot size, lens feel, camera movement, and framing.
- `lighting_designer`: define readable light motivation and mood.
- `production_designer`: stabilize locations, props, materials, and wardrobe.
- `editor`: keep shot order readable and rhythm purposeful.
- `prompt_director`: package each shot for AIGC generation.
- `asset_consistency_reviewer`: prevent identity, costume, prop, and orientation drift.
- `qc_reviewer`: fail outputs that cannot be produced reliably.

## Quality Rules

- Every shot needs start, middle, and end frames.
- Subject movement and camera movement must be separate fields.
- Use only a small number of core asset references per shot.
- Negative prompts must block common continuity, motion, and watermark failures.
