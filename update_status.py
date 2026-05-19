import os
import re
import subprocess
from datetime import datetime

# 配置学科目录与预期结束时间（硬编码或读取config.json）
SUBJECTS = {
    "Computer-Science/CPP-Memory-Model": {"name": "🛠️ C++ 核心与内存模型", "end_point": "2026-06-30"},
    "Mathematics/Linear-Algebra": {"name": "📐 线性代数 (MIT 18.06)", "end_point": "2026-07-15"},
    "Physics-and-Circuits/Differential-Eq": {"name": "⚡ 物理与电路微分方程", "end_point": "2026-08-30"}
}

def get_git_start_date(path):
    """通过 Git 管道获取目录中第一个 commit 的日期"""
    try:
        cmd = f"git log --reverse --format=%cd --date=format:%Y-%m-%d -- \"{path}\""
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        if output:
            return output.split('\n')[0] # 取最早的一条
        return "N/A"
    except Exception:
        return "N/A"

def calculate_progress(path):
    """扫描目录下所有 Markdown 的任务列表状态"""
    total_tasks = 0
    completed_tasks = 0
    
    if not os.path.exists(path):
        return 0, "⏸️ 未开始"

    # 编译正则提高匹配效率
    task_re = re.compile(r'^\s*-\s*\[([ xX])\]\s+(.+)$')

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.md'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    for line in f:
                        match = task_re.match(line)
                        if match:
                            total_tasks += 1
                            if match.group(1).lower() == 'x':
                                completed_tasks += 1

    if total_tasks == 0:
        return 0, "🔄 连载中" # 没有任务列表时默认的状态
        
    percentage = int((completed_tasks / total_tasks) * 100)
    status = "✅ 已结课" if percentage == 100 else "🔄 进行中"
    return percentage, status

def generate_progress_bar(percentage):
    """生成字符级进度条"""
    done = percentage // 10
    remain = 10 - done
    return f"`{'█' * done}{'░' * remain}` **{percentage}%**"

def update_readme():
    # 生成新的表格文本
    table_lines = [
        "| 学科分类 | 开始时间 | 目标结课时间 | 当前进度 (动态计算) | 当前状态 |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]

    for path, info in SUBJECTS.items():
        start_date = get_git_start_date(path)
        percentage, status = calculate_progress(path)
        bar = generate_progress_bar(percentage)
        table_lines.append(f"| {info['name']} | {start_date} | {info['end_point']} | {bar} | {status} |")

    table_content = "\n".join(table_lines)

    # 读取并回写 README
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    # 精准正则替换锚点间的内容
    pattern = r"()[\s\S]*?()"
    updated_content = re.sub(pattern, f"\\1\n{table_content}\n\\2", content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_content)

if __name__ == "__main__":
    update_readme()