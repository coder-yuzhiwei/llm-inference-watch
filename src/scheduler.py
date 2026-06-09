"""调度器：根据报告类型拉取数据、分析、生成报告并写入文件。"""

import os
import sys
import logging
import json
from datetime import datetime, timezone, timedelta

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fetcher import GitHubFetcher
from src.analyzer import Analyzer
from src.reporter import MarkdownReporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_report(content: str, report_type: str, date: datetime):
    """保存报告到对应目录。"""
    if report_type == "daily":
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        dir_path = os.path.join(PROJECT_ROOT, "reports", "daily")
    elif report_type == "weekly":
        filename = f"{date.strftime('%Y')}-W{date.isocalendar()[1]:02d}.md"
        dir_path = os.path.join(PROJECT_ROOT, "reports", "weekly")
    elif report_type == "monthly":
        filename = f"{date.strftime('%Y-%m')}.md"
        dir_path = os.path.join(PROJECT_ROOT, "reports", "monthly")
    else:
        raise ValueError(f"Unknown report type: {report_type}")

    ensure_dir(dir_path)
    filepath = os.path.join(dir_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Report saved: %s", filepath)
    return filepath


def run(report_type: str):
    """执行指定类型的报告生成。"""
    now = datetime.now(timezone.utc)

    if report_type == "daily":
        since = now - timedelta(hours=24)
        logger.info("Generating DAILY report (since %s)...", since.isoformat())
    elif report_type == "weekly":
        since = now - timedelta(days=7)
        logger.info("Generating WEEKLY report (since %s)...", since.isoformat())
    elif report_type == "monthly":
        since = now - timedelta(days=30)
        logger.info("Generating MONTHLY report (since %s)...", since.isoformat())
    else:
        logger.error("Unknown report type: %s", report_type)
        sys.exit(1)

    # 1. 抓取数据
    logger.info("=" * 50)
    logger.info("Step 1: Fetching data from GitHub API...")
    fetcher = GitHubFetcher()
    raw_data = fetcher.fetch_all(since)

    # 2. 分析
    logger.info("Step 2: Analyzing data...")
    analyzer = Analyzer()
    analysis_results = {}
    for repo_name, repo_data in raw_data.items():
        analysis_results[repo_name] = analyzer.analyze_repo(repo_data, repo_name)

    cross_summary = analyzer.cross_repo_summary(analysis_results)

    # 3. 生成报告
    logger.info("Step 3: Generating report...")
    reporter = MarkdownReporter()
    if report_type == "daily":
        content = reporter.generate_daily(analysis_results, cross_summary, now)
    elif report_type == "weekly":
        content = reporter.generate_weekly(analysis_results, cross_summary, now)
    elif report_type == "monthly":
        content = reporter.generate_monthly(analysis_results, cross_summary, now)

    # 4. 保存
    filepath = save_report(content, report_type, now)

    # 5. 输出摘要
    t = cross_summary["totals"]
    logger.info("=" * 50)
    logger.info("Report generated successfully!")
    logger.info("  Type: %s", report_type)
    logger.info("  File: %s", filepath)
    logger.info("  Summary: %d commits, %d issues, %d PRs, %d releases",
                t["commits"], t["issues"], t["prs"], t["releases"])

    return filepath


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM-Inference-Watch Report Generator")
    parser.add_argument("type", choices=["daily", "weekly", "monthly"],
                        help="Report type to generate")
    args = parser.parse_args()
    run(args.type)
