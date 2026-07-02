#!/usr/bin/env python3
"""扫描 vault 结构 + 读 git log，重新生成 README 的 AUTOGEN 区域。"""
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
EXCLUDE_DIRS = {".obsidian", ".git", "assets", "scripts", ".github", "node_modules"}


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
    subjects.sort(key=lambda x: x["notes"], reverse=True)
    return subjects


def git_timeline(n=10):
    out = run_git("log", f"--max-count={n*4}", "--pretty=format:%s|%ci")
    items = []
    for line in out.strip().splitlines():
        if "|" not in line:
            continue
        msg, ci = line.rsplit("|", 1)
        msg = msg.strip()
        if re.match(r"^vault backup:", msg):  # 过滤无信息条目
            continue
        try:
            dt = datetime.strptime(ci.strip()[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        items.append((msg, dt))
    return items[:n]


def git_recent_files(n=8):
    out = run_git("log", "--name-only", "--pretty=format:%ci", f"--max-count={n*6}")
    seen = {}
    cur_dt = None
    for line in out.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}", line):
            try:
                cur_dt = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                cur_dt = None
            continue
        if line.endswith(".md") and line not in seen and cur_dt:
            seen[line] = cur_dt
    return sorted(seen.items(), key=lambda x: x[1], reverse=True)[:n]


def git_daily_counts(weeks=12):
    out = run_git("log", f"--since={weeks} weeks ago", "--pretty=format:%ad", "--date=short")
    counts = defaultdict(int)
    for line in out.strip().splitlines():
        line = line.strip()
        if line:
            counts[line] += 1
    return counts


def git_streak():
    out = run_git("log", "--pretty=format:%ad", "--date=short")
    days = sorted(set(l.strip() for l in out.strip().splitlines() if l.strip()), reverse=True)
    if not days:
        return 0
    try:
        latest = datetime.strptime(days[0], "%Y-%m-%d").date()
    except ValueError:
        return 0
    if (date.today() - latest).days > 1:
        return 0
    streak = 1
    prev = latest
    for d in days[1:]:
        try:
            cur = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (prev - cur).days == 1:
            streak += 1
            prev = cur
        else:
            break
    return streak


def relative_time(dt):
    delta = datetime.now() - dt
    if delta.days == 0:
        h = delta.seconds // 3600
        return f"{h}小时前" if h else "刚刚"
    if delta.days == 1:
        return "昨天"
    if delta.days < 30:
        return f"{delta.days}天前"
    return f"{delta.days//30}个月前"


def gen_badges(total_notes, total_chars, n_subjects, total_links, streak):
    def badge(label, val, color, logo=""):
        lp = f"&logo={logo}&logoColor=white" if logo else ""
        return (f'<img src="https://img.shields.io/badge/{label}-{val}-{color}'
                f'?style=for-the-badge&labelColor=1a1b27{lp}" alt="{label}">')
    chars_disp = f"{total_chars/10000:.1f}万" if total_chars >= 10000 else str(total_chars)
    imgs = [
        badge("笔记总数", total_notes, "4c8bf5"),
        badge("总字数", chars_disp, "7c3aed"),
        badge("科目数", n_subjects, "2ea44f"),
        badge("双向链接", total_links, "f59e0b"),
        badge("连续记录", f"{streak}天", "ef4444"),
    ]
    return '<div align="center">\n\n' + "\n".join(imgs) + '\n\n</div>'


def gen_tree(subjects, total_notes):
    if not subjects:
        return "_(暂无科目)_"
    lines = ["", "| 科目 | 笔记数 | 字数 | 占比 |", "| :--- | :---: | :---: | :--- |"]
    max_notes = subjects[0]["notes"]
    for s in subjects:
        pct = s["notes"] / total_notes * 100 if total_notes else 0
        bar_len = int(s["notes"] / max_notes * 20) if max_notes else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)
        chars_disp = f"{s['chars']/10000:.1f}万" if s["chars"] >= 10000 else str(s["chars"])
        lines.append(f"| [{s['name']}](./{quote(s['name'])}) | `{s['notes']}` | `{chars_disp}` | `{bar}` {pct:.0f}% |")
    return "\n".join(lines)


def gen_heatmap(daily_counts, weeks=12):
    today = date.today()
    start = today - timedelta(days=weeks * 7 - 1)
    cell, gap = 13, 3
    w = weeks * (cell + gap) + 40
    h = 7 * (cell + gap) + 30

    def color(n):
        if n == 0:
            return "#161b22"
        if n == 1:
            return "#3b1d6e"
        if n <= 2:
            return "#5b2ba0"
        if n <= 4:
            return "#7c3aed"
        return "#a855f7"

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for c in range(weeks):
        for r in range(7):
            d = start + timedelta(days=c * 7 + r)
            if d > today:
                continue
            n = daily_counts.get(d.isoformat(), 0)
            x = 30 + c * (cell + gap)
            y = 10 + r * (cell + gap)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{color(n)}"><title>{d.isoformat()}: {n} 次提交</title></rect>'
            )
    parts.append('</svg>')
    svg = "\n".join(parts)
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "heatmap.svg").write_text(svg, encoding="utf-8")
    return '<img src="./assets/heatmap.svg" alt="笔记活跃热力图" width="100%">'


def gen_timeline(items):
    if not items:
        return "_(暂无更新记录)_"
    return "\n".join(
        f"- 📝 `{dt.strftime('%m-%d %H:%M')}` · {msg} <sub>{relative_time(dt)}</sub>"
        for msg, dt in items
    )


def gen_recent(items):
    if not items:
        return "_(暂无)_"
    return "\n".join(
        f"- [{Path(p).stem}](./{quote(p)}) <sub>{relative_time(dt)}</sub>"
        for p, dt in items
    )


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
    streak = git_streak()

    blocks = {
        "badges": gen_badges(total_notes, total_chars, len(subjects), total_links, streak),
        "tree": gen_tree(subjects, total_notes),
        "heatmap": gen_heatmap(git_daily_counts(12), 12),
        "timeline": gen_timeline(git_timeline(10)),
        "recent": gen_recent(git_recent_files(8)),
    }

    content = README.read_text(encoding="utf-8")
    for name, inner in blocks.items():
        content, _ = replace_block(content, name, inner)
    README.write_text(content, encoding="utf-8")
    print(f"updated: notes={total_notes} chars={total_chars} subjects={len(subjects)} "
          f"links={total_links} streak={streak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
