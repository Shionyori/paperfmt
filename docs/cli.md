# 命令参考

### `paperfmt init`

```bash
paperfmt init --template ieee-conf [--out DIR] [--force]
```

创建 `paperfmt.toml` 和 `.paperfmt/` 目录。已有 `.tex` 文件自动备份至 `.paperfmt/backup/`。

### `paperfmt check`

```bash
paperfmt check [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--format text|json|markdown] \
    [--list-rules] \
    [--strict]
```

- 自动追踪 `\input`/`\include` 引用的子文件
- `--format markdown` 输出 Markdown 表格
- `--list-rules` 列出所有规则及启用状态
- `--strict` 存在 warning 时返回非零退出码（CI 友好）

### `paperfmt fix`

```bash
paperfmt fix [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--dry-run] \
    [--backup/--no-backup] \
    [--prune-unused] \
    [--interactive]
```

- `--dry-run` 仅展示 diff，不写入文件
- `--backup` 修复前自动备份（默认开启）
- `--prune-unused` 清理 `.bib` 中未被引用的条目
- `--interactive` / `-i` 逐条确认修复，支持 `[y]es/[n]o/[s]kip rule/[a]ll/[q]uit`

所有修复均为安全修复：仅调整格式，不改变论文语义。
