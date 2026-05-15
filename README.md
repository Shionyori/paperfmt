简体中文 | [English](./README.en.md)

# paperfmt

paperfmt 是一个面向论文投稿前质检的 CLI 工具。支持 `.tex` 多文件项目、markdown 报告和自动修复。

当前稳定模板：`ieee-conf`（23 条规则，6 个自动修复）。

## 安装

```bash
pip install -e ".[dev]"        # 开发安装（含测试依赖）
pip install -e ".[image,link]"  # 可选：图片分辨率和链接可达性检查
pip install -e ".[full]"        # 全部可选依赖
```

## 命令说明

```bash
# 初始化项目
paperfmt init --template ieee-conf [--out DIR] [--force]

# 检查
paperfmt check [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--format text|json|markdown] \
    [--list-rules] \
    [--strict]

# 修复
paperfmt fix [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--dry-run] \
    [--backup/--no-backup] \
    [--prune-unused]
```

说明：
- `init` 初始化工具文件，已有 `.tex` 文件会自动备份到 `.paperfmt/backup/`。
- `check` / `fix` 默认读取 `paperfmt.toml` 中的 `main_tex`、`bibliography`、`rules`。
- `check` 支持 `\input`/`\include` 引用的子文件递归解析。
- `--format markdown` 输出 markdown 表格格式报告。
- `--list-rules` 列出当前模板所有规则及其启用状态和严重级别。
- `--prune-unused` 删除 `.bib` 中未被引用的条目。
- 所有执行记录会追加到 `.paperfmt/report.txt`。

## 配置驱动

`paperfmt.toml` 是纯文本配置，驱动链路为：

`paperfmt.toml -> RuleSet -> template rules plugins`

你可以手动修改：
- `main_tex`
- `bibliography`
- `state_dir`
- 每条规则的 `enabled` / `severity`

## 已实现规则（ieee-conf，共 23 条）

### 结构与排版
- `IEEE001` 图注位置检查（图注应在 `\includegraphics` 后） **[可修复]**
- `IEEE002` 表注位置检查（表注应在 `tabular` 前） **[可修复]**
- `IEEE004` 缺失 `abstract` 环境（error）
- `IEEE005` 缺失 `IEEEkeywords` 环境
- `IEEE008` 缺失 `\thanks`（作者单位/基金信息）
- `IEEE011` 缺失 `\bibliographystyle{IEEEtran}`（error） **[可修复]**
- `IEEE012` 缺失 `\balance` 等分栏平衡命令
- `TAB-FORMAT` 表格 `\hline` 风格检查（建议 `booktabs`）

### 引用与交叉引用
- `IEEE003` 引用命令规范化（`\citep` / `\citet` 归一化为 `\cite`）**[可修复]**
- `IEEE009` `\cite` keys 应为逗号分隔 **[可修复]**
- `IEEE010` 公式环境缺少末尾标点
- `CITE-MANUAL` 手写数字引用（如 `[1]`）
- `REF-HARDCODE` 硬编码交叉引用（如 `Eq. (1)`）
- `FIG-REF` 图片标签未被文中引用
- `TAB-REF` 表格标签未被文中引用
- `EQ-REF` 公式标签未被文中引用

### 匿名与文献
- `IEEE006` 双盲匿名泄漏（作者块）
- `IEEE007` 已引用条目 DOI 缺失
- `BIB-CROSSCHECK` `.tex` 与 `.bib` 双向比对（缺失键/未引用条目）

### 外部资源与启发式检查
- `IMG-RES` 图片分辨率检查（需 Pillow，可选）
- `LINK-VALID` URL/DOI 可达性检查（需 httpx，可选）
- `PAGE-LIMIT` 页数估算（IEEE 会议通常 6-8 页）
- `SEC-DEPTH` 章节嵌套深度（`\subsubsection` 以上警告）

## 已实现自动修复（safe fixes，共 6 个）

- `IEEE001` — 图注位置修正（`\caption` 移至 `\includegraphics` 之后）
- `IEEE002` — 表注位置修正（`\caption` 移至 `tabular` 之前）
- `IEEE003` — `\citep` / `\citet` 归一化为 `\cite`
- `IEEE009` — `\cite` keys 空格分隔修正为逗号分隔
- `IEEE011` — 自动插入 `\bibliographystyle{IEEEtran}`
- `--prune-unused` — 删除 `.bib` 中未被引用的条目

所有修复均为安全修复，不会改变论文语义，且默认创建备份。

## 规则扩展方式

当前规则按模板分文件组织：

- `paperfmt/core/rules/ieee_conf.py`：`ieee-conf` 全部规则
- `paperfmt/core/rules/__init__.py`：模板到规则集的汇总注册

新增模板建议流程：
1. 新建 `paperfmt/core/rules/<template>.py`，定义 `RULES: tuple[RulePlugin, ...]`
2. 在 `paperfmt/core/rules/__init__.py` 的 `TEMPLATE_RULES` 中注册
3. 在 `paperfmt/core/registry.py` 的 `CANONICAL_TEMPLATES` 中增加模板标识

## 开发

```bash
pip install -e ".[dev]"
python -m pytest -q        # 运行全部测试
python -m pytest -v         # 详细输出
python -m paperfmt --help   # 查看 CLI 帮助
```
