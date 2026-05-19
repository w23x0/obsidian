import os
import re
import json
import subprocess
from openai import OpenAI

# ── 排除的非学科目录 ──────────────────────────────────────────────
EXCLUDE_DIRS = {
    '.git', '.github', '__pycache__', '.pytest_cache',
    '.obsidian', 'png', 'img', 'images', 'assets'
}

# ── DeepSeek 客户端 ───────────────────────────────────────────────
def get_client():
    return OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

# ── 扫描目录结构 ──────────────────────────────────────────────────
def scan_directories():
    """返回 {一级目录: [二级目录, ...]} 的字典，排除系统文件夹"""
    result = {}
    for d1 in sorted(os.listdir('.')):
        if not os.path.isdir(d1) or d1 in EXCLUDE_DIRS or d1.startswith('.'):
            continue
        sub = []
        for d2 in sorted(os.listdir(d1)):
            path2 = os.path.join(d1, d2)
            if os.path.isdir(path2) and d2 not in EXCLUDE_DIRS and not d2.startswith('.'):
                sub.append(d2)
        result[d1] = sub
    return result

# ── AI 判断哪些目录是学科 ─────────────────────────────────────────
def ai_identify_subjects(dir_tree: dict) -> list[dict]:
    """
    传入目录树，让 AI 返回学科列表。
    返回格式：[{"path": "线性代数18.06sc", "name": "线性代数", "icon": "📐"}, ...]
    """
    tree_text = "\n".join(
        f"  {d1}/\n" + "".join(f"    {d2}/\n" for d2 in subs)
        for d1, subs in dir_tree.items()
    )

    prompt = f"""以下是一个个人学习笔记仓库的目录结构：

{tree_text}

请判断哪些一级目录是学科/课程笔记（排除工具、素材、杂项等），
并为每个学科返回一个 JSON 数组，格式严格如下，不要输出任何其他内容：

[
  {{"path": "目录名", "name": "简洁中文学科名", "icon": "一个emoji"}}
]"""

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw = resp.choices[0].message.content.strip()
        # 去掉可能的 markdown 代码块
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[warn] AI 识别学科失败: {e}")
        return []

# ── 读取目录下所有 md 文件内容（截断避免超 token）─────────────────
def read_md_content(path: str, max_chars: int = 4000) -> str:
    text = ""
    if not os.path.exists(path):
        return text
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith('.md'):
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as fh:
                        text += fh.read() + "\n"
                        if len(text) >= max_chars:
                            return text[:max_chars]
                except Exception:
                    pass
    return text[:max_chars]

# ── AI 生成进展摘要 ───────────────────────────────────────────────
def ai_summary(subject_name: str, content: str) -> str:
    if not content.strip():
        return "暂无笔记内容"
    try:
        client = get_client()
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个严格的学习进度分析器。根据笔记内容，"
                        "用一句极其精简、客观的话总结当前学习焦点或核心难点。"
                        "严禁比喻和修饰词，字数控制在20字以内。"
                    )
                },
                {
                    "role": "user",
                    "content": f"学科：{subject_name}\n笔记内容：\n{content}"
                }
            ],
            temperature=0.2
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "摘要获取失败"

# ── Git 时间信息 ──────────────────────────────────────────────────
def git_dates(path: str) -> tuple[str, str]:
    """返回 (最早commit日期, 最近commit日期)"""
    def run(cmd):
        try:
            out = subprocess.check_output(cmd, shell=True).decode().strip()
            return out.split('\n')[0] if out else "N/A"
        except Exception:
            return "N/A"

    start = run(f'git log --reverse --format=%cd --date=format:%Y-%m-%d -- "{path}"')
    last  = run(f'git log -1 --format=%cd --date=format:%Y-%m-%d -- "{path}"')
    return start, last

# ── 生成目录树 markdown ───────────────────────────────────────────
def generate_directory_tree(dir_tree: dict) -> str:
    lines = ["."]
    items = list(dir_tree.items())
    for i, (d1, subs) in enumerate(items):
        is_last = (i == len(items) - 1)
        lines.append(("└── " if is_last else "├── ") + d1 + "/")
        indent = "    " if is_last else "│   "
        for j, d2 in enumerate(subs):
            lines.append(indent + ("└── " if j == len(subs)-1 else "├── ") + d2 + "/")
    lines.append("└── README.md")
    return "\n".join(lines)

# ── 主函数 ────────────────────────────────────────────────────────
def update_readme():
    # 读取 README
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    if "<!-- TIMELINE_START -->" not in content:
        raise RuntimeError("README.md 缺少 <!-- TIMELINE_START --> 锚点")
    if "<!-- TREE_START -->" not in content:
        raise RuntimeError("README.md 缺少 <!-- TREE_START --> 锚点")

    # 1. 扫描目录
    dir_tree = scan_directories()

    # 2. AI 识别学科
    subjects = ai_identify_subjects(dir_tree)
    print(f"[info] 识别到 {len(subjects)} 个学科: {[s['path'] for s in subjects]}")

    # 3. 生成学科看板表格
    table_lines = [
        "| 学科 | 开始时间 | 最后活跃 | AI 核心进展摘要 |",
        "| :--- | :---: | :---: | :--- |"
    ]

    for s in subjects:
        path   = s.get("path", "")
        name   = s.get("name", path)
        icon   = s.get("icon", "📚")
        start, last = git_dates(path)
        md_text     = read_md_content(path)
        summary     = ai_summary(name, md_text)
        table_lines.append(f"| {icon} {name} | {start} | {last} | {summary} |")

    table_content = "\n".join(table_lines)

    # 4. 生成目录树
    tree_content = f"```text\n{generate_directory_tree(dir_tree)}\n```"

    # 5. 写回 README
    content = re.sub(
        r"(<!-- TIMELINE_START -->)[\s\S]*?(<!-- TIMELINE_END -->)",
        f"\\1\n{table_content}\n\\2",
        content
    )
    content = re.sub(
        r"(<!-- TREE_START -->)[\s\S]*?(<!-- TREE_END -->)",
        f"\\1\n{tree_content}\n\\2",
        content
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

    print("[info] README.md 更新完成")

if __name__ == "__main__":
    update_readme()