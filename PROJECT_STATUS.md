# PROJECT_STATUS.md — morph-cli 项目状态报告

> 更新时间：2026-06-12  
> 版本：v0.1.0 (MVP)

---

## 一、项目概述

**morph** 是一个面向开发者的命令行数据格式转换工具，支持 JSON、CSV、YAML 三种格式之间的互转。CLI 完全免费，作为获客漏斗，未来桌面版（Pro）收费。

| 项目 | 详情 |
|------|------|
| 包名 | `morph-cli` |
| 命令 | `morph` |
| PyPI 状态 | ✅ 已上传 TestPyPI，待正式发布 |
| 技术栈 | Python ≥3.9 + Click + Rich + PyYAML |
| 许可证 | MIT |

---

## 二、当前完成情况

### ✅ 阶段 0：项目初始化
- [x] 项目目录结构
- [x] `pyproject.toml`（含 CLI entry point）
- [x] `.gitignore`
- [x] 虚拟环境 + 依赖安装
- [x] pip install -e . 可安装

### ✅ 阶段 1：V1 核心功能 `morph convert`

| 模块 | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| 格式检测 | `morph/detector.py` | 11 | ✅ 68/68 通过 |
| 转换引擎 | `morph/converter.py` | 16 | ✅ |
| CLI 入口 | `morph/cli.py` | 19 | ✅ |
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

### ✅ 阶段 2：发布准备
- [x] README.md（安装 / 用法 / 对比表 / Roadmap）
- [ ] asciinema 终端录屏（待用户录制）
- [x] 发布到 PyPI（待用户操作） → ✅ 2026-06-12 已上传 TestPyPI 验证通过
- [ ] Git tag + GitHub Release

---

## 三、已知问题 & 待改进点

### 🐛 Bug / 边界情况

| # | 问题描述 | 严重程度 | 状态 |
|---|---------|---------|------|
| 1 | ~~`--no-flatten` 时嵌套对象在 CSV 中显示为 Python dict 字符串（`{'key': 'val'}`），而不是合法 JSON（`{"key": "val"}`）~~ | 中 | ✅ 已修复 |
| 2 | 超大文件（>100MB）没有流式处理，会一次性加载到内存 | 低 | V2 Roadmap |
| 3 | 没有 `--encoding` 显式指定编码的选项，只能靠自动检测 | 低 | 待讨论 |
| 4 | YAML → CSV 当顶层不是 list 时，拍平行为可能不符合预期（将单对象拍平为一行） | 中 | 需更多真实数据验证 |
| 5 | ~~单列 CSV（如 `Name\nAlice\nBob`）因 `_looks_like_csv` 要求最少 2 列而误判为 YAML~~ | 中 | ✅ 已修复 |
| 6 | ~~PyYAML 默认 width=80 导致长文本值在输出时被自动换行~~ | 低 | ✅ 已修复（width=4096） |

### 🔧 待改进

| # | 改进建议 | 优先级 |
|---|---------|--------|
| 1 | 增加 `--preview` 预览前 N 行的功能（JSON 树形、CSV 表格） | P1 |
| 2 | CSV 输出时列顺序目前基于所有行 keys 的并集，应该更稳定（按第一行输入顺序 + 追加新列） | P2 |
| 3 | 添加 `--encoding` 选项让用户显式指定输入编码 | P2 |
| 4 | JSON 数组拍平为列名时（如 `users_0_name`），不同长度的数组会导致不同的列集合 | P2 |
| 5 | 缺少集成测试（真实 API 管道场景） | P3 |

---

## 四、下一步计划

### 短期（本周）

1. **用户侧** ✅ 2026-06-12
   - [x] 确认/修改 `pyproject.toml` 中的 `authors` 和 `urls`
   - [x] 注册 PyPI 账号 + 创建 API token
   - [x] 用真实工作数据测试 morph
   - [x] 上传 TestPyPI 验证通过 ✔️

2. **明天（2026-06-13）计划**
   - [ ] **正式发布到 PyPI**（用正式 token）
   - [ ] 创建 GitHub 仓库 + 推送代码 + Git tag
   - [ ] 发布社区帖子：Reddit（r/Python, r/commandline）、Hacker News（Show HN）、V2EX
   - [ ] 收集反馈，决定 V2 功能优先级

### 开发者侧（已完成）
   - [x] 修复 Bug #1（`--no-flatten` CSV 值序列化为合法 JSON）— 已在之前完成
   - [x] 修复 Bug #5（单列 CSV 误识别为 YAML）— 2026-06-12 修改 `_looks_like_csv` 阈值从 `>1` 改为 `>=1`，增加 YAML key:value 误判防护
   - [x] 修复 Bug #6（YAML 长值自动换行）— 2026-06-12 `yaml.dump` 增加 `width=4096`

### 中期（2 周内）

3. **社区验证**
   - [ ] 准备 3 个社区帖子草稿（r/Python, r/commandline, Show HN）
   - [ ] 发布时间（周二-周四美东上午）
   - [ ] 收集并分类反馈

### 长期（视验证结果）

4. **V2 功能（待社区反馈定优先级）**
   - `morph merge` — 多文件合并（列自动对齐 + dry-run + undo）
   - `morph preview` — 终端美化预览
   - `morph filter` — 行过滤 + 字段选择
   - `--array-mode` — 数组转换模式：`columns`（当前行为，展开为多列）或 `rows`（展开为多行）[@已归档 V2 候选]

5. **货币化**
   - Gumroad 页面（$3.99 买断）
   - GitHub Pages Landing Page
   - 邮箱等待列表

---

## 五、项目文件清单

```
morph-cli/
├── morph/
│   ├── __init__.py          # v0.1.0
│   ├── cli.py               # Click CLI (convert 命令)
│   ├── converter.py         # 6 种转换路径 + flatten_dict
│   ├── detector.py          # JSON/CSV/YAML 自动检测
│   └── utils.py             # 编码检测 / 类型推断 / CSV 写
├── tests/
│   ├── __init__.py
│   ├── test_cli.py          # 19 tests
│   ├── test_converter.py    # 16 tests
│   ├── test_detector.py     # 11 tests
│   ├── test_utils.py        # 15 tests
│   └── fixtures/            # 8 fixtures
├── pyproject.toml
├── README.md
├── PROJECT_STATUS.md        # 本文件
├── HUMAN_TASKS.txt          # 用户侧任务清单
├── FLUX_PLAN.md             # 原始规划文档
├── CLAUDE.md                # Claude 角色约束
└── .gitignore
```

---

## 六、决策记录

| 决策 | 结论 | 日期 |
|------|------|------|
| 产品方向 | 数据格式转换，不做图片 | 2026-06-11 |
| 产品形态 | 独立 CLI 工具，做精做深 | 2026-06-11 |
| 商业模式 | CLI 免费获客 → 桌面版 Pro 收费 | 2026-06-11 |
| 包名 | `morph-cli`，命令 `morph` | 2026-06-11 |
| V1 范围 | 只做 `convert`，merge/filter 放 V2 | 2026-06-11 |
| 技术栈 | Python + Click + Rich（不用 Rust/Tauri） | 2026-06-11 |
| 验证路径 | 先发 HN / Reddit，再决定是否开 Gumroad | 2026-06-11 |
