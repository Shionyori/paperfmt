# paperfmt 完整开发路线图

## 概述

paperfmt 是面向论文投稿前质检的 CLI 工具。当前处于 MVP 阶段（v0.1.0），拥有 `init/check/fix` 三个命令、`ieee-conf` 一个模板、11 条规则（3 条可自动修复）。

目标用户：**个人研究者**，在投稿前自检格式合规性。

路线图分 4 个 Phase，以个人作者体验为主线，兼顾架构扩展性。

---

## Phase 1: 夯实核心 — 深化 ieee-conf 规则与修复（v0.2–v0.4）

**目标：** 让个人作者在 IEEE 投稿前能发现 90% 以上的常见格式问题，并自动修复其中大部分。

### 新增检查规则

| 规则 ID | 类别 | 严重级别 | 说明 |
|---------|------|---------|------|
| `IEEE008` | 结构 | warning | `\thanks` / `\IEEEPARstart` 缺失检查 |
| `IEEE009` | 引用 | warning | `\cite` 中多个 key 用空格而非逗号分隔（可修复） |
| `IEEE010` | 数学 | warning | 公式后标点缺失 |
| `IEEE011` | 结构 | error | 缺少 `\bibliographystyle{IEEEtran}`（可修复） |
| `IEEE012` | 结构 | info | `\bibliography` 与 `\end{document}` 之间缺少平衡命令 |
| `IMG-RES` | 图片 | warning | 引用的图片分辨率/尺寸检查 |
| `LINK-VALID` | 引用 | warning | URL/DOI 链接可访问性检查 |
| `PAGE-LIMIT` | 排版 | warning | 页数限制警告 |
| `SEC-DEPTH` | 结构 | info | 章节嵌套深度检查 |
| `FIG-REF` | 交叉引用 | warning | 图片是否在正文中被 `\ref` 引用 |
| `TAB-REF` | 交叉引用 | warning | 表格是否在正文中被 `\ref` 引用 |
| `EQ-REF` | 交叉引用 | warning | 公式是否在正文中被 `\eqref` 引用 |

### 新增自动修复

- `IEEE009` — 自动修正 `\cite` 内分隔符
- `IEEE011` — 自动插入缺失的 `\bibliographystyle{IEEEtran}`
- `BIB-CROSSCHECK` — 扩展 `--prune-unused` 标志，清理未引用条目

### 架构改进

- **多文件项目支持：** 解析 `\input{...}` / `\include{...}` 指令，递归检查子文件
- **Markdown 报告：** `check --format markdown` 输出，方便粘贴到 PR/issue
- **规则列表查询：** `paperfmt check --list-rules` 打印当前模板所有规则及启用状态（完整的 `paperfmt config` 子命令组在 Phase 3 实现）

### 验收标准

- 规则总数达到 23+，可自动修复 6+ 条
- 多文件项目检查覆盖率通过测试验证
- Markdown 格式输出包含规则 ID、行号、严重级别、修复建议

---

## Phase 2: 多模板支持（v0.5–v0.7）

**目标：** 覆盖主流会议/期刊模板，让 paperfmt 成为投稿前检查的通用工具。

### 新增模板

| 模板 ID | 初始规则数 | 优先级理由 |
|---------|-----------|-----------|
| `acm-conf` | 8-10 | 与 IEEE 并列为最大用户群 |
| `neurips` | 6-8 | ML 顶会，独特匿名化与页数要求 |
| `icml` | 5-7 | 与 NeurIPS 类似但模板有差异 |
| `cvpr` | 5-7 | CV 领域，匿名化+补充材料规则 |
| `springer-lncs` | 5-7 | LNCS 系列覆盖面广 |

### 共享规则机制

通用规则（`CITE-MANUAL`、`REF-HARDCODE`、`TAB-FORMAT`、`BIB-CROSSCHECK` 等）提取为 `common` 规则集。模板注册时声明继承关系，实现 DRY。

### 架构变化

```
paperfmt/core/rules/
├── __init__.py       # 注册 + 模板继承解析
├── base.py           # RulePlugin（不变）
├── common.py         # 跨模板通用规则（新增）
├── ieee_conf.py      # IEEE 特有规则
├── acm_conf.py       # ACM 特有规则（新增）
├── neurips.py        # NeurIPS 特有规则（新增）
├── icml.py           # ICML 特有规则（新增）
├── cvpr.py           # CVPR 特有规则（新增）
└── lncs.py           # LNCS 特有规则（新增）
```

`registry.py` 增加 `inherits` 元数据，`get_template_plugins()` 解析继承链。

### 验收标准

- 5 个新模板可用，每个含 5+ 条规则
- `common` 规则集覆盖所有模板的共享检查
- 模板继承机制通过单元测试验证

---

## Phase 3: 交互体验（v0.8–v0.9）

**目标：** 从"命令行检查"升级为"交互式辅助修正"，降低使用门槛。

### 交互式修复

```
paperfmt fix --interactive main.tex
```

- 逐条展示诊断，用户选择 `[y]es / [n]o / [s]kip / [q]uit`
- 每条显示上下文（前后 3 行）和高亮出错位置
- 支持 `--group-by rule` 按规则分组批量确认

### 报告增强

- `--format html` 生成独立 HTML 报告（折叠面板、严重级别着色）
- `check` 输出增加修复建议列（可修复/不可修复）
- `--diff` 标志等价于 `check` + `fix --dry-run`，一次性展示诊断和修复预览

### 配置管理子命令

```
paperfmt config show          # 显示当前配置
paperfmt config list-rules    # 列出所有规则及状态
paperfmt config set IEEE001 --enabled false   # 禁用规则
paperfmt config set IEEE001 --severity error  # 调整严重级别
paperfmt config reset         # 恢复默认配置
```

### 验收标准

- 交互式修复可完整走通用户确认流程
- HTML 报告可在浏览器中直接查看
- `config` 子命令组所有操作可用

---

## Phase 4: 生态集成（v0.10+）

**目标：** 融入研究者日常工作流，降低使用门槛，建立社区。

### CI 集成

- GitHub Actions 模板文件，`paperfmt init` 时可选生成
- `--strict` 模式下非零退出码 → CI 自动拦截不合规投稿
- `--format sarif` 输出 SARIF 格式，由 GitHub Code Scanning 消费

### 编辑器集成

- VS Code 基础支持：文件保存时自动运行 `paperfmt check`
- 提供 `.vscode/tasks.json` 模板

### 在线版（轻量）

- 单页 Web 工具：粘贴 `.tex` → 即时检查 → 诊断展示
- 使用 Pyodide 在浏览器中运行 Python
- 作为 discovery 渠道，引导用户安装 CLI 版本

### 社区规则市场

- 支持外部规则插件：`paperfmt check --plugin ./my-rules.py`
- 规则文件遵循约定接口：暴露 `RULES: tuple[RulePlugin, ...]`
- README 提供贡献指南

### 验收标准

- GitHub Actions 模板可被 `paperfmt init` 生成并正常工作
- SARIF 输出被 GitHub Code Scanning 正确消费
- 外部 `--plugin` 规则可被加载并参与检查

---

## 路线图总览

```
Phase 1 (v0.2–v0.4)  ████████████  夯实核心：23+ 规则 + 多文件 + markdown 报告
Phase 2 (v0.5–v0.7)  ████████████  多模板：ACM/NeurIPS/ICML/CVPR/LNCS + 共享规则
Phase 3 (v0.8–v0.9)  ████████████  交互式修复 + HTML 报告 + config 子命令
Phase 4 (v0.10+)      ████████████  CI 模板 + VS Code + 在线版 + 社区规则
```

## 核心原则

- **CLI-first：** 所有功能首先通过 CLI 暴露，GUI/编辑器集成基于 CLI
- **规则可扩展：** 新增模板和规则不需要改动核心引擎
- **安全修复优先：** 自动修复不改变论文语义，仅调整格式和样式
- **配置驱动：** paperfmt.toml 是唯一配置入口，所有行为和规则可调
