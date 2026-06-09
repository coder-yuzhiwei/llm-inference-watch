"""报告生成模块 — 每日简报 / 每周深度 / 每月趋势总结"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import yaml


class MarkdownReporter:
    """生成三类 Markdown 报告。"""

    def __init__(self, config_path: str = "config/repos.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    # ═══════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _format_num(n: int) -> str:
        """数字格式化：1,234 或 12.3k。"""
        if n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    @staticmethod
    def _emoji_for_category(cat: str) -> str:
        emoji_map = {
            "bug": "🐛", "feature": "✨", "performance": "⚡",
            "model_support": "🧠", "refactor": "♻️", "ci_docs": "📚",
            "kernel": "🔥", "api": "🔌", "distributed": "🌐",
            "discussion": "💬", "community": "🤝", "other": "📦",
        }
        return emoji_map.get(cat, "📦")

    @staticmethod
    def _truncate(text: str, max_len: int = 100) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."

    # ═══════════════════════════════════════════════════════════
    # 每日简报
    # ═══════════════════════════════════════════════════════════

    def generate_daily(self, analysis_results: dict, cross_summary: dict,
                       report_date: Optional[datetime] = None) -> str:
        """生成每日简报 Markdown。"""
        if report_date is None:
            report_date = datetime.now(timezone.utc)

        date_str = report_date.strftime("%Y-%m-%d")
        lines = []
        lines.append(f"# 🔍 LLM 推理引擎每日简报")
        lines.append(f"")
        lines.append(f"> 📅 **{date_str}** | 自动生成 by [LLM-Inference-Watch](https://github.com)")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # 概览表
        lines.append(f"## 📊 今日概览")
        lines.append(f"")
        lines.append(f"| 仓库 | ⭐ Stars | 📝 Commits | 🐛 Issues | 🔀 PRs | ✅ Merged | 📦 Releases |")
        lines.append(f"|------|---------|------------|-----------|--------|-----------|------------|")
        for r in cross_summary["repos"]:
            if "error" in r:
                lines.append(f"| {r['name']} | ❌ 获取失败 | - | - | - | - | - |")
            else:
                lines.append(
                    f"| **{r['name']}** | {self._format_num(r['stars'])} | "
                    f"{r['commits']} | {r['issues']} | {r['prs']} | "
                    f"{r['prs_merged']} | {r['releases']} |"
                )
        lines.append(f"")

        # 合计
        t = cross_summary["totals"]
        lines.append(f"> 📈 四仓库合计：**{t['commits']}** commits · **{t['issues']}** issues · "
                     f"**{t['prs']}** PRs · **{t['releases']}** releases")
        lines.append(f"")

        # 各仓库亮点
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 🏷️ 各仓库亮点")
        lines.append(f"")

        for repo_name, result in analysis_results.items():
            if "error" in result:
                lines.append(f"### {repo_name} ❌")
                lines.append(f"> 数据获取失败：{result['error']}")
                lines.append(f"")
                continue

            lines.append(f"### {result['name']}")
            lines.append(f"")

            # Commit 分类
            commit_cats = result["commits"]["by_category"]
            if commit_cats:
                cats_str = " · ".join(
                    f"{self._emoji_for_category(k)} {k}: {v}"
                    for k, v in list(commit_cats.items())[:5]
                )
                lines.append(f"📝 **{result['commits']['total']} commits** — {cats_str}")
                lines.append(f"")

            # 关键 commit
            key_commits = result["commits"].get("key_commits", [])[:5]
            if key_commits:
                for kc in key_commits:
                    lines.append(f"- [`{kc['sha']}`]({kc['html_url']}) {self._truncate(kc['message'])} "
                                 f"— *{kc['author']}*")
                lines.append(f"")

            # 重要 PR
            notable_prs = result["pull_requests"].get("notable", [])[:3]
            if notable_prs:
                lines.append(f"🔀 **高互动 PR：**")
                for pr in notable_prs:
                    state_icon = "✅" if pr["state"] == "merged" else "🔄"
                    lines.append(f"- {state_icon} [#{pr['number']}]({pr['html_url']}) "
                                 f"{self._truncate(pr['title'])} — 💬{pr['comments']}")
                lines.append(f"")

            # 重要 issue
            notable_issues = result["issues"].get("notable", [])[:3]
            if notable_issues:
                lines.append(f"🐛 **热门 Issue：**")
                for iss in notable_issues:
                    state_icon = "✅" if iss["state"] == "closed" else "🔴"
                    lines.append(f"- {state_icon} [#{iss['number']}]({iss['html_url']}) "
                                 f"{self._truncate(iss['title'])} — 💬{iss['comments']}")
                lines.append(f"")

            # Release
            releases = result.get("releases", [])
            if releases:
                lines.append(f"📦 **新 Release：**")
                for rel in releases[:2]:
                    lines.append(f"- [{rel['tag_name']}]({rel['html_url']}) — {rel.get('name', '')}")
                lines.append(f"")

            lines.append(f"---")
            lines.append(f"")

        # 活跃贡献者
        lines.append(f"## 👥 活跃贡献者 TOP 5")
        lines.append(f"")
        all_authors = Counter()
        for result in analysis_results.values():
            if "error" in result:
                continue
            for author, count in result["commits"].get("top_authors", {}).items():
                all_authors[author] += count

        for author, count in all_authors.most_common(5):
            lines.append(f"- **{author}** — {count} commits")
        lines.append(f"")

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*📬 本报告由 [LLM-Inference-Watch](https://github.com) 自动生成，"
                     f"数据来源：GitHub API*")
        lines.append(f"")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # 每周深度报告
    # ═══════════════════════════════════════════════════════════

    def generate_weekly(self, analysis_results: dict, cross_summary: dict,
                        report_date: Optional[datetime] = None) -> str:
        """生成每周深度报告 Markdown。"""
        if report_date is None:
            report_date = datetime.now(timezone.utc)

        date_str = report_date.strftime("%Y-%m-%d")
        week_num = report_date.isocalendar()[1]
        lines = []
        lines.append(f"# 📰 LLM 推理引擎周报")
        lines.append(f"")
        lines.append(f"> 📅 **{date_str} · 第 {week_num} 周** | "
                     f"自动生成 by [LLM-Inference-Watch](https://github.com)")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # 目录
        lines.append(f"## 📑 目录")
        lines.append(f"")
        lines.append(f"1. [本周概览](#本周概览)")
        lines.append(f"2. [各仓库深度分析](#各仓库深度分析)")
        for r in cross_summary["repos"]:
            name = r.get("name", "unknown")
            anchor = name.lower().replace("/", "").replace(".", "")
            lines.append(f"   - [{name}](#{anchor})")
        lines.append(f"3. [跨仓库对比](#跨仓库对比)")
        lines.append(f"4. [社区热点追踪](#社区热点追踪)")
        lines.append(f"5. [趋势洞察](#趋势洞察)")
        lines.append(f"")

        # 1. 本周概览
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 📊 本周概览")
        lines.append(f"")
        lines.append(f"| 仓库 | ⭐ Stars | 📝 Commits | 🐛 Issues | 🔀 PRs | ✅ Merged | 📦 Releases |")
        lines.append(f"|------|---------|------------|-----------|--------|-----------|------------|")
        for r in cross_summary["repos"]:
            if "error" in r:
                lines.append(f"| {r['name']} | ❌ 获取失败 | - | - | - | - | - |")
            else:
                lines.append(
                    f"| **{r['name']}** | {self._format_num(r['stars'])} | "
                    f"{r['commits']} | {r['issues']} | {r['prs']} | "
                    f"{r['prs_merged']} | {r['releases']} |"
                )
        lines.append(f"")

        t = cross_summary["totals"]
        lines.append(f"> 📈 四仓库本周合计：**{t['commits']}** commits · **{t['issues']}** issues · "
                     f"**{t['prs']}** PRs · **{t['releases']}** releases")
        lines.append(f"")

        # 2. 各仓库深度分析
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 🔬 各仓库深度分析")
        lines.append(f"")

        for repo_name, result in analysis_results.items():
            if "error" in result:
                continue

            anchor = repo_name.lower().replace("/", "").replace(".", "")
            lines.append(f"### {result['name']} {{#{anchor}}}")
            lines.append(f"")

            # 基本信息
            info = result["info"]
            lines.append(f"⭐ {self._format_num(info['stars'])} stars · "
                         f"🍴 {self._format_num(info['forks'])} forks · "
                         f"🐛 {info['open_issues']} open issues")
            lines.append(f"")
            lines.append(f"> {info.get('description', '')}")
            lines.append(f"")

            # Commit 分析
            commit_total = result["commits"]["total"]
            commit_cats = result["commits"]["by_category"]
            lines.append(f"#### 📝 变更分析（{commit_total} commits）")
            lines.append(f"")
            if commit_cats:
                lines.append(f"| 类别 | 数量 | 占比 |")
                lines.append(f"|------|------|------|")
                for cat, count in commit_cats.items():
                    pct = f"{count/commit_total*100:.1f}%" if commit_total else "0%"
                    lines.append(f"| {self._emoji_for_category(cat)} {cat} | {count} | {pct} |")
                lines.append(f"")

            # 关键变更
            key_commits = result["commits"].get("key_commits", [])[:8]
            if key_commits:
                lines.append(f"#### 🔑 关键变更")
                lines.append(f"")
                for kc in key_commits:
                    lines.append(f"- [`{kc['sha']}`]({kc['html_url']}) {kc['message']} "
                                 f"— *{kc['author']}*")
                lines.append(f"")

            # PR 分析
            pr_data = result["pull_requests"]
            lines.append(f"#### 🔀 PR 动态（{pr_data['total']} total · "
                         f"{pr_data['merged']} merged · {pr_data['open']} open）")
            lines.append(f"")
            pr_cats = pr_data.get("by_category", {})
            if pr_cats:
                cats_str = " · ".join(
                    f"{self._emoji_for_category(k)} {k}: {v}"
                    for k, v in list(pr_cats.items())[:5]
                )
                lines.append(f"**分类分布：** {cats_str}")
                lines.append(f"")

            notable_prs = pr_data.get("notable", [])[:5]
            if notable_prs:
                lines.append(f"**高互动 PR：**")
                lines.append(f"")
                for pr in notable_prs:
                    state_icon = "✅" if pr["state"] == "merged" else ("🔄" if pr["state"] == "open" else "❌")
                    lines.append(f"- {state_icon} **[{pr['title']}]({pr['html_url']})** "
                                 f"by @{pr['user']} — 💬 {pr['comments']} comments")
                lines.append(f"")

            # Issue 分析
            issue_data = result["issues"]
            lines.append(f"#### 🐛 Issue 动态（{issue_data['total']} 个）")
            lines.append(f"")
            notable_issues = issue_data.get("notable", [])[:5]
            if notable_issues:
                for iss in notable_issues:
                    state_icon = "✅" if iss["state"] == "closed" else "🔴"
                    lines.append(f"- {state_icon} **[{iss['title']}]({iss['html_url']})** "
                                 f"by @{iss['user']} — 💬 {iss['comments']} comments")
                lines.append(f"")

            # 贡献者
            top_authors = result["commits"].get("top_authors", {})
            if top_authors:
                authors_str = ", ".join(
                    f"**{a}** ({c})" for a, c in list(top_authors.items())[:5]
                )
                lines.append(f"#### 👥 活跃贡献者")
                lines.append(f"")
                lines.append(f"{authors_str}")
                lines.append(f"")

            # Releases
            releases = result.get("releases", [])
            if releases:
                lines.append(f"#### 📦 Releases")
                lines.append(f"")
                for rel in releases:
                    lines.append(f"- **[{rel['tag_name']}]({rel['html_url']})** "
                                 f"— {rel.get('name', 'No title')}")
                    body = rel.get("body", "").strip()
                    if body:
                        lines.append(f"  > {self._truncate(body, 200)}")
                lines.append(f"")

            lines.append(f"---")
            lines.append(f"")

        # 3. 跨仓库对比
        lines.append(f"## 📈 跨仓库对比")
        lines.append(f"")

        # 活跃度排行
        sorted_by_commits = sorted(
            [r for r in cross_summary["repos"] if "error" not in r],
            key=lambda x: x["commits"], reverse=True
        )
        lines.append(f"### 🏃 本周活跃度排行")
        lines.append(f"")
        for i, r in enumerate(sorted_by_commits, 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣"][i-1] if i <= 4 else f"{i}."
            lines.append(f"{medal} **{r['name']}** — {r['commits']} commits · "
                         f"{r['prs']} PRs · {r['issues']} issues")
        lines.append(f"")

        # Stars 排行
        sorted_by_stars = sorted(
            [r for r in cross_summary["repos"] if "error" not in r],
            key=lambda x: x["stars"], reverse=True
        )
        lines.append(f"### ⭐ Stars 排行")
        lines.append(f"")
        for i, r in enumerate(sorted_by_stars, 1):
            lines.append(f"{i}. **{r['name']}** — {self._format_num(r['stars'])} stars")
        lines.append(f"")

        # 4. 社区热点追踪
        lines.append(f"## 🔥 社区热点追踪")
        lines.append(f"")

        # 汇总所有高互动内容
        all_hot = []
        for result in analysis_results.values():
            if "error" in result:
                continue
            for pr in result["pull_requests"].get("notable", [])[:3]:
                all_hot.append({
                    "type": "PR",
                    "repo": result["name"],
                    "title": pr["title"],
                    "url": pr["html_url"],
                    "comments": pr["comments"],
                    "state": pr["state"],
                })
            for iss in result["issues"].get("notable", [])[:3]:
                all_hot.append({
                    "type": "Issue",
                    "repo": result["name"],
                    "title": iss["title"],
                    "url": iss["html_url"],
                    "comments": iss["comments"],
                    "state": iss["state"],
                })

        all_hot.sort(key=lambda x: x["comments"], reverse=True)
        top_hot = all_hot[:10]

        if top_hot:
            lines.append(f"以下是本周讨论最热烈的内容：")
            lines.append(f"")
            for item in top_hot:
                icon = "🔀" if item["type"] == "PR" else "🐛"
                lines.append(f"- {icon} [{item['type']}] **[{item['title']}]({item['url']})**")
                lines.append(f"  — {item['repo']} · 💬 {item['comments']} comments")
            lines.append(f"")

        # 5. 趋势洞察
        lines.append(f"## 💡 趋势洞察")
        lines.append(f"")

        # 汇总各仓库的分类分布
        all_cats = Counter()
        for result in analysis_results.values():
            if "error" in result:
                continue
            for cat, count in result["commits"].get("by_category", {}).items():
                all_cats[cat] += count

        if all_cats:
            lines.append(f"### 本周变更类型分布")
            lines.append(f"")
            total_cat = sum(all_cats.values())
            for cat, count in all_cats.most_common():
                pct = f"{count/total_cat*100:.1f}%" if total_cat else "0%"
                bar = "█" * int(count / total_cat * 30) if total_cat else ""
                lines.append(f"| {self._emoji_for_category(cat)} {cat} | {count} | {pct} | {bar} |")
            lines.append(f"")

        # 本周亮点总结
        lines.append(f"### 🎯 本周亮点")
        lines.append(f"")

        total_commits = t["commits"]
        total_prs = t["prs"]
        most_active = sorted_by_commits[0]["name"] if sorted_by_commits else "N/A"

        lines.append(f"- 本周最活跃仓库：**{most_active}**，贡献了 {sorted_by_commits[0]['commits']} 个 commits")
        lines.append(f"- 生态合计产出 **{total_commits}** 个 commits、**{total_prs}** 个 PRs")
        lines.append(f"- 主要变更方向集中在：**{', '.join(cat for cat, _ in all_cats.most_common(3))}**")
        lines.append(f"")

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*📬 本报告由 [LLM-Inference-Watch](https://github.com) 自动生成，"
                     f"数据来源：GitHub API · {date_str}*")
        lines.append(f"")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # 每月趋势总结
    # ═══════════════════════════════════════════════════════════

    def generate_monthly(self, analysis_results: dict, cross_summary: dict,
                         report_date: Optional[datetime] = None) -> str:
        """生成每月趋势总结 Markdown。"""
        if report_date is None:
            report_date = datetime.now(timezone.utc)

        date_str = report_date.strftime("%Y-%m")
        month_name = report_date.strftime("%Y 年 %m 月")
        lines = []
        lines.append(f"# 📊 LLM 推理引擎月报")
        lines.append(f"")
        lines.append(f"> 📅 **{month_name}** | 自动生成 by [LLM-Inference-Watch](https://github.com)")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # 目录
        lines.append(f"## 📑 目录")
        lines.append(f"")
        lines.append(f"1. [月度概览](#月度概览)")
        lines.append(f"2. [各仓库月度分析](#各仓库月度分析)")
        lines.append(f"3. [重大变更回顾](#重大变更回顾)")
        lines.append(f"4. [生态趋势洞察](#生态趋势洞察)")
        lines.append(f"5. [下月展望](#下月展望)")
        lines.append(f"")

        # 1. 月度概览
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 📊 月度概览")
        lines.append(f"")
        lines.append(f"| 仓库 | ⭐ Stars | 📝 Commits | 🐛 Issues | 🔀 PRs | ✅ Merged | 📦 Releases |")
        lines.append(f"|------|---------|------------|-----------|--------|-----------|------------|")
        for r in cross_summary["repos"]:
            if "error" in r:
                lines.append(f"| {r['name']} | ❌ 获取失败 | - | - | - | - | - |")
            else:
                lines.append(
                    f"| **{r['name']}** | {self._format_num(r['stars'])} | "
                    f"{r['commits']} | {r['issues']} | {r['prs']} | "
                    f"{r['prs_merged']} | {r['releases']} |"
                )
        lines.append(f"")

        t = cross_summary["totals"]
        lines.append(f"> 📈 四仓库本月合计：**{t['commits']}** commits · **{t['issues']}** issues · "
                     f"**{t['prs']}** PRs · **{t['releases']}** releases")
        lines.append(f"")

        # 2. 各仓库月度分析
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 🔬 各仓库月度分析")
        lines.append(f"")

        for repo_name, result in analysis_results.items():
            if "error" in result:
                continue

            lines.append(f"### {result['name']}")
            lines.append(f"")

            info = result["info"]
            lines.append(f"⭐ {self._format_num(info['stars'])} stars · "
                         f"🍴 {self._format_num(info['forks'])} forks")
            lines.append(f"")

            # Commit 分类饼图（文本版）
            commit_total = result["commits"]["total"]
            commit_cats = result["commits"]["by_category"]
            if commit_cats:
                lines.append(f"**变更分布（{commit_total} commits）：**")
                lines.append(f"")
                for cat, count in commit_cats.most_common():
                    pct = f"{count/commit_total*100:.1f}%" if commit_total else "0%"
                    bar_len = int(count / commit_total * 20) if commit_total else 0
                    bar = "▓" * bar_len + "░" * (20 - bar_len)
                    lines.append(f"| {self._emoji_for_category(cat)} {cat} | {bar} | {count} ({pct}) |")
                lines.append(f"")

            # PR 统计
            pr_data = result["pull_requests"]
            lines.append(f"**PR 统计：** {pr_data['total']} total · "
                         f"{pr_data['merged']} merged · {pr_data['open']} open · "
                         f"{pr_data['closed']} closed")
            lines.append(f"")

            # 重大 PR
            notable_prs = pr_data.get("notable", [])[:3]
            if notable_prs:
                lines.append(f"**本月重大 PR：**")
                for pr in notable_prs:
                    lines.append(f"- [{pr['title']}]({pr['html_url']}) by @{pr['user']} "
                                 f"({self._emoji_for_category(pr['category'])} {pr['category']})")
                lines.append(f"")

            # Releases
            releases = result.get("releases", [])
            if releases:
                lines.append(f"**本月发布：**")
                for rel in releases:
                    lines.append(f"- [{rel['tag_name']}]({rel['html_url']}) — {rel.get('name', '')}")
                lines.append(f"")

            # Top 贡献者
            top_authors = result["commits"].get("top_authors", {})
            if top_authors:
                authors_list = list(top_authors.items())[:5]
                lines.append(f"**Top 贡献者：** " + " · ".join(
                    f"@{a} ({c})" for a, c in authors_list
                ))
                lines.append(f"")

            lines.append(f"---")
            lines.append(f"")

        # 3. 重大变更回顾
        lines.append(f"## 🏛️ 重大变更回顾")
        lines.append(f"")

        all_releases = []
        for result in analysis_results.values():
            if "error" in result:
                continue
            for rel in result.get("releases", []):
                all_releases.append({
                    "repo": result["name"],
                    "tag": rel["tag_name"],
                    "name": rel.get("name", ""),
                    "url": rel["html_url"],
                    "body": rel.get("body", ""),
                })

        if all_releases:
            lines.append(f"本月各仓库共发布 **{len(all_releases)}** 个版本：")
            lines.append(f"")
            for rel in all_releases:
                lines.append(f"### {rel['repo']} — {rel['tag']}")
                lines.append(f"")
                lines.append(f"**[{rel['name'] or rel['tag']}]({rel['url']})**")
                if rel["body"]:
                    lines.append(f"")
                    # 截取 changelog 关键部分
                    body = rel["body"][:500]
                    lines.append(f"> {body}")
                lines.append(f"")

        # 4. 生态趋势洞察
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 🔭 生态趋势洞察")
        lines.append(f"")

        # 汇总全月分类数据
        all_cats = Counter()
        all_repos_active = {}
        for result in analysis_results.values():
            if "error" in result:
                continue
            for cat, count in result["commits"].get("by_category", {}).items():
                all_cats[cat] += count
            all_repos_active[result["name"]] = result["commits"]["total"]

        lines.append(f"### 📐 整体变更方向分析")
        lines.append(f"")
        total_cat = sum(all_cats.values())
        if total_cat:
            lines.append(f"| 方向 | 占比 | 趋势解读 |")
            lines.append(f"|------|------|----------|")
            insights = {
                "performance": "性能优化仍是各引擎竞争的核心战场",
                "model_support": "新模型支持是生态扩展的关键驱动力",
                "kernel": "CUDA/Triton kernel 优化是底层竞争焦点",
                "bug": "bug 修复反映稳定性成熟度",
                "feature": "新功能推进引擎能力边界",
                "api": "API 兼容性是生态互通的基础",
                "distributed": "分布式推理是规模化部署的必然方向",
                "refactor": "重构反映代码质量投入",
                "ci_docs": "CI/文档完善反映社区治理水平",
            }
            for cat, count in all_cats.most_common():
                pct = f"{count/total_cat*100:.1f}%" if total_cat else "0%"
                insight = insights.get(cat, "—")
                lines.append(f"| {self._emoji_for_category(cat)} **{cat}** | {pct} | {insight} |")
            lines.append(f"")

        lines.append(f"### 🎯 本月关键洞察")
        lines.append(f"")

        # 找出最活跃仓库
        most_active = max(all_repos_active, key=all_repos_active.get) if all_repos_active else "N/A"
        most_active_count = all_repos_active.get(most_active, 0)

        lines.append(f"1. **最活跃仓库：{most_active}** — 本月 {most_active_count} commits，"
                     f"是推理引擎生态的开发主力")
        lines.append(f"")
        lines.append(f"2. **核心方向：{', '.join(cat for cat, _ in all_cats.most_common(3))}** "
                     f"— 这些是本月推理引擎生态的主要发力方向")
        lines.append(f"")

        if all_releases:
            lines.append(f"3. **版本发布节奏：** 本月共 {len(all_releases)} 个版本发布，"
                         f"反映了各项目的迭代速度")
            lines.append(f"")

        # 5. 下月展望
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 🔮 下月展望")
        lines.append(f"")
        lines.append(f"基于本月动态，下月值得关注的方面：")
        lines.append(f"")

        # 找各仓库 open 的高互动 PR
        open_prs = []
        for result in analysis_results.values():
            if "error" in result:
                continue
            for pr in result["pull_requests"].get("notable", []):
                if pr["state"] == "open":
                    open_prs.append({
                        "repo": result["name"],
                        "title": pr["title"],
                        "url": pr["html_url"],
                        "comments": pr["comments"],
                    })
        open_prs.sort(key=lambda x: x["comments"], reverse=True)

        if open_prs:
            lines.append(f"**待合并的重大 PR：**")
            for pr in open_prs[:5]:
                lines.append(f"- [{pr['repo']}] [{pr['title']}]({pr['url']}) — 💬 {pr['comments']}")
            lines.append(f"")

        lines.append(f"**关注方向：**")
        lines.append(f"- 🚀 性能优化（kernel 融合、内存优化）的持续突破")
        lines.append(f"- 🧠 新模型架构（MoE、多模态）的支持进展")
        lines.append(f"- 🔌 API 标准化与生态互通趋势")
        lines.append(f"- 🌐 分布式推理方案的成熟度提升")
        lines.append(f"")

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*📬 本报告由 [LLM-Inference-Watch](https://github.com) 自动生成，"
                     f"数据来源：GitHub API · {date_str}*")
        lines.append(f"")

        return "\n".join(lines)


# 模块级 Counter 引用
from collections import Counter
