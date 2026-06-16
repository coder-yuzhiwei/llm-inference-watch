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

## 📊 报告体系

### 🔍 每日简报 (Daily Brief)
- 过去 24 小时各仓库新增 commits / issues / PRs 数量
- 重要 PR 合并与新 Release 高亮
- 每日自动生成并提交到 Git

### 🤖 AI 深度分析报告 (AI Analysis)
- 读取最近 N 天的数据进行深度分析（灵活选择时间范围）
- 智能过滤非核心变更（CI/文档/测试等）
- 提取推理引擎最新发展趋势
- 跨仓库技术对比与生态预测
- 支持 OpenAI/DeepSeek 等 API

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
│   └── repos.yaml              # 监控仓库配置
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
