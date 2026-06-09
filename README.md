# LLM-Inference-Watch 🔍

> 自动追踪主流 LLM 推理引擎开源仓库的最新动态，生成每日简报、每周深度报告和每月趋势总结。

[![Daily Report](https://github.com/your-username/llm-inference-watch/actions/workflows/daily.yml/badge.svg)](https://github.com/your-username/llm-inference-watch/actions/workflows/daily.yml)
[![Weekly Report](https://github.com/your-username/llm-inference-watch/actions/workflows/weekly.yml/badge.svg)](https://github.com/your-username/llm-inference-watch/actions/workflows/weekly.yml)
[![Monthly Report](https://github.com/your-username/llm-inference-watch/actions/workflows/monthly.yml/badge.svg)](https://github.com/your-username/llm-inference-watch/actions/workflows/monthly.yml)
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
- 一屏概览，快速了解当天动态

### 📰 每周深度报告 (Weekly Digest)
- 本周关键变更深度解读（按仓库分类）
- 社区讨论热点（高互动 issue/PR）
- 贡献者活跃度排行
- 跨仓库对比分析

### 📊 每月趋势总结 (Monthly Review)
- 月度关键指标趋势分析
- 重大架构/特性变更回顾
- 生态趋势洞察
- 下月关注预测

---

## 🚀 快速开始

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/your-username/llm-inference-watch.git
cd llm-inference-watch

# 安装依赖
pip install -r requirements.txt

# 设置 GitHub Token（可选，但强烈推荐以提高 API 速率限制）
export GITHUB_TOKEN=your_github_token

# 生成报告
python src/scheduler.py daily      # 每日简报
python src/scheduler.py weekly     # 每周深度报告
python src/scheduler.py monthly    # 每月趋势总结
```

### GitHub Actions 自动运行

项目已配置 GitHub Actions，推送到 GitHub 后自动按以下节奏运行：

| 报告类型 | 执行时间 (UTC) | 执行时间 (北京时间) |
|---------|---------------|-------------------|
| 每日简报 | 每天 16:00 | 每天 00:00 |
| 每周深度 | 每周一 00:00 | 每周一 08:00 |
| 每月总结 | 每月 1 号 00:00 | 每月 1 号 08:00 |

> **注意：** 需要在仓库 Settings → Secrets and variables → Actions 中设置 `GITHUB_TOKEN` secret，或者使用 GitHub Actions 自动提供的 `${{ secrets.GITHUB_TOKEN }}`。

---

## 📁 项目结构

```
llm-inference-watch/
├── config/
│   └── repos.yaml              # 监控仓库配置（可自定义添加仓库）
├── src/
│   ├── __init__.py
│   ├── fetcher.py              # GitHub API 数据抓取
│   ├── analyzer.py             # 数据分类与统计分析
│   ├── reporter.py             # Markdown 报告生成（日/周/月）
│   └── scheduler.py            # 调度入口
├── reports/
│   ├── daily/                  # 每日简报存档
│   ├── weekly/                 # 每周深度报告
│   └── monthly/                # 每月趋势总结
├── .github/workflows/
│   ├── daily.yml               # 每日定时任务
│   ├── weekly.yml              # 每周定时任务
│   └── monthly.yml             # 每月定时任务
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🔧 自定义配置

编辑 `config/repos.yaml` 可添加或修改监控仓库：

```yaml
repos:
  - vllm-project/vllm
  - sgl-project/sglang
  - NVIDIA/TensorRT-LLM
  - ggerganov/llama.cpp
  # 添加更多仓库...
  # - your-org/your-repo
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
- 灵感来自各类开源生态观察项目
