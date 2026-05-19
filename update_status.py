import os
import re
import subprocess
from openai import OpenAI

# 【在此处微调你的学科目录路径、显示名称和预计结束时间】
SUBJECTS = {
    "Computer-Science/CPP-Memory-Model": {
        "icon": "🛠️", 
        "name": "C++ 核心与内存模型", 
        "end_point": "2026-06-30"
    },
    "Mathematics/Linear-Algebra": {
        "icon": "📐", 
        "name": "线性代数 (MIT 18.06)", 
        "end_point": "2026-07-15"
    },
    "Physics-and-Circuits/Differential-Eq": {
        "icon": "⚡", 
        "name": "物理与电路微分方程", 
        "end_point": "2026-08-30"
    }
}

# 需要排除的无关系统文件夹
EXCLUDE_DIRS = {'.git', '.github', '__pycache__', '.pytest_cache'}

def get_git_start_date(path):
    try:
        cmd = f'git log --reverse --format=%cd --date=format:%Y-%m-%d -- "{path}"'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        if output:
            return output.split('\n')[0]
        return "N/A"
    except Exception:
        return "N/A"

def calculate_progress(path):
    total_tasks = 0
    completed_tasks = 0
    all_text = ""
    
    if not os.path.exists(path):
        return 0, "⏸️ 未开始", "尚无笔记数据"

    task_re = re.compile(r'^\s*-\s*\[([ xX])\]\s+(.+)$')

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.md'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_text += content + "\n"
                    f.seek(0)
                    for line in f:
                        match = task_re.match(line)
                        if match:
                            total_tasks += 1
                            if match.group(1).lower() == 'x':
                                completed_tasks += 1

    if total_tasks == 0:
        return 0, "🔄 连载中", all_text
        
    percentage = int((completed_tasks / total_tasks) * 100)
    status = "✅ 已结课" if percentage == 100 else "🔄 进行中"
    return percentage, status, all_text

def get_deepseek_summary(text_content):
    if not text_content.strip():
        return "暂无具体学习记录"
    
    try:
        client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        
        system_prompt = (
            "你是一个严格的底层技术分析器。请根据输入的学习笔记内容，用一句极其精简、"
            "绝对客观的话总结当前的学习焦点或核心攻克难点。严禁使用任何比喻，"
            "严禁使用客套话与总结性修饰词，字数严格控制在 20 字以内。"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"笔记内容如下：\n{text_content[:4000]}"}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI 摘要获取失败"

def generate_progress_bar(percentage):
    done = percentage // 10
    remain = 10 - done
    return f"`{'█' * done}{'░' * remain}` **{percentage}%**"

def generate_directory_tree():
    """精确扫描并生成根目录与二级文件夹的树状图"""
    tree_lines = ["."]
    # 获取根目录下的第一级目录（排除了隐藏文件夹和指定排除项）
    level1_dirs = sorted([
        d for d in os.listdir('.') 
        if os.path.isdir(d) and d not in EXCLUDE_DIRS and not d.startswith('.')
    ])
    
    for i, d1 in enumerate(level1_dirs):
        is_last_l1 = (i == len(level1_dirs) - 1)
        l1_prefix = "└── " if is_last_l1 else "├── "
        tree_lines.append(f"{l1_prefix}{d1}/")
        
        # 获取第二级子目录
        path_l1 = os.path.join('.', d1)
        level2_dirs = sorted([
            d for d in os.listdir(path_l1) 
            if os.path.isdir(os.path.join(path_l1, d)) and d not in EXCLUDE_DIRS
        ])
        
        for j, d2 in enumerate(level2_dirs):
            is_last_l2 = (j == len(level2_dirs) - 1)
            # 根据一级目录是否是最后一个，决定前缀是空格还是线条
            indent = "    " if is_last_l1 else "│   "
            l2_prefix = "└── " if is_last_l2 else "├── "
            tree_lines.append(f"{indent}{l2_prefix}{d2}/")
            
    # 补齐尾部的 README.md 展示
    tree_lines.append("└── README.md")
    return "\n".join(tree_lines)

def update_readme():
    # 1. 动态生成并替换学科看板
    table_lines = [
        "| 学科分类 | 开始时间 | 目标结课时间 | 当前进度 (动态计算) | 当前状态 | AI 核心进展摘要 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for path, info in SUBJECTS.items():
        start_date = get_git_start_date(path)
        percentage, status, text_content = calculate_progress(path)
        bar = generate_progress_bar(percentage)
        
        ai_summary = get_deepseek_summary(text_content) if status != "⏸️ 未开始" else "尚未启动进程"
        
        subject_display = f"{info['icon']} {info['name']}"
        table_lines.append(f"| {subject_display} | {start_date} | {info['end_point']} | {bar} | {status} | {ai_summary} |")

    table_content = "\n".join(table_lines)

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern_timeline = r"(<!-- TIMELINE_START -->)[\s\S]*?(<!-- TIMELINE_END -->)"
    content = re.sub(pattern_timeline, f"\\1\n{table_content}\n\\2", content)

    # 2. 动态生成并替换目录树
    tree_content = f"```text\n{generate_directory_tree()}\n```"
    pattern_tree = r"(<!-- TREE_START -->)[\s\S]*?(<!-- TREE_END -->)"
    content = re.sub(pattern_tree, f"\\1\n{tree_content}\n\\2", content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_readme()