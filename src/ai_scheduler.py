"""AI 分析调度器：两步分析流程"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fetcher import GitHubFetcher
from src.ai_analyzer import AIAnalyzer, DataAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "repos.yaml")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

AI_CONFIG = CONFIG.get("ai", {})
FILTER_CONFIG = AI_CONFIG.get("filter", {})
DETAIL_CONFIG = AI_CONFIG.get("detail", {})


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_ai_report(content: str, date_str: str):
    """保存 AI 分析报告到 reports/ai/ 目录。"""
    dir_path = os.path.join(PROJECT_ROOT, "reports", "ai")
    ensure_dir(dir_path)

    filename = f"{date_str}.md"
    filepath = os.path.join(dir_path, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("AI analysis report saved: %s", filepath)
    return filepath


def get_recent_data_files(days: int = 7) -> List[str]:
    """获取最近 N 天的数据文件路径列表。"""
    data_dir = os.path.join(PROJECT_ROOT, "data", "daily")
    if not os.path.exists(data_dir):
        return []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)
    recent_files = []

    for filename in files:
        date_str = filename.replace(".json", "")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date >= cutoff:
                recent_files.append(os.path.join(data_dir, filename))
        except ValueError:
            continue

    return recent_files


def merge_analysis_results(data_files: List[str]) -> Dict:
    """合并多个日期的分析结果。"""
    merged = {
        "analysis_results": {},
        "cross_summary": {
            "repos": [],
            "totals": {"commits": 0, "issues": 0, "prs": 0, "releases": 0}
        },
        "date_range": {
            "start": None,
            "end": None,
            "days": 0
        }
    }

    for filepath in data_files[::-1]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        date_str = data.get("date", "")

        if not merged["date_range"]["start"]:
            merged["date_range"]["start"] = date_str
        merged["date_range"]["end"] = date_str

        analysis_results = data.get("analysis_results", {})
        for repo_name, repo_data in analysis_results.items():
            if repo_name not in merged["analysis_results"]:
                merged["analysis_results"][repo_name] = {
                    "name": repo_name,
                    "commits": {"total": 0, "by_category": {}, "top_authors": {}, "key_commits": []},
                    "issues": {"total": 0, "by_category": {}, "notable": []},
                    "pull_requests": {"total": 0, "merged": 0, "open": 0, "closed": 0, "by_category": {}, "notable": []},
                    "releases": [],
                }

            repo_merged = merged["analysis_results"][repo_name]

            commits_data = repo_data.get("commits", {})
            repo_merged["commits"]["total"] += commits_data.get("total", 0)

            for cat, count in commits_data.get("by_category", {}).items():
                repo_merged["commits"]["by_category"][cat] = \
                    repo_merged["commits"]["by_category"].get(cat, 0) + count

            repo_merged["issues"]["total"] = repo_data.get("issues", {}).get("total", 0)
            repo_merged["pull_requests"]["total"] = repo_data.get("pull_requests", {}).get("total", 0)
            repo_merged["pull_requests"]["merged"] += repo_data.get("pull_requests", {}).get("merged", 0)

            seen_commits = {c["sha"] for c in repo_merged["commits"]["key_commits"]}
            for commit in commits_data.get("key_commits", []):
                if commit["sha"] not in seen_commits:
                    commit_with_date = {**commit, "date": date_str}
                    repo_merged["commits"]["key_commits"].append(commit_with_date)
                    seen_commits.add(commit["sha"])

            seen_prs = {pr["number"] for pr in repo_merged["pull_requests"]["notable"]}
            for pr in repo_data.get("pull_requests", {}).get("notable", []):
                if pr["number"] not in seen_prs:
                    pr_with_date = {**pr, "date": date_str}
                    repo_merged["pull_requests"]["notable"].append(pr_with_date)
                    seen_prs.add(pr["number"])

            seen_issues = {issue["number"] for issue in repo_merged["issues"]["notable"]}
            for issue in repo_data.get("issues", {}).get("notable", []):
                if issue["number"] not in seen_issues:
                    issue_with_date = {**issue, "date": date_str}
                    repo_merged["issues"]["notable"].append(issue_with_date)
                    seen_issues.add(issue["number"])

            for release in repo_data.get("releases", []):
                if release not in repo_merged["releases"]:
                    repo_merged["releases"].append(release)

    merged["date_range"]["days"] = len(data_files)

    t = merged["cross_summary"]["totals"]
    for repo_data in merged["analysis_results"].values():
        t["commits"] += repo_data["commits"]["total"]
        t["issues"] += repo_data["issues"]["total"]
        t["prs"] += repo_data["pull_requests"]["total"]
        t["releases"] += len(repo_data["releases"])

    return merged


def mark_selected_items_in_daily_files(data_files: List[str], selection: Dict):
    """将 AI 选中的 issue/PR 标记写回到每日 JSON 文件中。"""
    for filepath in data_files:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        analysis_results = data.get("analysis_results", {})
        
        modified = False
        for repo_name, repo_data in analysis_results.items():
            if repo_name not in selection:
                continue

            selected_items = selection[repo_name]
            
            for issue in repo_data.get("issues", {}).get("notable", []):
                for selected in selected_items.get("issues", []):
                    if issue["number"] == selected["number"]:
                        issue["ai_selected"] = True
                        issue["ai_reason"] = selected["reason"]
                        modified = True

            for pr in repo_data.get("pull_requests", {}).get("notable", []):
                for selected in selected_items.get("prs", []):
                    if pr["number"] == selected["number"]:
                        pr["ai_selected"] = True
                        pr["ai_reason"] = selected["reason"]
                        modified = True

        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Marked selected items in: %s", os.path.basename(filepath))


def fetch_selected_details(selection: Dict, fetcher: GitHubFetcher) -> Dict:
    """获取选中的 issue/PR 的详细信息。"""
    detailed_data = {}
    body_max_length = DETAIL_CONFIG.get("body_max_length", 1000)

    for repo_name, items in selection.items():
        owner, repo = repo_name.split("/")
        detailed_data[repo_name] = {"issues": [], "prs": []}

        for item in items.get("issues", []):
            number = item.get("number")
            reason = item.get("reason", "")
            detail = fetcher.get_issue_detail(owner, repo, number)
            if detail:
                detailed_data[repo_name]["issues"].append({
                    "number": number,
                    "title": detail.get("title"),
                    "body": detail.get("body", "")[:body_max_length],
                    "comments_count": detail.get("comments", 0),
                    "reason": reason,
                })

        for item in items.get("prs", []):
            number = item.get("number")
            reason = item.get("reason", "")
            detail = fetcher.get_pr_detail(owner, repo, number)
            if detail:
                detailed_data[repo_name]["prs"].append({
                    "number": number,
                    "title": detail.get("title"),
                    "body": detail.get("body", "")[:body_max_length],
                    "comments_count": detail.get("comments", 0),
                    "merged": bool(detail.get("merged_at")),
                    "additions": detail.get("additions", 0),
                    "deletions": detail.get("deletions", 0),
                    "reason": reason,
                })

    return detailed_data


def analyze(days: int = None):
    """执行两步 AI 分析流程。"""
    if days is None:
        days = AI_CONFIG.get("default_analysis_days", 7)
    logger.info("=" * 50)
    logger.info("Two-step AI analysis (last %d days)", days)

    # Step 1: 收集数据
    logger.info("Step 1: Collecting data...")
    data_files = get_recent_data_files(days)

    if not data_files:
        logger.error("No data files found in the last %d days", days)
        logger.error("Please run 'python src/scheduler.py daily' first")
        sys.exit(1)

    logger.info("Found %d data files:", len(data_files))
    for f in data_files:
        logger.info("  - %s", os.path.basename(f))

    logger.info("Merging analysis results...")
    merged_data = merge_analysis_results(data_files)

    date_range = merged_data["date_range"]
    logger.info("Date range: %s to %s (%d days)",
                date_range["start"], date_range["end"], date_range["days"])

    # Step 2: AI 筛选
    logger.info("=" * 50)
    logger.info("Step 2: AI filtering (select items to investigate)...")

    analyzer = AIAnalyzer()

    input_limit = FILTER_CONFIG.get("input_limit", {})

    # 构建筛选用的数据（只有标题）
    filter_data = {
        "repos": {},
        "date_range": f"{date_range['start']} ~ {date_range['end']}",
        "days": date_range["days"]
    }

    for repo_name, repo_data in merged_data["analysis_results"].items():
        filter_data["repos"][repo_name] = {
            "issues": repo_data["issues"].get("notable", [])[:input_limit.get("issues", 10)],
            "prs": repo_data["pull_requests"].get("notable", [])[:input_limit.get("prs", 10)],
            "commits": repo_data["commits"].get("key_commits", [])[:input_limit.get("commits", 10)],
            "releases": repo_data["releases"][:input_limit.get("releases", 3)],
            "category_distribution": repo_data["commits"].get("by_category", {}),
        }

    # 调用 AI 筛选
    selection = analyzer.filter_items(filter_data)

    if not selection:
        logger.error("AI filtering failed or returned no results")
        sys.exit(1)

    # 按分析天数动态限制每个仓库的选中数量
    multiplier = FILTER_CONFIG.get("max_items_per_repo_multiplier", 2)
    max_per_repo = days * multiplier

    for repo_name, items in selection.items():
        if len(items.get("issues", [])) > max_per_repo:
            selection[repo_name]["issues"] = items["issues"][:max_per_repo]
        if len(items.get("prs", [])) > max_per_repo:
            selection[repo_name]["prs"] = items["prs"][:max_per_repo]

    logger.info("AI selected items (after limit):")
    total_issues = 0
    total_prs = 0
    for repo, items in selection.items():
        issue_count = len(items.get("issues", []))
        pr_count = len(items.get("prs", []))
        total_issues += issue_count
        total_prs += pr_count
        logger.info("  %s: %d issues, %d PRs (max per repo: %d)",
                    repo,
                    issue_count,
                    pr_count,
                    max_per_repo)

    logger.info("=" * 50)
    logger.info("Total unique items selected by AI:")
    logger.info("  Issues: %d", total_issues)
    logger.info("  PRs: %d", total_prs)
    logger.info("  Total: %d", total_issues + total_prs)

    # Step 2.5: 将选中结果标记到每日 JSON 文件
    logger.info("=" * 50)
    logger.info("Step 2.5: Marking selected items in daily data files...")
    mark_selected_items_in_daily_files(data_files, selection)

    # Step 3: 获取详情
    logger.info("=" * 50)
    logger.info("Step 3: Fetching details for selected items...")

    fetcher = GitHubFetcher()
    detailed_data = fetch_selected_details(selection, fetcher)

    logger.info("Fetched details for %d repos", len(detailed_data))

    # Step 4: AI 生成报告
    logger.info("=" * 50)
    logger.info("Step 4: AI generating final report...")

    result = analyzer.generate_report(merged_data, detailed_data)

    if result.get("success"):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filepath = save_ai_report(result["content"], date_str)

        logger.info("=" * 50)
        logger.info("AI analysis completed successfully!")
        logger.info("  Date range: %s ~ %s (%d days)",
                    date_range["start"], date_range["end"], date_range["days"])
        logger.info("  Report: %s", filepath)

        return filepath
    else:
        logger.error("AI analysis failed")
        sys.exit(1)


def list_data():
    """列出可用的数据文件。"""
    data_dir = os.path.join(PROJECT_ROOT, "data", "daily")
    if not os.path.exists(data_dir):
        print("No data directory found.")
        return

    files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)

    print(f"Available daily data files ({len(files)} total):")
    print("-" * 40)
    for f in files[:14]:
        print(f"  {f}")
    if len(files) > 14:
        print(f"  ... and {len(files) - 14} more")


if __name__ == "__main__":
    import argparse

    default_days = AI_CONFIG.get("default_analysis_days", 7)

    parser = argparse.ArgumentParser(description="LLM-Inference-Watch AI Analyzer")
    parser.add_argument("action", choices=["analyze", "list"],
                        help="Action: 'analyze' for AI analysis, 'list' to show available data")
    parser.add_argument("--days", "-d", type=int, default=default_days,
                        help=f"Number of days to analyze (default: {default_days})")

    args = parser.parse_args()

    if args.action == "list":
        list_data()
    elif args.action == "analyze":
        analyze(args.days)
