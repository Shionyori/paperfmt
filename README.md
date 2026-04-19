简体中文 | [English](./README.en.md)

# paperfmt

paperfmt 是一个面向论文投稿前质检的 CLI 工具。

当前稳定模板：`ieee-conf`。


## 命令说明

```bash
paperfmt init --template ieee-conf [--out DIR] [--force]
paperfmt check [INPUT.tex] [--template ieee-conf] [--config paperfmt.toml] [--format text|json] [--strict]
paperfmt fix [INPUT.tex] [--template ieee-conf] [--config paperfmt.toml] [--dry-run] [--backup/--no-backup]
```

说明：
- `init` 初始化工具文件。
- `check` / `fix` 默认读取 `paperfmt.toml` 中的 `main_tex`、`bibliography`、`rules`。
- 所有执行记录会追加到 `.paperfmt/report.txt`。

## 配置驱动

`paperfmt.toml` 是纯文本配置，驱动链路为：

`paperfmt.toml -> RuleSet -> template rules plugins`

你可以手动修改：
- `main_tex`
- `bibliography`
- `state_dir`
- 每条规则的 `enabled` / `severity`

## 已实现规则（ieee-conf）

- `IEEE001` 图注位置检查（图注应在 `\\includegraphics` 后）
- `IEEE002` 表注位置检查（表注应在 `tabular` 前）
- `IEEE003` 引用命令规范化建议（`\\citep` / `\\citet`）
- `IEEE004` 缺失 `abstract` 环境
- `IEEE005` 缺失 `IEEEkeywords` 环境
- `IEEE006` 双盲匿名泄漏（作者块）
- `IEEE007` 已引用条目 DOI 缺失
- `CITE-MANUAL` 手写数字引用（如 `[1]`）
- `REF-HARDCODE` 硬编码交叉引用（如 `Eq. (1)`）
- `TAB-FORMAT` 表格 `\\hline` 风格检查（建议 `booktabs`）
- `BIB-CROSSCHECK` `.tex` 与 `.bib` 双向比对（缺失键/未引用条目）

## 已实现自动修复（safe fixes）

- 图注位置修正（`IEEE001`）
- 表注位置修正（`IEEE002`）
- `\\citep` / `\\citet` 归一化为 `\\cite`（`IEEE003`）

## 规则扩展方式

当前规则按模板分文件组织：

- `paperfmt/core/rules/ieee_conf.py`：`ieee-conf` 全部规则
- `paperfmt/core/rules/__init__.py`：模板到规则集的汇总注册

新增模板建议流程：
1. 新建 `paperfmt/core/rules/<template>.py`
2. 在 `paperfmt/core/rules/__init__.py` 注册
3. 在 `paperfmt/core/registry.py` 增加模板标识
