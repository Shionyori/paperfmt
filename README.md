简体中文 | [English](./README.en.md)

# paperfmt

论文的自动化质检与修复工具。解析 `.tex` 多文件项目，生成可读报告，并提供一键修复。

支持模板：`ieee-conf` · `acm-conf` · `neurips` · `acl-conf`

## 快速开始

```bash
# 在论文项目目录下初始化
paperfmt init --template ieee-conf

# 运行检查
paperfmt check

# 一键修复
paperfmt fix
```

## 配置

`paperfmt.toml` 示例：

```toml
main_tex = "paper.tex"
bibliography = "refs.bib"

[rules.IEEE006]
enabled = false        # 关闭匿名泄露检查

[rules.IEEE007]
severity = "warning"   # DOI 缺失降级为警告
```

执行记录自动追加至 `.paperfmt/report.txt`。

## 文档

| 文档 | 说明 |
|------|------|
| [命令参考](./docs/cli.md) | `init` / `check` / `fix` 详细用法 |
| [规则列表](./docs/rules.md) | 全部模板规则及说明 |
