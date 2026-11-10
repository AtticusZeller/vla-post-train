# ASPIRE Log

## 2026-11-10 · 接入 ASPIRE

- **背景与目的：** 接入 NVIDIA GEAR 的 ASPIRE（[项目页](https://research.nvidia.com/labs/gear/aspire/)，arXiv 2607.00272）作为 method，供后续研究与参考。
- **实现思路：** fork `AtticusZeller/ASPIRE` 作 origin，官方 `NVlabs/ASPIRE` 作 upstream；`workspace` 分支从上游 `main` 的 `fa00f0e` 开出，未加任何提交。6 个嵌套 submodule 保持未初始化。
- **组件变化：** 新增 `methods/aspire`，登记到 README；未创建实验配置或 runbook。
- **主要文件：** `.gitmodules` 与 `methods/aspire` gitlink；`docs/aspire/overview.md`。
- **验证：** `git ls-remote` 确认 fork 的 `workspace` 与 gitlink 同为 `fa00f0e`；6 个嵌套 submodule 的远端均可访问，未递归检出。
