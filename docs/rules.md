# 规则列表

### ieee-conf

| 规则 | 说明 | 严重级别 | 可修复 |
|------|------|----------|--------|
| `IEEE001` | 图注应在 `\includegraphics` 之后 | warning | ✓ |
| `IEEE002` | 表注应在 `tabular` 之前 | warning | ✓ |
| `IEEE003` | `\citep`/`\citet` 归一化为 `\cite` | warning | ✓ |
| `IEEE004` | 缺失 `abstract` 环境 | error | |
| `IEEE005` | 缺失 `IEEEkeywords` 环境 | warning | ✓ |
| `IEEE006` | 双盲匿名泄漏（作者块） | warning | |
| `IEEE007` | 已引用条目 DOI 缺失 | warning | |
| `IEEE008` | 缺失 `\thanks`（作者单位/基金信息） | warning | |
| `IEEE009` | `\cite` keys 应为逗号分隔 | warning | ✓ |
| `IEEE010` | 公式环境缺少末尾标点 | warning | ✓ |
| `IEEE011` | 缺失 `\bibliographystyle{IEEEtran}` | error | ✓ |
| `IEEE012` | 缺失 `\balance` 等分栏平衡命令 | info | ✓ |

### acm-conf

| 规则 | 说明 | 严重级别 | 可修复 |
|------|------|----------|--------|
| `ACM001` | 缺失 `\documentclass{acmart}` | error | |
| `ACM002` | 缺失 `\keywords{...}` | warning | |
| `ACM003` | 缺失 `\bibliographystyle{ACM-Reference-Format}` | error | ✓ |
| `ACM004` | 缺失 CCS 概念 (`\ccsdesc`) | warning | |
| `ACM005` | `\thanks` 应替换为 `\titlenote` | warning | ✓ |
| `ACM006` | 作者缺失 `\affiliation{...}` | warning | |
| `ACM007` | 图注应在 `\includegraphics` 之后 | warning | ✓ |
| `ACM008` | 表注应在 `tabular` 之前 | warning | ✓ |
| `ACM009` | 缺失 `\received`/`\accepted` | warning | |
| `ACM010` | `\citeauthor`/`\citeyear` 应替换为 `\cite` | warning | |
| `ACM011` | 作者缺失 `\email{...}` | warning | |
| `ACM012` | `acmsmall` 格式参数检查 | info | |

### neurips

| 规则 | 说明 | 严重级别 | 可修复 |
|------|------|----------|--------|
| `NEUR001` | 缺失 `\documentclass{neurips_XXX}` | error | |
| `NEUR002` | 缺失 `\usepackage[preprint]{neurips_XXX}` | error | |
| `NEUR003` | 缺失作者自查表章节 | warning | |
| `NEUR004` | `\author` 应在 `\begin{abstract}` 之后 | warning | |
| `NEUR005` | `\bibliographystyle` 应为 `{plain}` 等 | warning | |
| `NEUR006` | `\cite` 应替换为 `\citep`/`\citet` | warning | ✓ |
| `NEUR007` | 缺失 `abstract` 环境 | error | |
| `NEUR008` | 缺失 `\section{Introduction}` | warning | |
| `NEUR009` | 图注应在 `\includegraphics` 之后 | warning | ✓ |
| `NEUR010` | 表注应在 `tabular` 之前 | warning | ✓ |
| `NEUR011` | `\citep`/`\citet` keys 应为逗号分隔 | warning | ✓ |
| `NEUR012` | 缺失 `\balance` 分栏平衡命令 | info | |

### acl-conf

| 规则 | 说明 | 严重级别 | 可修复 |
|------|------|----------|--------|
| `ACL001` | 缺失 `\usepackage{acl}` | error | |
| `ACL002` | 缺失 `\author` 或 `\affiliation` | warning | |
| `ACL003` | 缺失 `\bibliographystyle{acl_natbib}` | error | ✓ |
| `ACL004` | `\cite` 应替换为 `\citep`/`\citet` | warning | ✓ |
| `ACL005` | 缺失 `abstract` 环境 | error | |
| `ACL006` | 图注应在 `\includegraphics` 之后 | warning | ✓ |
| `ACL007` | 表注应在 `tabular` 之前 | warning | ✓ |
| `ACL008` | 缺失 Limitations/Ethics 章节（ARR 要求） | warning | |
| `ACL009` | 缺失数据/代码仓库链接 | warning | |
| `ACL010` | `\thanks`/`\footnote` 可能破坏匿名 | warning | |
| `ACL011` | `a4paper` 应改为 US letter | warning | |
| `ACL012` | 缺失 `\aclfinalcopy`（camera-ready） | info | |

### 通用规则（所有模板共享）

| 规则 | 说明 | 严重级别 | 可选依赖 |
|------|------|----------|----------|
| `CITE-MANUAL` | 手写数字引用（如 `[1]`），应使用 `\cite` | warning | |
| `REF-HARDCODE` | 硬编码交叉引用（如 `Eq. (1)`），应使用 `\ref` | warning | |
| `TAB-FORMAT` | 表格 `\hline` 建议替换为 booktabs 命令 | warning | |
| `BIB-CROSSCHECK` | `.tex` 与 `.bib` 双向比对 | warning | |
| `FIG-REF` | 图片标签未被文中引用 | warning | |
| `TAB-REF` | 表格标签未被文中引用 | warning | |
| `EQ-REF` | 公式标签未被文中引用 | warning | |
| `IMG-RES` | 图片分辨率检查（建议 300 DPI） | warning | Pillow |
| `LINK-VALID` | URL/DOI 可达性检查 | warning | httpx |
| `PAGE-LIMIT` | 页数估算 | warning | |
| `SEC-DEPTH` | 章节嵌套深度（`\subsubsection` 以上警告） | info | |
