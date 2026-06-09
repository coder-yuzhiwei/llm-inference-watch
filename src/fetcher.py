"""GitHub API 数据抓取模块"""

import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
import yaml

logger = logging.getLogger(__name__)


class GitHubFetcher:
    """封装 GitHub REST API，负责从指定仓库拉取各类数据。"""

    BASE_URL = "https://api.github.com"

    def __init__(self, config_path: str = "config/repos.yaml"):
        # 加载 .env 文件中的环境变量
        self._load_dotenv()

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.repos = self.config["repos"]
        self.per_page = self.config["github"].get("per_page", 100)
        self.max_pages = self.config["github"].get("max_pages", 5)
        self.token = os.environ.get("GITHUB_TOKEN")

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "LLM-Inference-Watch/1.0",
        })
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})

    @staticmethod
    def _load_dotenv():
        """加载项目根目录的 .env 文件到环境变量。"""
        import os as _os
        env_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".env")
        if _os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        if key.strip() not in _os.environ:
                            _os.environ[key.strip()] = value.strip()

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
        """获取 pull requests。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": "all", "sort": "updated", "direction": "desc"}
        # GitHub PR API 不支持 since 参数，我们手动分页过滤
        all_prs = self._paginate(url, params)

        if since:
            since_iso = since.isoformat()
            filtered = []
            for pr in all_prs:
                if pr.get("updated_at", "") >= since_iso or pr.get("created_at", "") >= since_iso:
                    filtered.append(pr)
                else:
                    # 按更新时间降序排列，一旦遇到早于 since 的就停止
                    break
            return filtered
        return all_prs

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

    def fetch_all(self, since: datetime) -> dict:
        """批量获取所有配置仓库的完整数据快照。"""
        results = {}
        for full_name in self.repos:
            owner, repo = full_name.split("/")
            logger.info("Fetching %s/%s ...", owner, repo)

            try:
                repo_info = self.get_repo_info(owner, repo)
                results[full_name] = {
                    "info": repo_info,
                    "commits": self.get_commits(owner, repo, since),
                    "issues": self.get_issues(owner, repo, since),
                    "pull_requests": self.get_pull_requests(owner, repo, since),
                    "releases": self.get_releases(owner, repo, since),
                }
            except Exception as e:
                logger.error("Failed to fetch %s: %s", full_name, e)
                results[full_name] = {"error": str(e)}

        return results

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
