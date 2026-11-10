# RPent Log

## 2026-11-10 · 接入 RPent

- **背景与目的：** 接入 RLinf 组织的 RPent（[文档](https://rpent.readthedocs.io/en/latest/)，arXiv 2607.08448）作为 framework，供后续研究与参考。
- **实现思路：** fork `AtticusZeller/RPent` 作 origin，官方 `RLinf/RPent` 作 upstream；`workspace` 分支从上游 `main` 的 `ed6b922` 开出，未加提交。上游自带 `AGENTS.md`，`CLAUDE.md` 是指向它的符号链接，原样保留。
- **组件变化：** 新增 `methods/rpent`，登记到 README；上游没有嵌套 submodule；未创建实验配置或 runbook。
- **主要文件：** `.gitmodules` 与 `methods/rpent` gitlink；`docs/rpent/overview.md`。
- **验证：** `git ls-remote` 确认 fork 的 `workspace` 与 gitlink 同为 `ed6b922`。
