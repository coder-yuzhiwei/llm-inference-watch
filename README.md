# LLM-Inference-Watch 🔍

> 自动追踪主流 LLM 推理引擎开源仓库的最新动态，生成每日简报，并支持 AI 智能分析（按时间范围灵活分析）。

[![Daily Report](https://github.com/your-username/llm-inference-watch/actions/workflows/daily.yml/badge.svg)](https://github.com/your-username/llm-inference-watch/actions/workflows/daily.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📡 监控仓库

| 仓库 | 描述 | Stars |
|------|------|-------|
| [vllm-project/vllm](https://github.com/vllm-project/vllm) | 高吞吐量 LLM 推理引擎 | ![Stars](https://img.shields.io/github/stars/vllm-project/vllm) |
| [sgl-project/sglang](https://github.com/sgl-project/sglang) | 结构化生成语言与高效推理框架 | ![Stars](https://img.shields.io/github/stars/sgl-project/sglang) |
| [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | NVIDIA 官方 LLM 推理优化库 | ![Stars](https://img.shields.io/github/stars/NVIDIA/TensorRT-LLM) |
| [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) | C/C++ 实现的轻量级 LLM 推理 | ![Stars](https://img.shields.io/github/stars/ggerganov/llama.cpp) |

---

## 🔄 运行流程

### 一、数据采集流程（每日定时）

```
┌─────────────────────────────────────────────────────────────────┐
│                    python src/scheduler.py daily                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. GitHubFetcher 拉取数据（过去 24 小时）                        │
│     - commits / issues / pull_requests / releases / repo info   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Analyzer 分类统计                                           │
│     - commit 分类 (feature/performance/model_support/kernel...) │
│     - 提取 notable items (comments >= 3 且非 bug)               │
│     - 统计作者贡献                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 保存数据到 data/daily/YYYY-MM-DD.json                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. MarkdownReporter 生成报告到 reports/daily/                   │
└─────────────────────────────────────────────────────────────────┘
```

### 二、AI 分析流程（手动触发）

```
┌─────────────────────────────────────────────────────────────────┐
│              python src/ai_scheduler.py analyze --days 7        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 收集数据                                               │
│  - 读取 data/daily/ 下最近 N 天的 JSON 文件                     │
│  - 合并多日数据（去重，保留最新状态）                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: AI 筛选（第一步调用 AI）                               │
│  - 构建筛选数据（只有标题，按配置 input_limit 限制）              │
│  - AI 返回选中的 issue/PR 编号和理由                             │
│  - 将 ai_selected 标记写回 daily JSON 文件                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: 获取详情                                               │
│  - 根据 AI 选中的编号，调用 GitHub API 拉取完整 body             │
│  - 生成 detailed_data                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: AI 生成报告（第二步调用 AI）                           │
│  - 传入统计数据 + 选中项详情                                     │
│  - 保存到 reports/ai/YYYY-MM-DD.md                              │
└─────────────────────────────────────────────────────────────────┘
```

### 三、关键设计点

| 设计点 | 说明 |
|--------|------|
| **两步 AI** | 先筛选（只看标题）→ 再拉详情 → 最后生成报告，避免 AI 基于标题幻觉 |
| **去重机制** | 合并多日数据时，同一 issue/PR 只保留一条最新记录 |
| **动态数量** | 每个仓库最多选 `分析天数 × 2` 个 item |
| **数据分级** | daily JSON 是原始分析数据，报告是最终产物 |

---

## 🚀 快速开始

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/your-username/llm-inference-watch.git
cd llm-inference-watch

# 安装依赖
pip install -r requirements.txt

# 生成每日报告（自动保存数据到 data/daily/）
python src/scheduler.py daily

# AI 深度分析（默认分析最近 7 天）
python src/ai_scheduler.py analyze

# AI 深度分析报告（分析最近 N 天）
python src/ai_scheduler.py analyze --days 14

# 列出可用的数据
python src/ai_scheduler.py list
```

> **提示**：详细的本地开发指南请查看 [AGENTS.md](AGENTS.md)。

### GitHub Actions 自动运行

项目已配置 GitHub Actions，每天 UTC 16:00（北京时间次日 00:00）自动运行：

```yaml
# .github/workflows/daily.yml
on:
  schedule:
    - cron: "0 16 * * *"  # 每天 UTC 16:00
  workflow_dispatch:  # 允许手动触发
```

---

## 🔧 环境配置

### 使用 .env 文件（推荐）

创建 `.env` 文件，统一管理环境变量：

```env
# GitHub API Token（提高 API 速率限制）
GITHUB_TOKEN=your-github-token

# AI API 配置（支持 OpenAI、DeepSeek 等 OpenAI 兼容 API）
AI_API_KEY=your-api-key
AI_API_BASE=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
```

> **本地代理**：如需本地代理访问 GitHub，通过环境变量设置，不要写入 .env 文件：
> ```powershell
> $env:HTTP_PROXY="http://127.0.0.1:7897"
> $env:HTTPS_PROXY="http://127.0.0.1:7897"
> ```

### AI API 配置

| API 提供商 | API_BASE | 模型名称 |
|-----------|----------|---------|
| DeepSeek | `https://api.deepseek.com` | `deepseek-v4-flash`, `deepseek-v4-pro` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4-turbo` |

> **注意：** DeepSeek 的 `deepseek-chat` 和 `deepseek-reasoner` 模型将于 2026/07/24 弃用，请使用新模型 `deepseek-v4-flash` 或 `deepseek-v4-pro`。

---

## 📁 项目结构

```
llm-inference-watch/
├── config/
│   ├── repos.yaml              # 监控仓库配置
│   └── prompts/                # AI 提示词模板
│       ├── step1_filter.txt    # 第一步：AI 筛选提示词
│       └── step2_analyze.txt   # 第二步：AI 分析提示词
├── data/
│   └── daily/                  # 每日分析数据（用于 AI 分析）
│       ├── 2026-06-09.json
│       ├── 2026-06-10.json
│       └── ...
├── src/
│   ├── __init__.py
│   ├── fetcher.py              # GitHub API 数据抓取
│   ├── analyzer.py             # 数据分类与统计分析
│   ├── reporter.py             # Markdown 报告生成
│   ├── scheduler.py            # 每日报告调度器
│   ├── ai_analyzer.py          # AI 智能分析模块
│   ├── ai_scheduler.py         # AI 分析调度器
│   └── utils.py                # 通用工具
├── tests/
│   └── test_main.py            # 单元测试
├── reports/
│   ├── daily/                  # 每日简报存档
│   └── ai/                     # AI 分析报告存档
├── .github/workflows/
│   └── daily.yml               # 每日定时任务
├── .env                        # 环境变量配置
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🧪 运行测试

```bash
# 运行所有测试
python -m pytest tests/test_main.py -v

# 运行特定测试类
python -m pytest tests/test_main.py::TestAIAnalysis -v
```

---

## 🧩 数据维度

| 维度 | 说明 |
|------|------|
| **Commits** | 提交数量、作者分布、变更分类（feature/bug/perf/model 等） |
| **Issues** | 新增问题、热门讨论、标签分类 |
| **Pull Requests** | 新 PR、合并/关闭统计、高互动 PR 追踪 |
| **Releases** | 版本发布记录与 changelog 摘要 |
| **Stars/Forks** | 社区增长指标 |

### 变更分类标签

| 标签 | 含义 |
|------|------|
| 🐛 bug | Bug 修复 |
| ✨ feature | 新功能 |
| ⚡ performance | 性能优化 |
| 🧠 model_support | 新模型支持 |
| 🔥 kernel | CUDA/Triton kernel 优化 |
| 🔌 api | API/接口变更 |
| 🌐 distributed | 分布式推理 |
| ♻️ refactor | 重构 |
| 📚 ci_docs | CI/文档 |

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 数据来源：[GitHub REST API](https://docs.github.com/en/rest)
- AI 分析：支持 OpenAI、DeepSeek 等 API
- 灵感来自各类开源生态观察项目