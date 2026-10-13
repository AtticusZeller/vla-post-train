---
name: write-reproduction-spec
description: Create or substantially reorganize a paper-reproduction specification covering method intuition, component definitions, implementation choices, data and training workflows, and experiment-informed decisions. Use for reproduction specs in method directories under docs/; ordinary paper summaries and individual experiment records do not require this workflow.
---

# Write Reproduction Spec

## Purpose

Write a specification that lets a researcher understand the method,
reproduce the selected implementation, and trace the reasons for its choices.

Read applicable documentation rules and existing method documents first.
Inspect the paper, relevant implementation, configurations, and experiment
evidence needed for the requested scope.

Explain method-specific conventions at the depth needed for reproduction.
Keep basic tutorials from review discussions and incidental optimization
suggestions out of the spec unless they belong to the agreed scope.

## Document Structure

### 1. Method Overview

Give a short, intuitive explanation of the method:
what information it uses, what it produces, and how learning improves it.
Add a compact architecture or flow diagram when it helps understanding.

Keep this section brief. Do not require separate problem, architecture,
and training-stage subsections. Leave formulas and configuration details
to the following sections.

### 2. Model Definitions and Implementation Choices

Define shared symbols, dimensions, and indexing conventions first.
Explain mathematical operators used in the document as well.

Keep mathematical definitions at the level of the modeled objects, preserving
their meaning and shape. Describe implementation-only flattening, reshaping,
and concatenation in the implementation explanation.

Organize the rest by component. For each component, explain:
purpose and inputs/outputs -> mathematical definition and objective ->
data representation and transforms -> implementation structure and
rationale -> selected structural parameters.

Include shared transforms once and reference them from each consumer.
Keep layer counts, widths, activations, normalization, initialization,
and related model parameters beside the component they define.

### 3. Data Construction and Training Workflow

Explain how data and model artifacts move through the complete workflow.
Cover preparation, training stages, sample construction, update scheduling,
and the conditions for starting, switching, completing, or resuming stages.

For masks, labels, and supervision targets, explain how collection or data
preparation produces them before explaining how training uses them.

Place optimizer settings, batch sizes, data budgets, and training schedules
beside the workflow they control. Summarize the selected training recipe
without duplicating model-structure tables.

Adapt subsections to the method. Do not impose RLToken-specific concepts
such as intervention, replay, or two-stage training on other methods.

### 4. Experimental Details and Discussion

Explain consequential choices through:
initial question or hypothesis -> alternatives tried -> observations ->
current decision -> remaining uncertainty.

Keep enough evidence to explain the selected specification.
Link full run records instead of copying experiment logs.
Clearly distinguish adopted, retained, inconclusive, and untested options.

Place brief observations, hypotheses, and parameter interpretations beside
the relevant loss or component using Markdown blockquotes (`>`). Label their
status explicitly. Keep cross-component discussion and final decisions in
this section without duplicating those local notes.

## Evidence and Consistency

Distinguish paper requirements, reference-implementation behavior,
local implementation choices, and actual experimental evidence.

Distinguish code defaults, the selected reproduction configuration,
and individual run overrides. Identify their sources.

Check formulas against implementation conventions, including tensor shapes,
reductions, units, masks, transforms, and update timing.
Do not treat current code alone as proof of intended behavior.

Preserve relevant existing rules and examples within the approved scope
when reorganizing a spec, and honor approved deletions. Do not restore
removed sections or recast an erroneous implementation as a design
alternative. Keep the current adopted method clear.
Surface contradictions and unresolved choices rather than silently
resolving them.

## Review

Present the proposed outline before a substantial reorganization.
When the user requires approval before writing, show the concrete proposed
content and wait for approval; outline approval alone does not approve
unseen substantive changes.

Before delivery, check notation, links, configuration provenance,
internal consistency, and preservation of agreed content.
