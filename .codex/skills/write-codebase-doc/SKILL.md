---
name: write-codebase-doc
description: Create or update docs/<method>/codebase.md, the visual map of a method repository - overview diagram, startup entries, annotated file map, module interaction diagrams, and module inputs/outputs. Use whenever the user wants to understand, map, compare, or document how a method's code is organized (training, evaluation, inference, deployment, or robot/sim client entry points; module responsibilities; who calls whom), asks 代码库怎么组织 / 梳理代码结构 / 画模块关系 / 入口在哪, or when a change adds, moves, or renames an entry point, module, config location, or protocol that an existing codebase.md describes. Method rules and formulas belong to write-reproduction-spec; copyable commands belong to cmd.md.
---

# Write Codebase Doc

`docs/<method>/codebase.md` lets a researcher build a mental map of a method repository before deciding
anything about it: what runs where, which file does what, and how the pieces talk. The reader wants to
see the structure, so diagrams, annotated file trees, and tables carry the content. Prose explains only
what a picture cannot, such as why a connection runs one way or a constraint that is not visible in code.

The first version of the reference document, `docs/xense-openpi/codebase.md`, was rejected as too
prose-heavy; the reader asked for five things: modules, files, responsibilities, startup entries, and
module interactions. Every section below serves one of them. Read that document before writing a new one.

## Before Writing

1. Pin the snapshot: the method branch and commit the document describes, by default the branch
   registered in `.gitmodules`. When another branch is also in active use, compare the two and plan a
   location-mapping table.
2. Read the method's README, `AGENTS.md` or `CLAUDE.md`, and its own docs, then the code:
   - each entry script's arguments, what it reads, what it writes, and where its artifacts go;
   - the config system: which config files exist, what resolves them, which entries share them;
   - packages and processes that run elsewhere, such as a robot host, simulator workers, or an
     inference server, and the protocol between them;
   - the actual imports, for every dependency arrow you will draw.
3. Treat the method's own docs as claims to verify against code. Surface contradictions to the user
   instead of silently picking one side.
4. Find the parts that run outside the repository: forks cloned during setup, other repositories,
   firmware or servers on other machines. When they are not available locally, describe them from the
   imports and calls the repository makes into them, and say so in the snapshot line.

## Document Structure

Write in Chinese and keep identifiers, paths, and interface names unchanged, as `docs/AGENTS.md`
requires. Use this order. Drop a section that has nothing to show, and rename parts to fit the method:
a simulation-only method has workers, not a robot host.

0. **Title and one snapshot line**: branch, commit, and what differs between relevant branches.
1. **总图**: one mermaid `flowchart LR`. Use a `subgraph` per machine or process group, entry scripts
   as nodes, artifacts such as datasets and checkpoints as labels on thin arrows, and runtime
   connections as thick arrows (`<==>`). Follow it with a small table of connection types: how each is
   started, who drives each step, request → reply.
2. **启动入口**: one table, 目的 | 机器 | 命令 | 输入 | 输出. Commands use placeholders such as
   `<config>` and `<run>`; define path placeholders once below the table. Note missing capabilities
   briefly here, for example that no offline evaluation entry exists.
3. **文件地图**: annotated `text` trees, one per area: entries and configs; the core package; the
   robot, device, or simulator side; algorithm packages. Give each file one line with its
   responsibility in a few words, and put minor siblings on one shared line. Leave out tests,
   `__init__.py`, caches, and function lists.
4. **模块交互**: one diagram per flow, then input/output tables.
   - Training or data pipeline: a `flowchart` from config and data to checkpoint.
   - Each runtime loop, such as deployment, online training, or evaluation: a `sequenceDiagram` with a
     `box` per machine, `actor` for humans, and messages that name the data being moved.
   - Layering: a `flowchart TB` with one subgraph per layer, arrows meaning "imports", built from the
     real imports.
   - Input/output tables, 模块 | 输入 | 输出, for the modules that appear in the diagrams.
   - A protocol table, 请求 | 发送方给 | 回复, wherever processes talk over a wire protocol.
   Short shared conventions, such as a tensor layout or a transform chain, may sit in a small `text`
   block beside the diagram that uses them.
5. **分支位置对照**: only when two branches matter, as 内容 | branch A | branch B.
6. **已知耦合**: optional, as 接口 | 现在的假设 | 位置, for interfaces that still carry one
   algorithm's or one robot's assumptions. State facts and leave decisions to the user and `plan.md`.

Keep out plans and proposals (`plan.md`), method rules and formulas (`<topic>-spec.md`), copyable
commands with prerequisites and expected results (`cmd.md`), run results (`experiments.md`), and
change history (`log.md`).

## Mermaid Conventions

These keep diagrams rendering the same in GitHub, Obsidian, and IDE previews.

- Quote every label: `A["text"]` for nodes, `-- "text" -->` for edges. Use `<br/>` for line breaks.
- Do not put `<` or `>` inside labels. Write `configs 下的 YAML` rather than a placeholder path.
- Keep edge labels to a few words; long ones are clipped. Move detail to the table under the diagram.
- Draw artifacts as edge labels rather than nodes, and merge small modules into one node (`a · b`).
  Keep a graph under roughly 25 edges, and name what was omitted in one line below it.
- Edge direction decides placement: in `flowchart LR` the source sits left of the target. Write
  `A <==> B` with `A` on the side you want it, and order machines the way they are wired (for example
  NUC → robot host → GPU server). A `subgraph` id can be an edge endpoint, which replaces one edge per
  member with a single edge.
- Use dashed arrows (`-.->`) for the exceptions a reader should notice, such as reverse dependencies,
  and say what the dashes mean above the diagram.
- In a `sequenceDiagram`, wrap each machine's participants in `box <machine>` ... `end`, and use
  `loop` and `opt` for repetition and conditions.

## Verify Before Handing Over

1. Check paths against the pinned revision, and extract the diagrams:

   ```bash
   uv run python .codex/skills/write-codebase-doc/scripts/check_codebase_doc.py \
       docs/<method>/codebase.md --repo methods/<method> --rev <commit> \
       [--rev <other branch>] --mermaid-json <scratchpad>/mermaid.json
   ```

   The script lists backtick paths and file-tree entries that match no tracked file or directory at
   any given revision; a relative path passes when some tracked path ends with it. Review each
   reported item. Fix real misses. Expected noise: placeholders, branch, repository, and protocol
   names, untracked virtual environments, external checkouts, and output directories.
2. Render every diagram and look at it, following
   [references/render-check.md](references/render-check.md). A diagram with tangled crossing edges or
   clipped edge labels is not finished: simplify it and render again. If no browser is available,
   tell the user that the diagrams were not render-checked.
3. Read the document as its reader would. Each of the five questions should be answerable from a
   diagram or table without reading paragraphs: which modules exist, which file does what, what each
   is responsible for, how to start each part, and how the parts interact.

## Maintaining

Update `codebase.md` in the same task that adds, moves, or renames an entry point, module, config
location, or protocol it describes, or that changes the registered branch. Move the snapshot line to
the new commit. A small update touches only the affected rows, tree lines, and diagram nodes; rerun
the path check, and render-check the diagrams you changed.
