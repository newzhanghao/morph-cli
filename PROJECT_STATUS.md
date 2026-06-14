# PROJECT_STATUS.md — morph-cli 项目状态报告

> 更新时间：2026-06-14  
> 版本：v0.1.0 (MVP)

---

## 一、项目概述

**morph** 是一个流式的、零学习成本的数据处理 CLI。面向 AI 时代开发者：filter/select/convert JSON CSV YAML，一行命令搞定，不爆内存。

| 项目 | 详情 |
|------|------|
| 包名 | `morph-cli` (PyPI: `morph-converter`) |
| 命令 | `morph` |
| 定位 | Process data at the speed of thought |
| GitHub | https://github.com/newzhanghao/morph-cli |
| PyPI 状态 | ✅ TestPyPI 已验证，正式版待发布 |
| 技术栈 | Python ≥3.9 + Click + Rich + PyYAML |
| 许可证 | MIT |

---

## 二、完成情况

### ✅ 阶段 0：项目初始化
- [x] 项目目录结构
- [x] `pyproject.toml`（含 CLI entry point）
- [x] `.gitignore`
- [x] 虚拟环境 + 依赖安装
- [x] GitHub 仓库创建 + 代码推送 + tag v0.1.0 + Release

### ✅ V1 核心功能

| 模块 | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| 安全表达式引擎 | `morph/filter_expr.py` | 33 | ✅ |
| 格式检测 | `morph/detector.py` | 11 | ✅ |
| 转换引擎 | `morph/converter.py` | 16 | ✅ |
| CLI 入口 | `morph/cli.py` | 41 (含新命令) | ✅ |
| 工具函数 | `morph/utils.py` | 15 | ✅ |
| 测试 fixtures | `tests/fixtures/` | 8 个 | ✅ |

| 功能 | 状态 |
|------|------|
| JSON → CSV（嵌套自动拍平） | ✅ |
| JSON → YAML | ✅ |
| CSV → JSON（类型推断） | ✅ |
| CSV → YAML | ✅ |
| YAML → JSON | ✅ |
| YAML → CSV（嵌套拍平） | ✅ |
| **`morph filter` — AST 安全过滤** | ✅ 新增 |
| **`morph select` — 字段提取 (dot-notation)** | ✅ 新增 |
| **`morph head/tail` — 记录预览** | ✅ 新增 |
| **`morph sample` — 随机采样** | ✅ 新增 |
| 自动格式检测（扩展名 + 内容嗅探） | ✅ |
| 管道/标准输入读取 | ✅ |
| `-o` 文件输出 | ✅ |
| `--pretty` / `--no-pretty` | ✅ |
| `--flatten` / `--no-flatten` | ✅ |
| `--delimiter` 自定义分隔符 | ✅ |
| Rich 终端语法高亮（JSON/YAML） | ✅ |
| 编码自动检测（UTF-8/BOM/Latin-1/GBK） | ✅ |
| CSV 智能类型推断（int/float/bool/null） | ✅ |
| `--help` 和 `--version` | ✅ |

### ✅ 发布准备
- [x] README.md — 新定位 + LLM SEO + 命令文档
- [x] 竞品分析 Excel (jq/yq/csvkit — 6 sheets)
- [ ] asciinema 终端录屏（待用户录制）
- [ ] 正式发布到 PyPI（待用户操作）

---

## 三、架构

```
morph/
  cli.py         — CLI 入口 (convert, filter, select, head, tail, sample)
  converter.py   — 格式转换引擎 (JSON/CSV/YAML 互转)
  detector.py    — 自动格式检测
  filter_expr.py — 安全表达式引擎 (AST walker, 零依赖, 无 eval)
  utils.py       — 编码检测/类型推断/CSV 写入
```

### 安全设计

`filter_expr.py` 用 Python `ast` 模块做白名单解析：  
- 物理阻止函数调用 (`ast.Call` 直接拒绝)  
- 阻止推导式、lambda  
- 缺失字段优雅降级返回 False 而非 TypeError  
- 零第三方依赖

---

## 四、已修复 Bug

| # | 问题 | 状态 |
|---|------|------|
| 1 | `--no-flatten` CSV 嵌套值序列化为合法 JSON | ✅ |
| 5 | 单列 CSV 误识别为 YAML | ✅ |
| 6 | PyYAML 默认 width=80 导致长文本换行 | ✅ |

---

## 五、下一步计划

### 短期
- [ ] 正式发布到 PyPI
- [ ] 社区帖子（r/Python, r/commandline, Hacker News Show HN）
- [ ] 收集反馈，决定 V2 优先级

### V2 候选功能（待社区反馈定优先级）
- `morph dedupe` — 基于某字段去重
- `morph sort` — 流式排序
- `morph preview` — Rich 表格终端预览
- 流式 I/O (>100MB 文件分块处理)
- `--encoding` 显式指定编码选项

### 货币化（远期）
- Gumroad $3.99 买断
- 桌面版 Pro（可视化编辑、批量管道）

---

## 六、决策记录

| 决策 | 结论 | 日期 |
|------|------|------|
| 产品方向 | 数据格式转换，不做图片 | 2026-06-11 |
| 产品形态 | 独立 CLI 工具，做精做深 | 2026-06-11 |
| 商业模式 | CLI 免费获客 → 桌面版 Pro 收费 | 2026-06-11 |
| 包名 | `morph-cli`，命令 `morph` | 2026-06-11 |
| V1 范围 | 只做 `convert` → 扩展为 filter/select/head/sample | 2026-06-14 |
| 技术栈 | Python + Click + Rich（不用 Rust/Tauri） | 2026-06-11 |
| 产品定位升级 | 格式转换器 → **AI 时代的一句话数据处理 CLI** | 2026-06-14 |
| 安全过滤方案 | `ast` 白名单，不 eval | 2026-06-14 |
| 不造 DSL | 子命令 + 参数，不发明新语言 | 2026-06-14 |
| 不造 AI 子命令 | 保持确定性工具纯粹性 | 2026-06-14 |
| 验证路径 | 先发 HN / Reddit，再决定是否开 Gumroad | 2026-06-11 |
