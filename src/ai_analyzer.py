"""AI 智能分析模块 — 对周报数据进行深度分析，提取推理引擎发展趋势"""

import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

import yaml

from src.utils import load_dotenv

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """从分析后的数据中提取值得关注的变更。"""

    IGNORED_CATEGORIES = ["ci_docs", "refactor", "other"]

    def __init__(self, config_path: str = "config/repos.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.repos = self.config["repos"]

    def extract_notable_changes(self, analysis_results: Dict) -> Dict:
        """从分析结果中提取值得关注的变更。"""
        notable_data = {
            "repos": {},
            "releases": [],
            "hot_topics": [],
        }

        for repo_name, repo_data in analysis_results.items():
            if "error" in repo_data:
                continue

            repo_notable = {
                "key_commits": [],
                "notable_prs": [],
                "notable_issues": [],
                "category_distribution": {},
                "releases": [],
            }

            # 提取关键 commits（过滤掉 CI/Docs 等）
            key_commits = repo_data.get("commits", {}).get("key_commits", [])
            for commit in key_commits[:10]:
                message = commit.get("message", "")
                if self._is_notable_commit(message):
                    repo_notable["key_commits"].append({
                        "sha": commit.get("sha", ""),
                        "url": commit.get("html_url", ""),
                        "message": message,
                        "author": commit.get("author", "unknown"),
                        "category": self._classify_commit(message),
                    })

            # 提取高互动 PR
            notable_prs = repo_data.get("pull_requests", {}).get("notable", [])
            for pr in notable_prs[:5]:
                if pr.get("comments", 0) >= 5 or pr.get("state") == "merged":
                    repo_notable["notable_prs"].append({
                        "number": pr.get("number"),
                        "title": pr.get("title", ""),
                        "url": pr.get("html_url", ""),
                        "user": pr.get("user", ""),
                        "comments": pr.get("comments", 0),
                        "state": pr.get("state", ""),
                        "category": pr.get("category", ""),
                    })

            # 提取高互动 issues
            notable_issues = repo_data.get("issues", {}).get("notable", [])
            for issue in notable_issues[:5]:
                if issue.get("comments", 0) >= 10:
                    repo_notable["notable_issues"].append({
                        "number": issue.get("number"),
                        "title": issue.get("title", ""),
                        "url": issue.get("html_url", ""),
                        "user": issue.get("user", ""),
                        "comments": issue.get("comments", 0),
                        "state": issue.get("state", ""),
                    })

            # 类别分布（过滤掉不重要的类别）
            categories = repo_data.get("commits", {}).get("by_category", {})
            for cat, count in categories.items():
                if cat not in self.IGNORED_CATEGORIES:
                    repo_notable["category_distribution"][cat] = count

            # Releases
            releases = repo_data.get("releases", [])
            for rel in releases[:3]:
                repo_notable["releases"].append({
                    "tag": rel.get("tag_name", ""),
                    "name": rel.get("name", ""),
                    "url": rel.get("html_url", ""),
                    "body": rel.get("body", "")[:500] if rel.get("body") else "",
                })

            notable_data["repos"][repo_name] = repo_notable

        return notable_data

    def _is_notable_commit(self, message: str) -> bool:
        """判断 commit 是否值得关注。"""
        msg_lower = message.lower()
        ignore_keywords = ["ci", "docs", "documentation", "readme", "changelog", "typo",
                           "spelling", "lint", "format", "style", "docker", "infra",
                           "workflow", "test", "coverage", "bump", "version", "lock"]

        for kw in ignore_keywords:
            if kw in msg_lower:
                return False

        return True

    def _classify_commit(self, message: str) -> str:
        """简单的 commit 分类。"""
        msg_lower = message.lower()
        categories = {
            "performance": ["perf", "performance", "optimize", "speed", "throughput", "latency", "memory", "throughput"],
            "model_support": ["model", "support", "architecture", "llama", "mistral", "qwen", "deepseek", "gemma", "mixtral", "moe"],
            "kernel": ["kernel", "cuda", "triton", "flash", "attention", "gemm", "fused"],
            "feature": ["feat", "feature", "add", "implement", "introduce", "enable"],
            "bug": ["fix", "bug", "hotfix", "crash", "error", "regression"],
            "api": ["api", "endpoint", "server", "rest", "openai", "compatible"],
            "distributed": ["distributed", "tensor parallel", "pipeline parallel", "multi-node", "tp", "dp"],
        }

        for cat, keywords in categories.items():
            if any(kw in msg_lower for kw in keywords):
                return cat

        return "other"


class AIAnalyzer:
    """调用 AI 进行深度分析，提取推理引擎发展趋势。"""

    def __init__(self, config_path: str = "config/repos.yaml"):
        load_dotenv()

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.data_analyzer = DataAnalyzer(config_path)
        self.api_key = os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.api_base = os.environ.get("AI_API_BASE")
        self.model = os.environ.get("AI_MODEL") or "deepseek-v4-flash"

        if not self.api_key:
            logger.warning("AI_API_KEY 或 OPENAI_API_KEY 未设置，将使用模拟分析模式")

    def analyze_from_data(self, data_path: str) -> Dict:
        """从分析数据文件中进行 AI 分析。"""
        logger.info("Loading analyzed data from: %s", data_path)
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        analysis_results = data.get("analysis_results", {})
        cross_summary = data.get("cross_summary", {})
        report_type = data.get("report_type", "weekly")
        generated_at = data.get("generated_at", "")

        if generated_at:
            report_date = datetime.fromisoformat(generated_at)
        else:
            report_date = datetime.now(timezone.utc)

        week_num = report_date.isocalendar()[1]

        # 提取值得关注的变更
        notable_data = self.data_analyzer.extract_notable_changes(analysis_results)
        notable_data["date"] = report_date.strftime("%Y-%m-%d")
        notable_data["week"] = str(week_num)
        notable_data["report_type"] = report_type

        if not self.api_key:
            logger.info("No AI API key found, using mock analysis")
            return self._mock_analysis(notable_data)

        return self._call_ai_analysis(notable_data)

    def analyze_from_merged_data(self, merged_data: Dict) -> Dict:
        """从合并后的多日数据中进行 AI 分析。"""
        analysis_results = merged_data.get("analysis_results", {})
        date_range = merged_data.get("date_range", {})

        start_date = date_range.get("start", "")
        end_date = date_range.get("end", "")
        days = date_range.get("days", 0)

        # 提取值得关注的变更
        notable_data = self.data_analyzer.extract_notable_changes(analysis_results)
        notable_data["date"] = end_date
        notable_data["date_range"] = f"{start_date} ~ {end_date}"
        notable_data["days"] = days
        notable_data["report_type"] = "merged"

        if not self.api_key:
            logger.info("No AI API key found, using mock analysis")
            return self._mock_analysis(notable_data)

        return self._call_ai_analysis(notable_data)

    def _build_prompt(self, notable_data: Dict) -> str:
        """构建 AI 分析的 prompt，从模板文件加载。"""
        date_range = notable_data.get("date_range", notable_data.get("date", ""))
        days = notable_data.get("days", 1)

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "prompt_template.txt"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        repo_data = ""
        for repo_name, repo_info in notable_data["repos"].items():
            repo_data += f"\n### {repo_name}\n\n"

            if repo_info["key_commits"]:
                repo_data += "**关键变更（按重要性排序）：**\n"
                for commit in repo_info["key_commits"]:
                    repo_data += f"- [{commit['sha']}] {commit['message']} ({commit['category']})\n"
                repo_data += "\n"

            if repo_info["notable_prs"]:
                repo_data += "**高互动/已合并 PR：**\n"
                for pr in repo_info["notable_prs"]:
                    state_icon = "✅" if pr["state"] == "merged" else "🔄"
                    repo_data += f"- {state_icon} #{pr['number']}: {pr['title']} (@{pr['user']}, 💬{pr['comments']}, {pr['category']})\n"
                repo_data += "\n"

            if repo_info["releases"]:
                repo_data += "**新版本发布：**\n"
                for rel in repo_info["releases"]:
                    repo_data += f"- {rel['tag']}: {rel['name']}\n"
                    if rel["body"]:
                        repo_data += f"  > {rel['body'][:200]}...\n"
                repo_data += "\n"

            if repo_info["notable_issues"]:
                repo_data += "**高互动 Issues：**\n"
                for issue in repo_info["notable_issues"]:
                    repo_data += f"- #{issue['number']}: {issue['title']} (@{issue['user']}, 💬{issue['comments']})\n"
                repo_data += "\n"

            if repo_info["category_distribution"]:
                repo_data += "**变更类别分布：**\n"
                for cat, count in repo_info["category_distribution"].items():
                    repo_data += f"- {cat}: {count}\n"
                repo_data += "\n"

        prompt = template.format(
            date_range=date_range,
            days=days,
            repo_data=repo_data,
        )

        return prompt

    def _call_ai_analysis(self, notable_data: Dict) -> Dict:
        """调用 AI API 进行分析。"""
        prompt = self._build_prompt(notable_data)

        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base if self.api_base else None,
            )

            logger.info("Calling AI API for analysis (model: %s)...", self.model)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个资深的 LLM 推理引擎技术分析师，擅长从代码变更中提取技术趋势。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            )

            return {
                "success": True,
                "content": response.choices[0].message.content.strip(),
                "date": notable_data.get("date_range", notable_data.get("date", "")),
                "mode": "AI",
            }

        except ImportError:
            logger.error("openai 库未安装，请运行 pip install openai")
            return self._mock_analysis(notable_data)
        except Exception as e:
            logger.error("AI API 调用失败: %s", e)
            return self._mock_analysis(notable_data)

    def _mock_analysis(self, notable_data: Dict) -> Dict:
        """模拟 AI 分析结果。"""
        date_range = notable_data.get("date_range", notable_data.get("date", ""))
        days = notable_data.get("days", 1)

        content = f"""# 🤖 LLM 推理引擎 AI 深度分析报告

> 📅 {date_range}（共 {days} 天）

## 一、核心趋势

**注意：** 此为模拟分析结果。设置 AI_API_KEY 环境变量以启用真实 AI 分析。

- 当前各推理引擎普遍关注性能优化，尤其是针对 Blackwell 架构的适配
- 新模型支持持续扩展，特别是 MoE 和多模态模型
- 分布式推理方案逐渐成熟，成为大型部署的关键技术

## 二、各仓库深度分析

"""

        for repo_name, repo_data in notable_data["repos"].items():
            content += f"""### {repo_name}

**重点关注：**
"""
            if repo_data["key_commits"]:
                for commit in repo_data["key_commits"][:3]:
                    content += f"- {commit['message']} ({commit['category']})\n"
            else:
                content += "- 暂无值得关注的核心变更\n"

            if repo_data["notable_prs"]:
                content += f"\n**重要 PR：**\n"
                for pr in repo_data["notable_prs"][:2]:
                    content += f"- #{pr['number']}: {pr['title']} ({pr['state']})\n"

            if repo_data["releases"]:
                content += f"\n**新版本发布：**\n"
                for rel in repo_data["releases"]:
                    content += f"- {rel['tag']}\n"

            content += "\n---\n\n"

        content += f"""## 三、跨仓库趋势对比

本周各仓库均有活跃开发，主要集中在性能优化和新特性开发。

## 四、生态趋势预测

基于当前动态，未来值得关注：
- GPU 架构优化（特别是 Blackwell/Hopper）
- MoE 模型推理效率提升
- 多模态推理能力扩展

## 五、值得关注的 PR/Issue

"""

        for repo_name, repo_data in notable_data["repos"].items():
            if repo_data["notable_prs"]:
                for pr in repo_data["notable_prs"][:2]:
                    content += f"- [{repo_name}] #{pr['number']}: {pr['title']}\n"

        content += "\n---\n\n*📬 本报告由 AI 智能分析生成（模拟模式）*"

        return {
            "success": True,
            "content": content,
            "date": notable_data.get("date_range", notable_data.get("date", "")),
            "mode": "mock",
        }

    def list_analyzed_data(self, report_type: str = "weekly") -> List[str]:
        """列出可用的分析数据文件。"""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "analyzed")
        if not os.path.exists(data_dir):
            return []

        files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)
        filtered = []
        for f in files:
            if report_type == "weekly" and "-W" in f:
                filtered.append(os.path.join(data_dir, f))
            elif report_type == "daily" and "-W" not in f and len(f) == 15:  # YYYY-MM-DD.json
                filtered.append(os.path.join(data_dir, f))
            elif report_type == "monthly" and len(f) == 11:  # YYYY-MM.json
                filtered.append(os.path.join(data_dir, f))

        return filtered if filtered else [os.path.join(data_dir, f) for f in files]
