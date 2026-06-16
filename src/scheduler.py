"""调度器：根据报告类型拉取数据、分析、生成报告并写入文件。"""

import os
import sys
import logging
import json
from datetime import datetime, timezone, timedelta

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


def save_report(content: str, date: datetime):
    """保存每日报告到 reports/daily/ 目录。"""
    filename = f"{date.strftime('%Y-%m-%d')}.md"
    dir_path = os.path.join(PROJECT_ROOT, "reports", "daily")
    ensure_dir(dir_path)
    filepath = os.path.join(dir_path, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Report saved: %s", filepath)
    return filepath


def save_daily_data(data: dict, date: datetime):
    """保存每日分析数据到 data/daily/ 目录（用于 AI 分析）。"""
    timestamp = date.strftime("%Y-%m-%d")
    dir_path = os.path.join(PROJECT_ROOT, "data", "daily")
    ensure_dir(dir_path)
    filepath = os.path.join(dir_path, f"{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("Daily data saved: %s", filepath)
    return filepath


def run_daily():
    """执行每日报告生成和数据采集。"""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    logger.info("=" * 50)
    logger.info("Generating DAILY report (since %s)...", since.isoformat())

    # 1. 抓取数据
    logger.info("Step 1: Fetching data from GitHub API...")
    fetcher = GitHubFetcher()
    raw_data = fetcher.fetch_all(since, mode="light")

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
    content = reporter.generate_daily(analysis_results, cross_summary, now)

    # 4. 保存报告
    filepath = save_report(content, now)

    # 5. 保存每日数据（用于 AI 分析）
    save_daily_data({
        "analysis_results": analysis_results,
        "cross_summary": cross_summary,
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
    }, now)

    # 6. 输出摘要
    t = cross_summary["totals"]
    logger.info("=" * 50)
    logger.info("Daily report generated successfully!")
    logger.info("  File: %s", filepath)
    logger.info("  Summary: %d commits, %d issues, %d PRs, %d releases",
                t["commits"], t["issues"], t["prs"], t["releases"])

    return filepath


def run(report_type: str = "daily"):
    """执行指定类型的报告生成。"""
    if report_type == "daily":
        return run_daily()
    else:
        logger.error("Only 'daily' report type is supported currently")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM-Inference-Watch Report Generator")
    parser.add_argument("type", nargs="?", default="daily", choices=["daily"],
                        help="Report type to generate (only 'daily' is supported)")
    args = parser.parse_args()
    run(args.type)
