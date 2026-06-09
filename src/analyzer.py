"""数据分析与分类模块"""

import re
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class ChangeClassifier:
    """对 commits / issues / PRs 进行语义分类。"""

    # Commit message 关键词 -> 分类标签
    COMMIT_CATEGORIES = {
        "bug": ["fix", "bug", "hotfix", "crash", "error", "regression", "segfault"],
        "feature": ["feat", "feature", "add", "support", "implement", "introduce"],
        "performance": ["perf", "performance", "optimize", "optimization", "speed", "faster",
                        "throughput", "latency", "memory", "cuda graph", "triton kernel"],
        "model_support": ["model", "architecture", "llama", "mistral", "qwen", "deepseek",
                          "gemma", "phi", "falcon", "mixtral", "moe", "quantization", "gguf"],
        "refactor": ["refactor", "cleanup", "rewrite", "restructure", "simplify"],
        "ci_docs": ["ci", "docs", "documentation", "readme", "changelog", "typo", "spelling",
                    "lint", "format", "style"],
        "kernel": ["kernel", "triton", "cuda", "flash", "attention", "gemm", "fused"],
        "api": ["api", "endpoint", "server", "rest", "openai", "compatible"],
        "distributed": ["distributed", "tp", "tensor parallel", "pipeline parallel", "dp",
                        "multi-node", "ray", "nccl"],
    }

    ISSUE_LABEL_MAP = {
        "bug": "bug",
        "feature request": "feature",
        "enhancement": "feature",
        "performance": "performance",
        "documentation": "ci_docs",
        "good first issue": "community",
        "help wanted": "community",
        "question": "discussion",
    }

    @classmethod
    def classify_commit(cls, message: str) -> str:
        """根据 commit message 分类。"""
        msg_lower = message.lower()
        for category, keywords in cls.COMMIT_CATEGORIES.items():
            if any(kw in msg_lower for kw in keywords):
                return category
        return "other"

    @classmethod
    def classify_issue(cls, issue: dict) -> str:
        """根据 issue labels 分类。"""
        labels = [l["name"].lower() for l in issue.get("labels", [])]
        for label, category in cls.ISSUE_LABEL_MAP.items():
            if label in labels:
                return category
        # 根据标题关键词推测
        title = issue.get("title", "").lower()
        for category, keywords in cls.COMMIT_CATEGORIES.items():
            if any(kw in title for kw in keywords):
                return category
        return "other"

    @classmethod
    def classify_pr(cls, pr: dict) -> str:
        """根据 PR 标题和标签分类。"""
        labels = [l["name"].lower() for l in pr.get("labels", [])]
        for label, category in cls.ISSUE_LABEL_MAP.items():
            if label in labels:
                return category
        title = pr.get("title", "").lower()
        return cls.classify_commit(title)


class Analyzer:
    """汇总分析模块：统计数据、计算趋势、提取高亮项。"""

    def __init__(self):
        self.classifier = ChangeClassifier()

    def analyze_repo(self, repo_data: dict, repo_name: str) -> dict:
        """分析单个仓库的数据。"""
        if "error" in repo_data:
            return {"name": repo_name, "error": repo_data["error"]}

        commits = repo_data.get("commits", [])
        issues = repo_data.get("issues", [])
        prs = repo_data.get("pull_requests", [])
        releases = repo_data.get("releases", [])
        info = repo_data.get("info", {})

        # Commit 分类统计
        commit_categories = Counter()
        commit_authors = Counter()
        for c in commits:
            msg = c.get("commit", {}).get("message", "")
            cat = self.classifier.classify_commit(msg)
            commit_categories[cat] += 1
            author = c.get("commit", {}).get("author", {}).get("name", "unknown")
            commit_authors[author] += 1

        # Issue 分类统计
        issue_categories = Counter()
        for i in issues:
            cat = self.classifier.classify_issue(i)
            issue_categories[cat] += 1

        # PR 分类统计
        pr_categories = Counter()
        pr_merged = 0
        pr_open = 0
        pr_closed = 0
        notable_prs = []
        for pr in prs:
            cat = self.classifier.classify_pr(pr)
            pr_categories[cat] += 1

            if pr.get("merged_at"):
                pr_merged += 1
            elif pr.get("state") == "open":
                pr_open += 1
            else:
                pr_closed += 1

            # 标记高互动 PR
            comments = pr.get("comments", 0) + pr.get("review_comments", 0)
            if comments >= 5:
                notable_prs.append({
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "html_url": pr.get("html_url"),
                    "user": pr.get("user", {}).get("login", ""),
                    "comments": comments,
                    "state": "merged" if pr.get("merged_at") else pr.get("state"),
                    "category": cat,
                })

        notable_prs.sort(key=lambda x: x["comments"], reverse=True)

        # 高互动 issue
        notable_issues = []
        for i in issues:
            if i.get("comments", 0) >= 3:
                notable_issues.append({
                    "number": i.get("number"),
                    "title": i.get("title"),
                    "html_url": i.get("html_url"),
                    "user": i.get("user", {}).get("login", ""),
                    "comments": i.get("comments", 0),
                    "state": i.get("state"),
                })
        notable_issues.sort(key=lambda x: x["comments"], reverse=True)

        # Releases
        recent_releases = []
        for r in releases:
            recent_releases.append({
                "tag_name": r.get("tag_name"),
                "name": r.get("name"),
                "html_url": r.get("html_url"),
                "published_at": r.get("published_at"),
                "body": (r.get("body") or "")[:300],
            })

        # 提取 commit 中的关键变更（非 trivial 的 commit）
        key_commits = []
        for c in commits:
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            if len(msg) > 10 and not msg.lower().startswith(("merge", "bump", "chore", "typo", "nit")):
                key_commits.append({
                    "sha": c.get("sha", "")[:7],
                    "message": msg[:120],
                    "html_url": c.get("html_url"),
                    "author": c.get("commit", {}).get("author", {}).get("name", "unknown"),
                })

        return {
            "name": repo_name,
            "info": {
                "stars": info.get("stargazers_count", 0),
                "forks": info.get("forks_count", 0),
                "open_issues": info.get("open_issues_count", 0),
                "description": info.get("description", ""),
            },
            "commits": {
                "total": len(commits),
                "by_category": dict(commit_categories.most_common()),
                "top_authors": dict(commit_authors.most_common(10)),
                "key_commits": key_commits[:15],
            },
            "issues": {
                "total": len(issues),
                "by_category": dict(issue_categories.most_common()),
                "notable": notable_issues[:10],
            },
            "pull_requests": {
                "total": len(prs),
                "merged": pr_merged,
                "open": pr_open,
                "closed": pr_closed,
                "by_category": dict(pr_categories.most_common()),
                "notable": notable_prs[:10],
            },
            "releases": recent_releases[:5],
        }

    def cross_repo_summary(self, analysis_results: dict) -> dict:
        """跨仓库对比汇总。"""
        repos_summary = []
        total_stars = 0
        total_commits = 0
        total_issues = 0
        total_prs = 0
        total_releases = 0

        for name, result in analysis_results.items():
            if "error" in result:
                repos_summary.append({"name": name, "error": result["error"]})
                continue

            repos_summary.append({
                "name": name,
                "stars": result["info"]["stars"],
                "commits": result["commits"]["total"],
                "issues": result["issues"]["total"],
                "prs": result["pull_requests"]["total"],
                "prs_merged": result["pull_requests"]["merged"],
                "releases": len(result["releases"]),
            })
            total_stars += result["info"]["stars"]
            total_commits += result["commits"]["total"]
            total_issues += result["issues"]["total"]
            total_prs += result["pull_requests"]["total"]
            total_releases += len(result["releases"])

        # 按活跃度排序
        repos_summary.sort(key=lambda x: x.get("commits", 0), reverse=True)

        return {
            "repos": repos_summary,
            "totals": {
                "stars": total_stars,
                "commits": total_commits,
                "issues": total_issues,
                "prs": total_prs,
                "releases": total_releases,
            },
        }
