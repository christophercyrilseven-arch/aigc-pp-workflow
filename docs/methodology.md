# Worldbuilding Novel Methodology

This project packages a reusable creative workflow for turning a compact world
concept into a finished short novel and a downstream film production plan.

The method is intentionally operational. It is not a prompt collection and it
does not depend on one private model, one private machine, or one fixed cloud
vendor. Each step produces files that can be inspected, validated, repaired, and
reused by another tool.

## 1. World Rules Before Plot

A story world starts with constraints, not decoration.

Every run should extract:

- governing rule: what the world makes possible or impossible
- visible cost: what a character loses when they use or violate the rule
- institution: who benefits from preserving the rule
- forbidden pressure point: what must not be discovered, opened, crossed, or remembered
- sensory identity: materials, light, sound, weather, and tools that make the world concrete

The engine writes this layer to `01_world/` so later stages do not invent a new
world every time.

## 2. Character Choice With Cost

The protagonist must make at least one active choice that changes the state of
the world or their relationship to it.

The workflow rejects story fragments where the lead only observes, waits, or is
carried by events. A valid short novel needs:

- desire: what the character is trying to obtain or protect
- fear: what they avoid admitting
- agency: the irreversible choice they make
- cost: the personal, social, physical, or moral price of that choice
- trace: what remains different after the ending

## 3. Scene Pressure Ladder

Scenes should not be interchangeable. Each scene must change at least one axis:

- knowledge
- danger
- relationship
- status
- physical location
- moral obligation

The novel expert pack favors a compact pressure ladder:

1. arrival under constraint
2. discovery that changes the rules
3. alliance or conflict with a cost
4. institutional pressure
5. final choice and consequence

## 4. Complete Novel, Not Sample Text

The workflow targets a finished short novel around 2,000 Chinese characters.

The QC layer fails outputs that look like:

- outlines
- teaser openings
- chapter previews
- "sample" language
- disconnected fragments
- endings that only promise the real story later

If the model returns weak or incomplete prose, the pipeline can apply limited
repair and still produces a deterministic offline fallback for tests and demos.

## 5. Continuity State

Continuity is treated as data, not memory.

The workflow keeps stable references for:

- character IDs and visual identity
- scenes and materials
- important props
- storyboard shot IDs
- asset prompts
- shot prompts
- QC findings

This makes the same package usable by writing tools, storyboard tools, image
generation tools, video generation tools, and reviewers.

## 6. Film Translation Rules

The film expert pack converts prose into production units instead of generic
visual descriptions.

Every shot should separate:

- start frame
- middle frame
- end frame
- subject movement
- camera movement
- lens or shot size
- lighting motivation
- asset references
- negative prompt constraints

This separation prevents common AIGC failures where character motion, camera
motion, and continuity are collapsed into one vague sentence.

## 7. QC Creates Repair Tasks

The core rule is simple: checks must live in the workflow, not only in a human
reviewer's memory.

A useful QC report should say:

- what failed
- where it failed
- why it matters
- whether automatic repair was attempted
- which artifact should be edited next

The first version implements focused checks for complete-novel delivery,
storyboard structure, shot prompt fields, artifact presence, and path safety.

## 8. Provider-Neutral Execution

Users can run the same methodology with:

- the offline fake provider for tests and demos
- an OpenAI-compatible API endpoint
- an Ollama-compatible local model endpoint
- future custom providers

The expert packs remain editable text and YAML files so teams can version their
own writing and film standards without changing engine code.

