---
name: gh-issue-markdown
description: Turn a local Markdown document (specs, plans, experiment records under docs/) into a GitHub issue, pull request, or comment body that renders correctly, with its formulas and local images, then verify the rendering in a real browser. Use whenever content with LaTeX math (\( \), \[ \], $...$, $$...$$, cases/aligned environments), local images (![](figures/x.png), <img src>), mermaid diagrams, or relative links is posted to GitHub with gh, and whenever the user reports that formulas or images on a GitHub issue or PR do not show — raw $...$, red boxes such as "Missing \end{cases}" or "macros are not allowed", broken image icons, 公式没渲染 / latex 不显示 / 图片不显示 / issue 里加图片.
---

# GitHub Issue Markdown

GitHub runs its Markdown and HTML pipeline before MathJax sees a formula, so math that renders in
Obsidian, VS Code, or a local preview often breaks on an issue. Local images break too: a relative
path means nothing on an issue page. `gh` 2.99 and later upload them with `--attach`. Convert the
document with the bundled script, post the converted file with its attachments, and confirm the live
page. The source document stays as it is; the converted body is a separate file in the scratchpad.

## Workflow

1. **Convert** without touching the source:

   ```bash
   uv run --no-project python .codex/skills/gh-issue-markdown/scripts/to_gh_markdown.py \
       docs/<area>/<doc>.md -o <scratchpad>/issue-body.md --drop-h1 \
       [--link-base https://github.com/<owner>/<repo>/blob/<rev>/docs/<area>] \
       [--prepend "<intro line>"] [--append "<footer>"]
   ```

   - `--drop-h1` removes the leading `# Title` and prints it, so it can become the issue title.
   - Relative links keep only their text unless `--link-base` is given, because `experiments.md`
     means nothing on the issue page.
   - Local images, Markdown or `<img src>`, become percent-encoded absolute paths, and the script
     writes one `--attach=<path>` line per file to `<output>.attach` (empty when there are none).
     `gh` rewrites only references it can parse as a Markdown link, so a `<img>` tag becomes
     `![alt](path)` and loses its `width`; a path with a space must stay encoded.
   - Images need no commit or push. The script writes nothing when an image file is missing.
   - The script refuses to write over its source.

2. **Post** the file with `--body-file`, never by pasting the text into a shell argument, and feed the
   `.attach` file to the same command:

   ```bash
   xargs -d '\n' -a <scratchpad>/issue-body.md.attach \
       gh issue create -R <owner>/<repo> --title "<title>" --body-file <scratchpad>/issue-body.md
   ```

   `gh issue edit <n>`, `gh issue comment`, and `gh pr create|edit|comment` take the same flags.
   `gh` uploads each file and replaces every reference to it with a
   `github.com/user-attachments/assets/...` URL. A referenced image left out of `--attach` stays a
   local path with exit code 0, so always pass the generated list rather than picking files by
   hand. Only the author or a writer can edit a body later, so create it with the account that will
   maintain it.

3. **Verify** the live page:

   ```bash
   NODE_PATH=<dir>/node_modules node .codex/skills/gh-issue-markdown/scripts/check_gh_render.cjs \
       https://github.com/<owner>/<repo>/issues/<n> [--shots <scratchpad>/shots]
   ```

   The checker needs `playwright-core` and a Chrome or Chromium binary. Install the package once
   outside the repository, for example `npm i --prefix <scratchpad>/pw playwright-core@1.49.1`, and
   pass `NODE_PATH=<scratchpad>/pw/node_modules`; it finds Chrome in the usual paths or takes
   `--chrome <path>`. Exit code 0 means every formula rendered, every body image loaded, and no
   MathJax error text appeared. The report lists `math_raw` (formulas left as `$...$`),
   `images_broken` (image URLs that did not load), and `errors` (MathJax messages). With `--shots`,
   look at the section screenshots too: the checker cannot judge a formula or figure that renders
   but shows the wrong thing.

4. **Fix and repeat**. A new failure pattern belongs in `to_gh_markdown.py` with a row in the table
   below, so the next document benefits. Edit the converted file only for one-off content problems.

Do not test the checker by posting a deliberately broken body to a live issue: people may be reading
it, and one reader already saw such a test. Use a throwaway issue in a repository you own, then
delete it with `gh issue delete`.

## What the Converter Changes and Why

| Problem on GitHub | Symptom | Conversion |
|---|---|---|
| `\(...\)` is not a GitHub delimiter | formula shown as text | inline math becomes ``$`...`$`` |
| `$x$` glued to Chinese text, as in `对$\mathcal D$每` | left as plain `$...$`, so escapes are lost | only ASCII letters and digits block an inline `$` pair |
| Markdown runs inside `$...$` / `$$...$$` | `\{0,1\}` renders as `{0,1}`; `_` and `*` may turn into emphasis | inline ``$`...`$``; display math becomes a fenced `math` block |
| A line ending in `\\` inside math becomes a hard break | `\\` turns into `\\\`; `Missing \end{cases}` | the next line is joined onto the `\\` line |
| `<` inside math starts an HTML tag | everything after `<` disappears; `Missing \end{cases}` | `<` becomes `\lt`, `>` becomes `\gt` |
| `\tag{n}` in a display block | the number becomes a separate column and the formula wraps into a narrow stack | `\tag{n}` becomes `\qquad (n)` at the end of the formula |
| `\operatorname` is not allowed | red box `The following macros are not allowed: operatorname` | `\operatorname{x}` becomes `\mathrm{x}` |
| `|` inside inline math in a table row | the table cell splits | `|` becomes `\vert`, `\|` becomes `\Vert` |
| Relative image paths | broken image icon | encoded absolute path plus an `--attach` line; a missing file stops the conversion |
| Relative links | 404 from the issue page | absolute with `--link-base`, else text only |

Code blocks, inline code, external URLs, and mermaid blocks pass through unchanged; GitHub renders
`mermaid` fences natively. A lone `$` in prose, such as a price, is left alone unless a second `$` on
the same line forms a plausible pair; check such lines in the output. Obsidian embeds such as
`![[x.png]]` are not converted; rewrite them as standard Markdown images first.

## Verification Record

- Math: on XenseRobotics-AI/xense-openpi#28 (the RLToken spec, 49 inline and 16 display formulas,
  one mermaid diagram), the converted body rendered all 65 formulas with no errors and the checker
  exited 0. The pre-fix body with `|\mathcal B|<N_{\rm warm}` made it report `Missing \end{cases}`
  and exit 1. A headless load occasionally leaves all formulas raw because GitHub loads its math
  chunk lazily; the checker reloads up to three times before reporting `math_raw`.
- `\tag`: on AtticusZeller/xense-openpi#1 (the π*0.6 spec, 81 formulas, 3 images) the three
  `\tag{n}` equations rendered as squeezed stacks while the checker still exited 0; screenshots
  caught it. With `\qquad (n)` all 12 display formulas render.
- Images: on a throwaway issue, `gh 2.103.3` with `--attach` rewrote relative, absolute, and
  `%20`-encoded Markdown paths and a repeated reference, but not an HTML `<img src>` or an unencoded
  path with a space. A converted body posted through `xargs ... gh issue edit` loaded all three
  attachments in the checker. With one image missing the converter wrote nothing and exited 1.
