## Plan: Paperfmt Checker/Fixer 落地方案

围绕“论文模板合规检查与安全修复”定位，先交付最小可发布闭环：`init/check/fix` 三命令 + IEEE 规则集 + 可追溯修复。

**Steps**
1. 明确边界与成功标准：冻结 MVP 范围为 `init/check/fix`，输入为 `.tex`，输出为结构化诊断与安全补丁；排除编译调度、编辑器能力、语义改写。
2. Phase A（命令入口）：搭建 CLI 子命令框架，支持 `paperfmt init --template ieee`、`paperfmt check main.tex`、`paperfmt fix main.tex --dry-run`。
3. Phase B（规则引擎）：实现规则模型（规则 ID、严重级别、行号、是否可修复），先落地 IEEE 高频规则。
4. Phase C（安全修复）：只允许语义不变的修复，支持备份、差异预览与可回滚。
5. Phase D（报告与 CI）：支持 text/json 输出与严格模式退出码，方便本地和 CI 流水线接入。
6. Phase E（可发布最小质量）：补齐命令烟测与工作流测试，完善 README 与样例文档。
7. 发布 Gate：以“投稿前 30 秒发现关键格式问题”为验收门槛；通过后发布 v0.1.0。
8. P1 演进（并行候选）：匿名化检查、DOI 完整性、图片分辨率、链接有效性、交互式修复。

**Relevant files**
- /home/shionyori/project/paperfmt/pyproject.toml — 包管理与 CLI 入口。
- /home/shionyori/project/paperfmt/paperfmt/cli.py — `init/check/fix` 命令定义。
- /home/shionyori/project/paperfmt/paperfmt/core/checker.py — 规则扫描与安全修复。
- /home/shionyori/project/paperfmt/paperfmt/core/scaffold.py — 模板工程初始化。
- /home/shionyori/project/paperfmt/tests/test_cli.py — CLI 基础可见性测试。
- /home/shionyori/project/paperfmt/tests/test_workflow.py — 命令工作流测试。
- /home/shionyori/project/paperfmt/README.md — 新定位和用法说明。

**Verification**
1. 运行 `paperfmt init --template ieee`，确认生成 `main.tex` 与 `refs.bib`。
2. 运行 `paperfmt check main.tex --format text/json`，确认输出诊断与统计。
3. 运行 `paperfmt fix main.tex --dry-run`，确认只输出补丁不改写文件。
4. 运行 `paperfmt fix main.tex`，确认创建备份并写回修复结果。
5. 运行 `python -m pytest -q`，确认命令与规则回归通过。

**Decisions**
- 已确认：不再承担 Pandoc/LaTeX 编译调度。
- 已确认：MVP 输入以 `.tex` 为主。
- 已确认：首批模板规则从 IEEE 开始。
- 设计原则：CLI-first、规则可扩展、安全修复优先。

**Further Considerations**
1. 引入规则配置文件（开关、级别、模板分组）。
2. 增加交互式修复确认与撤销历史。
3. 输出 SARIF/JSON 报告以便代码审查与 CI 集成。