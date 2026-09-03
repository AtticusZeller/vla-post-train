# Documentation Rules

These rules apply to every file under `docs/`.

## Purpose and Layout

Documentation is human-facing project context. Keep only information that helps a researcher understand
an area, resume an approved task, or assess completed work without reconstructing the discussion.

The only first-level documentation directories are:

- `docs/workspace/` for root orchestration, governance, and cross-method work;
- `docs/<method>/` for a method that currently exists under `methods/<method>/`.

Every directory must contain `plan.md` and `log.md`. Use `overview.md` for durable understanding of the
area. Add another topic file only when one coherent subject cannot remain clear inside `overview.md`.

Do not create root-level human documentation alongside this file. Keep planning, change summaries, and
durable understanding inside the applicable first-level directory.

## `plan.md` Contract

`plan.md` contains confirmed, unfinished work only. A chunk is one coherent transaction and may contain
multiple dependent tasks. Remove the chunk after acceptance and summarize the result in `log.md`.

Each task uses this structure:

```markdown
## <事务名称>

### Task: <可观察目标>

**Change**

- <要实现或修改什么>

**Verification**

1. <Agent 可以实际运行的检查>

**Done**

- <可以直接观察和判断的验收结果>
```

`Task = Change + Observable Evidence`. Do not use “完成实现”“测试通过” or another circular claim as
the Done condition. When no work is approved, write only `当前没有已确认、未完成的事务。`.

## `log.md` Contract

`log.md` records completed substantial changes, newest first. One entry may compress several commits of
the same intent. It is a change summary, not a commit list, terminal transcript, daily journal, or test
dump.

Each entry contains:

```markdown
## YYYY-MM-DD · <改动名称>

- **背景与目的：** <为什么需要这次改动；新增能力或解决的问题>
- **实现思路：** <方案和关键边界>
- **组件变化：** <新增、替换或移除的模块>
- **主要文件：** <少量关键路径及其职责>
- **验证：** <检查方式和观察到的结果>
```

Keep the explanation at design level. Mention only files needed to locate the change; omit routine code
details and exhaustive path lists.

## Understanding Notes

`overview.md` and topic notes may preserve conclusions from researcher-agent discussions. Keep:

- responsibilities and boundaries;
- architecture and information flow;
- non-obvious design rationale or distinctions;
- verified limitations, uncertainty, and evidence boundaries.

Do not copy directory trees, class/function inventories, setup command transcripts, historical commit
sequences, or facts that a quick code read or command reveals. Do not turn an upstream claim into local
verification. Use a date or pinned revision only when the conclusion is snapshot-sensitive.

Write human documentation in concise Chinese. Keep identifiers, paths, interface names, and established
technical terms in their original form when translation would reduce precision.
