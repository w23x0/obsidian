#!/usr/bin/env python3
"""扫描 vault 结构 + 读 git log，重新生成 README 的 AUTOGEN 区域。"""
import re
import sys
import subprocess
import html
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent.parent
README = ROOT / "README.md"
ASSETS = ROOT / ".github" / "assets"
HISTORY_SUMMARIES = ROOT / ".github" / "data" / "history_summaries.json"
DISPLAY_TIMEZONE = ZoneInfo("Asia/Shanghai")
EXCLUDE_DIRS = {".obsidian", ".git", "assets", "scripts", ".github", "node_modules"}

NOTE_EXTENSIONS = {".md", ".canvas", ".base"}
NON_NOTE_PATHS = {"readme.md", "conflict-files-obsidian-git.md"}
WORD_SWATCH_GRADIENTS = [
    ("#fff7bc", "#fee391"),
    ("#e7f5a9", "#b8de29"),
    ("#b8de29", "#6cce59"),
    ("#6cce59", "#35b779"),
    ("#35b779", "#1f9e89"),
    ("#1f9e89", "#26828e"),
    ("#26828e", "#31688e"),
    ("#31688e", "#3e4989"),
    ("#3e4989", "#440154"),
]
TIMELINE_VISIBLE_FILES = 3

# 日志里只排除机器生成的 README 提交；旧 vault backup 由 LLM 摘要替换。
AUTOMATION_PATTERNS = [
    r"\[skip ci\]",
    r"auto[- ]?updat",
]
GENERIC_MESSAGES = {"readme", "first backup", "dify"}


def run_git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotepath=false", *args],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def md_files_in(folder):
    out = []
    for p in folder.rglob("*.md"):
        if any(part in EXCLUDE_DIRS for part in p.relative_to(folder).parts):
            continue
        out.append(p)
    return out


def count_chars(text):
    """剥掉 markdown 语法 / 空白后按字符计（中文友好）。"""
    t = re.sub(r"```.*?```", "", text, flags=re.S)
    t = re.sub(r"\[\[(.+?)\]\]", r"\1", t)
    t = re.sub(r"[#*`>|!\[\]\-()]", "", t)
    t = re.sub(r"\s+", "", t)
    return len(t)


def count_links(text):
    return len(re.findall(r"\[\[(.+?)\]\]", text))


def scan_subjects():
    subjects = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in EXCLUDE_DIRS:
            continue
        mds = md_files_in(d)
        if not mds:
            continue
        chars = links = 0
        for m in mds:
            try:
                txt = m.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                txt = ""
            chars += count_chars(txt)
            links += count_links(txt)
        subjects.append({"name": d.name, "notes": len(mds), "chars": chars, "links": links})
    subjects.sort(key=lambda x: x["chars"], reverse=True)
    return subjects


def is_automation(msg, email=""):
    return ("github-actions" in email.lower()
            and any(re.search(p, msg, re.I) for p in AUTOMATION_PATTERNS))


def needs_llm_summary(msg):
    normalized = msg.strip()
    return (bool(re.match(r"^vault backup:", normalized, re.I))
            or bool(re.fullmatch(r"\d+", normalized))
            or normalized.lower() in GENERIC_MESSAGES)


def load_history_summaries():
    try:
        data = json.loads(HISTORY_SUMMARIES.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    summaries = data.get("summaries") if isinstance(data, dict) else None
    if not isinstance(summaries, dict):
        return {}
    valid = {}
    for commit_hash, entry in summaries.items():
        summary = entry.get("summary") if isinstance(entry, dict) else entry
        if (not isinstance(commit_hash, str)
                or not re.fullmatch(r"[0-9a-f]{40}", commit_hash)
                or not isinstance(summary, str)):
            continue
        summary = summary.strip()
        if not summary or any(char in summary for char in "\r\n") or len(summary) > 50:
            continue
        valid[commit_hash] = summary
    return valid


def git_timeline(n=None):
    summaries = load_history_summaries()
    out = run_git("log", "--no-merges", "--find-renames", "--diff-filter=ACMRTD",
                  "--pretty=format:%x1e%H%x1f%s%x1f%cI%x1f%ae%x00",
                  "--name-status", "-z")
    items = []
    for record in out.split("\x1e"):
        header_line, separator, changes_blob = record.partition("\x00")
        if not separator:
            continue
        header = header_line.split("\x1f", 3)
        if len(header) != 4:
            continue
        commit_hash, original_msg, ci, email = header
        if is_automation(original_msg, email):
            continue
        msg = summaries.get(commit_hash, original_msg)
        try:
            dt = datetime.fromisoformat(ci.strip().replace("Z", "+00:00"))
        except ValueError:
            continue
        changes = []
        tokens = changes_blob.split("\x00")
        index = 0
        while index < len(tokens):
            status_text = tokens[index].strip()
            index += 1
            if not status_text:
                continue
            status = status_text[:1]
            if status in {"R", "C"}:
                if index + 1 >= len(tokens):
                    break
                changes.append({"status": status, "old_path": tokens[index],
                                "path": tokens[index + 1]})
                index += 2
            elif status in {"A", "M", "T", "D"}:
                if index >= len(tokens):
                    break
                changes.append({"status": status, "path": tokens[index]})
                index += 1
        items.append({"hash": commit_hash, "message": msg, "datetime": dt,
                      "changes": changes})
    items.sort(key=lambda item: (item["datetime"].astimezone(DISPLAY_TIMEZONE),
                                 item["hash"]), reverse=True)
    return items[:n] if n is not None else items


def git_daily_counts(weeks=26):
    out = run_git("log", f"--since={weeks} weeks ago", "--pretty=format:%cI")
    counts = defaultdict(int)
    for timestamp in out.splitlines():
        try:
            local_day = (
                datetime.fromisoformat(timestamp.strip().replace("Z", "+00:00"))
                .astimezone(DISPLAY_TIMEZONE)
                .date()
                .isoformat()
            )
        except ValueError:
            continue
        counts[local_day] += 1
    return counts


def git_record_days():
    """统计历史中实际修改过笔记文件的自然日数量。"""
    pathspecs = [f":(top,glob,icase)**/*{ext}" for ext in sorted(NOTE_EXTENSIONS)]
    pathspecs.extend(f":(top,exclude,icase){path}" for path in sorted(NON_NOTE_PATHS))
    pathspecs.extend(
        f":(top,glob,exclude,icase)**/{folder}/**" for folder in sorted(EXCLUDE_DIRS)
    )
    out = run_git("log", "--full-history", "--no-merges", "--find-renames",
                  "--diff-filter=ACMRD", "--pretty=format:%cI", "--", *pathspecs)
    days = set()
    for timestamp in out.splitlines():
        try:
            day = (
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                .astimezone(DISPLAY_TIMEZONE)
                .date()
                .isoformat()
            )
        except ValueError:
            continue
        days.add(day)
    return len(days)


def fmt_chars(n):
    return f"{n/10000:.1f}万" if n >= 10000 else str(n)


def gen_stats(total_notes, total_chars, n_subjects, total_links, record_days):
    """页脚一行灰色小字，替代原来的彩色徽章。"""
    return (f"<sub>{total_notes} 篇笔记 · {fmt_chars(total_chars)}字 · "
            f"{n_subjects} 个科目 · {total_links} 处双向链接 · "
            f"累计记录 {record_days} 天</sub>")


def gen_word_swatches():
    """生成固定尺寸的渐变色块；级别越高，颜色越深。"""
    ASSETS.mkdir(parents=True, exist_ok=True)
    total = len(WORD_SWATCH_GRADIENTS)
    for level, (start, end) in enumerate(WORD_SWATCH_GRADIENTS):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18">
<title>字数热度 {level + 1}/{total}</title>
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/>
</linearGradient></defs>
<rect x="0.5" y="0.5" width="17" height="17" rx="3.5" fill="url(#g)" stroke="#8c959f"/>
</svg>
'''
        (ASSETS / f"word-level-{level}.svg").write_text(svg, encoding="utf-8")


def word_level(chars, min_chars, max_chars):
    if max_chars <= min_chars:
        return len(WORD_SWATCH_GRADIENTS) // 2
    low, high = math.log1p(min_chars), math.log1p(max_chars)
    normalized = (math.log1p(chars) - low) / (high - low)
    return max(0, min(len(WORD_SWATCH_GRADIENTS) - 1,
                      round(normalized * (len(WORD_SWATCH_GRADIENTS) - 1))))


def gen_tree(subjects):
    """目录导航：展示全部顶层科目，并用字数映射固定大小的渐变色块。"""
    if not subjects:
        return '<p align="center"><em>暂无科目</em></p>'
    min_chars = min(s["chars"] for s in subjects)
    max_chars = max(s["chars"] for s in subjects)
    lines = [
        '<table align="center">',
        '  <thead>',
        '    <tr>',
        '      <th align="center">科目</th>',
        '      <th align="center">笔记数</th>',
        '      <th align="center">字数</th>',
        '    </tr>',
        '  </thead>',
        '  <tbody>',
    ]
    for s in subjects:
        level = word_level(s["chars"], min_chars, max_chars)
        name = html.escape(s["name"])
        lines.append(
            f'    <tr><td align="center"><a href="./{quote(s["name"])}">{name}</a></td>'
            f'<td align="center"><code>{s["notes"]}</code></td>'
            f'<td align="center"><img src="./.github/assets/word-level-{level}.svg" '
            f'width="16" height="16" alt="字数热度 {level + 1}/{len(WORD_SWATCH_GRADIENTS)}"> '
            f'<code>{fmt_chars(s["chars"])}</code></td></tr>'
        )
    lines.extend(['  </tbody>', '</table>'])
    return "\n".join(lines)


def gen_heatmap(daily_counts, weeks=26):
    """GitHub 贡献图风格的日历热力图（小圆角绿格 + 星期/月份标签 + 图例）。"""
    CELL, GAP = 11, 3
    STEP = CELL + GAP
    PAD_L, PAD_T = 30, 20
    today = datetime.now(DISPLAY_TIMEZONE).date()
    # 起点对齐到周日（GitHub 顶行是周日）
    start = today - timedelta(days=weeks * 7 - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    n_cols = (today - start).days // 7 + 1

    grid_w = PAD_L + n_cols * STEP
    width = grid_w + 6
    height = PAD_T + 7 * STEP + 26  # 底部留给图例

    green = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

    def level(n):
        if n <= 0:
            return 0
        if n == 1:
            return 1
        if n <= 3:
            return 2
        if n <= 6:
            return 3
        return 4

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">']

    # 月份标签（相邻标签太近则跳过，避免拥挤）
    last_month = None
    last_label_x = -999
    for c in range(n_cols):
        col_first = start + timedelta(days=c * 7)
        if col_first.month != last_month:
            last_month = col_first.month
            x = PAD_L + c * STEP
            if x < grid_w - 14 and x - last_label_x >= 3 * STEP:
                p.append(f'<text x="{x}" y="{PAD_T - 6}" font-size="10" '
                         f'fill="#768390">{col_first.month}月</text>')
                last_label_x = x

    # 星期标签（周一/三/五）
    for row, label in [(1, "一"), (3, "三"), (5, "五")]:
        y = PAD_T + row * STEP + CELL - 1
        p.append(f'<text x="6" y="{y}" font-size="9" fill="#768390">{label}</text>')

    # 格子
    for c in range(n_cols):
        for r in range(7):
            d = start + timedelta(days=c * 7 + r)
            if d > today:
                continue
            n = daily_counts.get(d.isoformat(), 0)
            x = PAD_L + c * STEP
            y = PAD_T + r * STEP
            p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
                     f'fill="{green[level(n)]}"><title>{d.isoformat()}：{n} 次提交</title></rect>')

    # 图例：少 ▢▢▢▢▢ 多
    ly = PAD_T + 7 * STEP + 12
    lx = grid_w - (5 * STEP + 44)
    p.append(f'<text x="{lx}" y="{ly + CELL - 2}" font-size="9" fill="#768390">少</text>')
    for i in range(5):
        x = lx + 20 + i * STEP
        p.append(f'<rect x="{x}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
                 f'fill="{green[i]}"/>')
    p.append(f'<text x="{lx + 20 + 5 * STEP + 2}" y="{ly + CELL - 2}" '
             f'font-size="9" fill="#768390">多</text>')

    p.append('</svg>')
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "heatmap.svg").write_text("\n".join(p), encoding="utf-8")
    return ('<p align="center">'
            '<img src="./.github/assets/heatmap.svg" alt="活跃热力图">'
            '</p>')


def gen_timeline(items):
    if not items:
        return '<p align="center"><em>暂无更新记录</em></p>'
    lines = [
        '<table align="center">',
        '  <tbody>',
    ]
    for item in items:
        msg, dt, changes = item["message"], item["datetime"], item["changes"]
        local_dt = dt.astimezone(DISPLAY_TIMEZONE)
        iso_time = dt.isoformat(timespec="seconds")
        fallback = local_dt.strftime("%Y-%m-%d %H:%M")
        display_time = local_dt.strftime("%m-%d&nbsp;%H:%M")
        file_lines = []
        for change in changes:
            status, path = change["status"], change["path"]
            label = html.escape(path).replace("/", "/&ZeroWidthSpace;")
            current_path = (ROOT / path).exists()
            if status in {"R", "C"}:
                old_path = change["old_path"]
                old_label = html.escape(old_path).replace("/", "/&ZeroWidthSpace;")
                old_markup = (f'<del><code>{old_label}</code></del>' if status == "R"
                              else f'<code>{old_label}</code>')
                if current_path:
                    new_markup = f'<a href="./{quote(path)}"><code>{label}</code></a>'
                else:
                    new_markup = f'<del><code>{label}</code></del> <em>现已删除</em>'
                file_lines.append(f'{old_markup} &rarr; {new_markup}')
            elif status == "D":
                file_lines.append(f'<del><code>{label}</code></del> <em>该提交删除</em>')
            elif current_path:
                file_lines.append(f'<a href="./{quote(path)}"><code>{label}</code></a>')
            else:
                file_lines.append(f'<del><code>{label}</code></del> <em>现已删除</em>')
        visible_files = file_lines[:TIMELINE_VISIBLE_FILES]
        hidden_files = file_lines[TIMELINE_VISIBLE_FILES:]
        file_block = f'<br/>{"<br/>".join(visible_files)}' if visible_files else ""
        if hidden_files:
            file_block += (
                f'<details><summary>其余 {len(hidden_files)} 个文件</summary>'
                f'{"<br/>".join(hidden_files)}</details>'
            )
        lines.append(
            f'    <tr><td align="right" valign="top"><code>{display_time}</code></td>'
            f'<td align="left"><strong>{html.escape(msg)}</strong> '
            f'<sub><relative-time datetime="{iso_time}" lang="zh-CN">'
            f'{fallback}</relative-time></sub>{file_block}</td></tr>'
        )
    lines.extend(['  </tbody>', '</table>'])
    return "\n".join(lines)


def github_repo_url():
    remote = run_git("remote", "get-url", "origin").strip()
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.removeprefix("git@github.com:")
    if remote.startswith("https://github.com/"):
        return remote.removesuffix(".git")
    return ""


def history_bucket(dt, now=None):
    now = (now or datetime.now(DISPLAY_TIMEZONE)).astimezone(DISPLAY_TIMEZONE)
    local_dt = dt.astimezone(DISPLAY_TIMEZONE)
    if local_dt.year != now.year:
        return "year", local_dt.strftime("%Y")
    if local_dt.month != now.month:
        return "month", local_dt.strftime("%Y-%m")
    return "day", local_dt.strftime("%Y-%m-%d")


def gen_history_archive(items, now=None):
    if not items:
        return '<p align="center"><em>暂无历史日志</em></p>'

    groups = {}
    ordered_items = sorted(
        items,
        key=lambda item: (
            item["datetime"].astimezone(DISPLAY_TIMEZONE), item["hash"]
        ),
        reverse=True,
    )
    for item in ordered_items:
        bucket = history_bucket(item["datetime"], now)
        groups.setdefault(bucket, []).append(item)

    repo_url = github_repo_url()
    lines = []
    for (_, label), entries in groups.items():
        lines.append('<details>')
        lines.append(
            f'<summary><strong>{html.escape(label)}</strong> · '
            f'<code>{len(entries)}</code> 次更新</summary>'
        )
        lines.extend(['<table align="center">', '  <tbody>'])
        for item in entries:
            commit_hash = item["hash"]
            local_dt = item["datetime"].astimezone(DISPLAY_TIMEZONE)
            display_time = local_dt.strftime("%m-%d&nbsp;%H:%M")
            short_hash = commit_hash[:7]
            if repo_url:
                commit_url = html.escape(f"{repo_url}/commit/{commit_hash}", quote=True)
                commit_markup = f'<a href="{commit_url}"><code>{short_hash}</code></a>'
            else:
                commit_markup = f'<code>{short_hash}</code>'
            lines.append(
                f'    <tr><td align="right"><code>{display_time}</code></td>'
                f'<td align="left">{html.escape(item["message"])} · '
                f'{commit_markup}</td></tr>'
            )
        lines.extend(['  </tbody>', '</table>', '</details>'])
    return "\n".join(lines)


def replace_block(content, name, new_inner):
    pat = re.compile(rf"(<!-- AUTOGEN:{name} -->)(.*?)(<!-- /AUTOGEN:{name} -->)", re.S)
    if not pat.search(content):
        print(f"WARN: block {name} not found in README")
        return content, False
    return pat.sub(lambda m: f"{m.group(1)}\n{new_inner}\n{m.group(3)}", content), True


def main():
    subjects = scan_subjects()
    total_notes = sum(s["notes"] for s in subjects)
    total_chars = sum(s["chars"] for s in subjects)
    total_links = sum(s["links"] for s in subjects)
    record_days = git_record_days()
    gen_word_swatches()

    timeline_items = git_timeline()
    blocks = {
        "stats": gen_stats(total_notes, total_chars, len(subjects), total_links, record_days),
        "tree": gen_tree(subjects),
        "heatmap": gen_heatmap(git_daily_counts(26), 26),
        "timeline": gen_timeline(timeline_items[:10]),
        "history": gen_history_archive(timeline_items[10:]),
    }

    content = README.read_text(encoding="utf-8")
    for name, inner in blocks.items():
        content, _ = replace_block(content, name, inner)
    README.write_text(content, encoding="utf-8")
    print(f"updated: notes={total_notes} chars={total_chars} subjects={len(subjects)} "
          f"links={total_links} record_days={record_days}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
