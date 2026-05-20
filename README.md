简体中文 | [English](./README.en.md)

<p align="center">
  <img src="docs/icon.png" alt="paperfmt" width="128">
</p>

<h1 align="center">paperfmt</h1>

<p align="center">
  学术论文模板合规检查与安全修复工具。
  <br>
  解析 <code>.tex</code> 多文件项目，生成可读报告，一键修复格式问题。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-%E2%89%A53.10-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
</p>

## 快速开始

```bash
# 在论文项目目录下初始化
paperfmt init --template ieee-conf

# 运行检查
paperfmt check

# 一键修复
paperfmt fix
```

## 支持模板

| 模板 | 标识 | 规则数 | 说明 |
|------|------|--------|------|
| IEEE 会议 | `ieee-conf` | 12 | IEEE 会议论文格式 |
| ACM 会议 | `acm-conf` | 12 | ACM 会议论文格式 |
| NeurIPS | `neurips` | 12 | NeurIPS 会议论文格式 |
| ACL 会议 | `acl-conf` | 12 | ACL 会议论文格式 |

所有模板均包含 10 项通用规则（引用检查、标签验证、分辨率检查等）。

> 详细内容见 [规则列表](./docs/rules.md)。

## 命令一览

| 命令 | 用途 |
|------|------|
| `paperfmt init` | 初始化项目，创建 `paperfmt.toml` 和 `.paperfmt/` |
| `paperfmt check` | 检查 `.tex` 文件，支持 `--strict` CI 模式、`--format json` 等 |
| `paperfmt fix` | 安全修复，支持 `--dry-run` 预览、`--interactive` 逐条确认 |

> 详细用法见 [命令参考](./docs/cli.md)。

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
