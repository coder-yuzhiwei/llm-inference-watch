"""主测试文件：测试数据采集、报告生成和 AI 分析功能"""

import os
import sys
import json
import pytest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analyzer import Analyzer, ChangeClassifier
from src.reporter import MarkdownReporter
from src.ai_analyzer import AIAnalyzer, DataAnalyzer
from src.ai_scheduler import get_recent_data_files, merge_analysis_results

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDataCollection:
    """测试数据采集功能（使用 mock 数据，不实际调用 GitHub API）"""

    def test_analyzer_classifies_commits(self):
        """测试 ChangeClassifier 分类功能"""
        assert ChangeClassifier.classify_commit("fix: resolve memory leak") == "bug"
        assert ChangeClassifier.classify_commit("feat: new feature") == "feature"
        assert ChangeClassifier.classify_commit("perf: optimize CUDA kernel") == "performance"
        assert ChangeClassifier.classify_commit("docs: update README") == "ci_docs"
        assert ChangeClassifier.classify_commit("ci: update workflow") == "ci_docs"
        assert ChangeClassifier.classify_commit("llama-3 model") == "model_support"
        assert ChangeClassifier.classify_commit("quantization update") == "model_support"
        assert ChangeClassifier.classify_commit("kernel: triton attention") == "kernel"
        assert ChangeClassifier.classify_commit("distributed: tensor parallel") == "distributed"
        assert ChangeClassifier.classify_commit("refactor: cleanup code") == "refactor"

    def test_analyzer_output_structure(self):
        """测试分析结果结构正确"""
        analyzer = Analyzer()

        mock_repo_data = {
            "commits": [
                {"sha": "abc123", "commit": {"message": "feat: add new feature", "author": {"name": "test"}}},
                {"sha": "def456", "commit": {"message": "fix: bug fix", "author": {"name": "test"}}},
                {"sha": "ghi789", "commit": {"message": "perf: optimize CUDA kernel", "author": {"name": "test"}}},
            ],
            "issues": [
                {"number": 1, "title": "Feature request: xxx", "comments": 5, "state": "open", "labels": [{"name": "feature request"}]},
                {"number": 2, "title": "Bug: something wrong", "comments": 3, "state": "open", "labels": [{"name": "bug"}]},
                {"number": 3, "title": "Performance issue", "comments": 10, "state": "open", "labels": [{"name": "performance"}]},
            ],
            "pull_requests": [
                {"number": 10, "title": "Add new feature", "comments": 10, "state": "merged", "merged_at": "2026-06-20T00:00:00Z", "labels": [{"name": "feature"}]},
                {"number": 11, "title": "Fix memory leak", "comments": 2, "state": "merged", "merged_at": "2026-06-20T00:00:00Z", "labels": [{"name": "bug"}]},
            ],
            "releases": [],
            "info": {"stargazers_count": 10000, "forks_count": 2000, "open_issues_count": 500, "description": "test"},
        }

        result = analyzer.analyze_repo(mock_repo_data, "test/repo")

        assert "name" in result
        assert "commits" in result
        assert "issues" in result
        assert "pull_requests" in result
        assert "releases" in result

        commits = result["commits"]
        assert "total" in commits
        assert "by_category" in commits
        assert "key_commits" in commits
        assert commits["total"] == 3

        prs = result["pull_requests"]
        assert "total" in prs
        assert "merged" in prs
        assert "notable" in prs
        assert prs["merged"] == 2

    def test_analyzer_filter_notable(self):
        """测试 analyzer 正确过滤 notable items"""
        analyzer = Analyzer()

        mock_repo_data = {
            "commits": [],
            "issues": [
                {"number": 1, "title": "Low interaction", "comments": 2, "state": "open", "labels": [{"name": "bug"}]},
                {"number": 2, "title": "High interaction feature", "comments": 5, "state": "open", "labels": [{"name": "feature request"}]},
                {"number": 3, "title": "Bug with comments", "comments": 10, "state": "open", "labels": [{"name": "bug"}]},
            ],
            "pull_requests": [
                {"number": 10, "title": "Minor fix", "comments": 2, "state": "merged", "merged_at": "2026-06-20T00:00:00Z", "labels": [{"name": "bug"}]},
                {"number": 11, "title": "Major feature", "comments": 8, "state": "merged", "merged_at": "2026-06-20T00:00:00Z", "labels": [{"name": "feature"}]},
            ],
            "releases": [],
            "info": {"stargazers_count": 10000, "forks_count": 2000, "open_issues_count": 500, "description": "test"},
        }

        result = analyzer.analyze_repo(mock_repo_data, "test/repo")

        issues = result["issues"]["notable"]
        prs = result["pull_requests"]["notable"]

        assert len(issues) == 1, f"Expected 1 notable issue (feature with comments >= 3), got {len(issues)}"
        assert issues[0]["number"] == 2, "Bug issues should be filtered out"

        assert len(prs) == 1, f"Expected 1 notable PR (feature with comments >= 3), got {len(prs)}"
        assert prs[0]["number"] == 11, "Bug PRs should be filtered out"


class TestReportGeneration:
    """测试报告生成功能（只测试每日报告）"""

    def test_reporter_generates_daily(self):
        """测试每日报告生成"""
        reporter = MarkdownReporter()

        mock_analysis = {
            "vllm-project/vllm": {
                "name": "vllm-project/vllm",
                "info": {"stars": 50000, "forks": 8000, "open_issues": 1000, "description": "vLLM is a fast and easy-to-use LLM inference and serving library"},
                "commits": {"total": 15, "by_category": {"feature": 5, "performance": 4, "bug": 3, "kernel": 3}, "key_commits": [
                    {"sha": "abc123", "message": "feat: add new model support", "html_url": "https://github.com/test", "author": "dev"},
                    {"sha": "def456", "message": "perf: optimize attention kernel", "html_url": "https://github.com/test", "author": "dev"},
                ]},
                "issues": {"total": 8, "notable": [
                    {"number": 12345, "title": "Feature request: distributed inference", "html_url": "https://github.com/test", "user": "user", "comments": 20, "state": "open"},
                ]},
                "pull_requests": {"total": 10, "merged": 7, "open": 3, "notable": [
                    {"number": 67890, "title": "Add flash attention v3", "html_url": "https://github.com/test", "user": "dev", "comments": 15, "state": "merged"},
                ]},
                "releases": [{"tag_name": "v0.5.0", "name": "v0.5.0", "html_url": "https://github.com/test"}],
            }
        }

        mock_summary = {
            "repos": [{"name": "vllm-project/vllm", "stars": 50000, "commits": 15, "issues": 8, "prs": 10, "prs_merged": 7, "releases": 1}],
            "totals": {"stars": 50000, "commits": 15, "issues": 8, "prs": 10, "releases": 1},
        }

        report = reporter.generate_daily(mock_analysis, mock_summary)

        assert isinstance(report, str)
        assert len(report) > 0
        assert "每日简报" in report
        assert "vllm-project/vllm" in report
        assert "15 commits" in report
        assert "distributed inference" in report
        assert "flash attention" in report

    def test_reporter_daily_structure(self):
        """测试每日报告结构完整性"""
        reporter = MarkdownReporter()

        mock_analysis = {
            "test/repo": {
                "name": "test/repo",
                "info": {"stars": 10000, "forks": 2000, "open_issues": 500, "description": "test"},
                "commits": {"total": 5, "by_category": {}, "key_commits": []},
                "issues": {"total": 3, "notable": []},
                "pull_requests": {"total": 2, "merged": 1, "open": 1, "notable": []},
                "releases": [],
            }
        }

        mock_summary = {
            "repos": [{"name": "test/repo", "stars": 10000, "commits": 5, "issues": 3, "prs": 2, "prs_merged": 1, "releases": 0}],
            "totals": {"stars": 10000, "commits": 5, "issues": 3, "prs": 2, "releases": 0},
        }

        report = reporter.generate_daily(mock_analysis, mock_summary)

        sections = ["今日概览", "各仓库亮点", "活跃贡献者"]
        for section in sections:
            assert section in report, f"Missing section: {section}"


class TestAIAnalysis:
    """测试 AI 分析功能（无 API key 时使用 mock 模式）"""

    def test_ai_analyzer_initialization(self):
        """测试 AIAnalyzer 初始化"""
        analyzer = AIAnalyzer()
        assert analyzer is not None
        assert analyzer.model is not None
        assert analyzer.max_tokens > 0
        assert 0 <= analyzer.temperature <= 1

    def test_data_analyzer_extracts_notable(self):
        """测试 DataAnalyzer 提取值得关注的变更"""
        analyzer = DataAnalyzer()

        mock_data = {
            "vllm-project/vllm": {
                "commits": {"key_commits": [
                    {"sha": "abc", "message": "feat: add flash attention v3", "html_url": "url", "author": "test"},
                    {"sha": "def", "message": "perf: optimize memory usage", "html_url": "url", "author": "test"},
                ]},
                "issues": {"notable": [
                    {"number": 1, "title": "Feature request: distributed inference", "html_url": "url", "user": "test", "comments": 20, "state": "open"},
                    {"number": 2, "title": "Performance issue on A100", "html_url": "url", "user": "test", "comments": 15, "state": "open"},
                ]},
                "pull_requests": {"notable": [
                    {"number": 10, "title": "Add new model support", "html_url": "url", "user": "test", "comments": 10, "state": "merged"},
                ]},
                "releases": [{"tag_name": "v0.5.0", "name": "v0.5.0", "html_url": "url", "body": "new features"}],
            }
        }

        result = analyzer.extract_notable_changes(mock_data)

        assert "repos" in result
        assert "vllm-project/vllm" in result["repos"]
        assert len(result["repos"]["vllm-project/vllm"]["key_commits"]) == 2
        assert len(result["repos"]["vllm-project/vllm"]["notable_issues"]) == 2
        assert len(result["repos"]["vllm-project/vllm"]["notable_prs"]) == 1

    def test_get_recent_data_files(self):
        """测试获取最近数据文件"""
        files = get_recent_data_files(days=30)
        assert isinstance(files, list)

    def test_merge_analysis_results(self):
        """测试合并分析结果（基于已有数据文件）"""
        mock_files = []
        data_dir = os.path.join(PROJECT_ROOT, "data", "daily")
        if os.path.exists(data_dir):
            for f in sorted(os.listdir(data_dir))[-2:] if os.listdir(data_dir) else []:
                mock_files.append(os.path.join(data_dir, f))

        if mock_files:
            merged = merge_analysis_results(mock_files)
            assert "analysis_results" in merged
            assert "date_range" in merged
            assert "cross_summary" in merged

            date_range = merged["date_range"]
            assert date_range["start"] is not None
            assert date_range["end"] is not None
            assert date_range["days"] >= 1

            for repo_data in merged["analysis_results"].values():
                assert "commits" in repo_data
                assert "issues" in repo_data
                assert "pull_requests" in repo_data

    def test_ai_filter_items_no_api_key(self):
        """测试无 API key 时 AI 筛选返回空"""
        analyzer = AIAnalyzer()

        test_data = {
            "repos": {
                "vllm-project/vllm": {
                    "issues": [{"number": 1, "title": "Test issue about performance", "comments": 5}],
                    "prs": [{"number": 10, "title": "Test PR adding new feature", "state": "merged", "comments": 3}],
                    "commits": [],
                    "releases": [],
                    "category_distribution": {},
                }
            },
            "date_range": "2026-06-15 ~ 2026-06-21",
            "days": 7,
        }

        result = analyzer.filter_items(test_data)
        assert isinstance(result, dict)

    def test_ai_generate_report_no_api_key(self):
        """测试无 API key 时生成模拟报告"""
        analyzer = AIAnalyzer()

        merged_data = {
            "analysis_results": {
                "vllm-project/vllm": {
                    "commits": {"total": 10, "by_category": {"feature": 5, "performance": 3, "kernel": 2}},
                    "issues": {"total": 5},
                    "pull_requests": {"total": 8, "merged": 6, "open": 2},
                    "releases": [],
                }
            },
            "date_range": {"start": "2026-06-15", "end": "2026-06-21", "days": 7},
        }

        detailed_data = {}

        result = analyzer.generate_report(merged_data, detailed_data)
        assert result["success"] is True
        assert "content" in result
        assert len(result["content"]) > 0

    def test_ai_generate_report_with_detailed_data(self):
        """测试带详细数据时生成报告"""
        analyzer = AIAnalyzer()

        merged_data = {
            "analysis_results": {
                "vllm-project/vllm": {
                    "commits": {"total": 10, "by_category": {"feature": 5}},
                    "issues": {"total": 5},
                    "pull_requests": {"total": 8, "merged": 6, "open": 2},
                    "releases": [],
                }
            },
            "date_range": {"start": "2026-06-15", "end": "2026-06-21", "days": 7},
        }

        detailed_data = {
            "vllm-project/vllm": {
                "issues": [
                    {"number": 12345, "title": "Feature request: distributed inference", "body": "This is a detailed body...", "comments_count": 20, "reason": "High interaction about distributed inference"},
                ],
                "prs": [
                    {"number": 67890, "title": "Add flash attention v3", "body": "This PR adds flash attention v3 support...", "comments_count": 15, "merged": True, "additions": 500, "deletions": 100, "reason": "Major feature addition"},
                ],
            }
        }

        result = analyzer.generate_report(merged_data, detailed_data)
        assert result["success"] is True
        assert "content" in result


class TestConfiguration:
    """测试配置文件加载"""

    def test_config_loading(self):
        """测试配置文件能正常加载"""
        import yaml

        config_path = os.path.join(PROJECT_ROOT, "config", "repos.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "repos" in config
        assert "github" in config
        assert "ai" in config
        assert "fetch" in config
        assert "display" in config

        assert len(config["repos"]) >= 1
        assert config["ai"]["default_model"] is not None
        assert config["ai"]["max_tokens"] > 0

    def test_ai_analyzer_uses_config(self):
        """测试 AIAnalyzer 正确使用配置文件中的参数"""
        analyzer = AIAnalyzer()

        import yaml
        config_path = os.path.join(PROJECT_ROOT, "config", "repos.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        ai_config = config.get("ai", {})
        expected_model = ai_config.get("default_model", "deepseek-v4-flash")
        expected_tokens = ai_config.get("max_tokens", 4096)
        expected_temp = ai_config.get("temperature", 0.3)

        assert analyzer.model == expected_model
        assert analyzer.max_tokens == expected_tokens
        assert analyzer.temperature == expected_temp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])