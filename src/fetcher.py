"""GitHub API 数据抓取模块"""

import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
import yaml

from src.utils import load_dotenv

logger = logging.getLogger(__name__)


class GitHubFetcher:
    """封装 GitHub REST API，负责从指定仓库拉取各类数据。"""

    BASE_URL = "https://api.github.com"

    def __init__(self, config_path: str = "config/repos.yaml"):
        load_dotenv()

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.repos = self.config["repos"]
        self.per_page = self.config["github"].get("per_page", 100)
        self.max_pages = self.config["github"].get("max_pages", 5)
        self.token = os.environ.get("GITHUB_TOKEN")
        if self.token:
            logger.info("GitHub Token loaded (length: %d)", len(self.token))
        else:
            logger.warning("No GitHub Token found, using unauthenticated API (rate limited)")

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "LLM-Inference-Watch/1.0",
        })
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})

        proxy_url = os.environ.get("HTTP_PROXY", os.environ.get("PROXY_URL"))
        if proxy_url:
            self.session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            logger.info("Using proxy: %s", proxy_url)

    def _paginate(self, url: str, params: dict) -> list:
        """分页获取 API 数据，返回合并后的结果列表。"""
        all_items = []
        params["per_page"] = self.per_page
        params["page"] = 1

        for _ in range(self.max_pages):
            resp = self.session.get(url, params=params)
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_time - time.time(), 0) + 5
                logger.warning("Rate limit hit, waiting %d seconds...", wait)
                time.sleep(wait)
                continue

            if resp.status_code == 404:
                logger.warning("Resource not found: %s", url)
                break

            resp.raise_for_status()
            items = resp.json()
            if not items:
                break

            all_items.extend(items)
            params["page"] += 1
            time.sleep(0.2)  # 温和节流

        return all_items

    # ─── 仓库基本信息 ──────────────────────────────────────

    def get_repo_info(self, owner: str, repo: str) -> dict:
        """获取仓库基本信息（stars, forks, open_issues 等）。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    # ─── Commits ───────────────────────────────────────────

    def get_commits(self, owner: str, repo: str, since: Optional[datetime] = None) -> list:
        """获取仓库 commits，可选时间过滤。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {}
        if since:
            params["since"] = since.isoformat()
        return self._paginate(url, params)

    # ─── Issues ────────────────────────────────────────────

    def get_issues(self, owner: str, repo: str, since: Optional[datetime] = None) -> list:
        """获取 issues（不含 PR，GitHub API 中 PR 也是 issue）。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        params = {"state": "all", "sort": "updated", "direction": "desc"}
        if since:
            params["since"] = since.isoformat()

        all_issues = self._paginate(url, params)
        # 过滤掉 pull request（它们的 html_url 含 /pull/）
        return [i for i in all_issues if "pull_request" not in i]

    # ─── Pull Requests ─────────────────────────────────────

    def get_pull_requests(self, owner: str, repo: str, since: Optional[datetime] = None) -> list:
        """获取 pull requests（合并 PR API 和 Issues API 数据）。
        
        PR API 返回 merged_at 但不返回 comments。
        Issues API 返回 comments 但 merged_at 为 null。
        所以合并两个数据源。
        """
        # 1. 从 PR API 获取 PR 列表（包含 merged_at）
        pr_url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        pr_params = {"state": "all", "sort": "updated", "direction": "desc"}
        prs_from_api = self._paginate(pr_url, pr_params)
        
        # 2. 从 Issues API 获取 PR 的 comments
        issues_url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        issues_params = {"state": "all", "sort": "updated", "direction": "desc"}
        all_issues = self._paginate(issues_url, issues_params)
        prs_from_issues = {i["number"]: i for i in all_issues if "pull_request" in i}
        
        # 3. 合并数据：PR API 的 merged_at + Issues API 的 comments
        merged_prs = []
        for pr in prs_from_api:
            pr_number = pr.get("number")
            issue_data = prs_from_issues.get(pr_number, {})
            merged_pr = {
                **pr,
                "comments": issue_data.get("comments", 0),
            }
            merged_prs.append(merged_pr)
        
        # 4. 时间过滤
        if since:
            since_iso = since.isoformat()
            filtered = []
            for pr in merged_prs:
                if pr.get("updated_at", "") >= since_iso or pr.get("created_at", "") >= since_iso:
                    filtered.append(pr)
            return filtered
        return merged_prs

    # ─── Releases ──────────────────────────────────────────

    def get_releases(self, owner: str, repo: str, since: Optional[datetime] = None) -> list:
        """获取 releases。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/releases"
        params = {}
        all_releases = self._paginate(url, params)

        if since:
            return [r for r in all_releases
                    if r.get("published_at", "") >= since.isoformat()]
        return all_releases

    # ─── 批量获取 ──────────────────────────────────────────

    def fetch_all(self, since: datetime, mode: str = "light") -> dict:
        """批量获取所有配置仓库的数据快照。
        
        Args:
            since: 时间过滤起始点
            mode: light（轻量模式，过滤无关数据）或 full（全量模式，保留所有数据）
        """
        results = {}
        for full_name in self.repos:
            owner, repo = full_name.split("/")
            logger.info("Fetching %s/%s ...", owner, repo)

            try:
                repo_info = self.get_repo_info(owner, repo)
                commits = self.get_commits(owner, repo, since)
                issues = self.get_issues(owner, repo, since)
                pull_requests = self.get_pull_requests(owner, repo, since)
                releases = self.get_releases(owner, repo, since)

                if mode == "light":
                    commits = self._filter_commits(commits)
                    issues = self._filter_issues(issues)
                    pull_requests = self._filter_prs(pull_requests)
                    repo_info = self._filter_repo_info(repo_info)

                results[full_name] = {
                    "info": repo_info,
                    "commits": commits,
                    "issues": issues,
                    "pull_requests": pull_requests,
                    "releases": releases,
                }
            except Exception as e:
                logger.error("Failed to fetch %s: %s", full_name, e)
                results[full_name] = {"error": str(e)}

        return results

    @staticmethod
    def _filter_commits(commits: list) -> list:
        """轻量模式下过滤 commits：过滤 CI/Docs 等非核心提交，保留关键字段。"""
        ignore_keywords = ["ci", "docs", "documentation", "readme", "changelog", "typo",
                           "spelling", "lint", "format", "style", "docker", "infra",
                           "workflow", "test", "coverage", "bump", "version", "lock"]

        filtered = []
        for commit in commits:
            message = commit.get("commit", {}).get("message", "").lower()
            if any(kw in message for kw in ignore_keywords):
                continue

            filtered.append({
                "sha": commit.get("sha", ""),
                "message": commit.get("commit", {}).get("message", ""),
                "author": commit.get("commit", {}).get("author", {}).get("name", ""),
                "html_url": commit.get("html_url", ""),
                "committed_date": commit.get("commit", {}).get("committed_date", ""),
            })

        return filtered

    @staticmethod
    def _filter_issues(issues: list) -> list:
        """轻量模式下过滤 issues：保留关键字段（不限制数量）。"""
        filtered = []
        for issue in issues:
            filtered.append({
                "number": issue.get("number"),
                "title": issue.get("title", ""),
                "state": issue.get("state", ""),
                "comments": issue.get("comments", 0),
                "user": issue.get("user", {}).get("login", ""),
                "html_url": issue.get("html_url", ""),
                "created_at": issue.get("created_at", ""),
                "labels": issue.get("labels", []),
            })
        return filtered

    @staticmethod
    def _filter_prs(pull_requests: list) -> list:
        """轻量模式下过滤 PRs：保留关键字段（不限制数量）。"""
        filtered = []
        for pr in pull_requests:
            filtered.append({
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "state": pr.get("state", ""),
                "comments": pr.get("comments", 0) + pr.get("review_comments", 0),
                "user": pr.get("user", {}).get("login", ""),
                "html_url": pr.get("html_url", ""),
                "created_at": pr.get("created_at", ""),
                "merged_at": pr.get("merged_at", ""),
                "labels": pr.get("labels", []),
            })
        return filtered

    @staticmethod
    def _filter_repo_info(info: dict) -> dict:
        """轻量模式下过滤仓库信息：仅保留必要字段。"""
        return {
            "stargazers_count": info.get("stargazers_count", 0),
            "forks_count": info.get("forks_count", 0),
            "open_issues_count": info.get("open_issues_count", 0),
            "description": info.get("description", ""),
            "updated_at": info.get("updated_at", ""),
        }

    def fetch_basic_stats(self) -> dict:
        """轻量获取：仅拉取各仓库 stars/forks/open_issues 统计。"""
        results = {}
        for full_name in self.repos:
            owner, repo = full_name.split("/")
            try:
                info = self.get_repo_info(owner, repo)
                results[full_name] = {
                    "stars": info.get("stargazers_count", 0),
                    "forks": info.get("forks_count", 0),
                    "open_issues": info.get("open_issues_count", 0),
                    "description": info.get("description", ""),
                }
            except Exception as e:
                logger.error("Failed to fetch stats for %s: %s", full_name, e)
                results[full_name] = {"error": str(e)}
        return results
