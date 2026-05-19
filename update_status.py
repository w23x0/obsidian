import os
import re
import subprocess
from openai import OpenAI

SUBJECTS = {
    "Computer-Science/CPP-Memory-Model": {"name": "🛠️ C++ 核心与内存模型", "end_point": "2026-06-30"},
    "Mathematics/Linear-Algebra": {"name": "📐 线性代数 (MIT 18.06)", "end_point": "2026-07-15"},
    "Physics-and-Circuits/Differential-Eq": {"name": "⚡ 物理与电路微分方程", "end_point": "2026-08-30"}
}

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

def get_ai_summary(text_content):
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

def update_readme():
    table_lines = [
        "| 学科分类 | 开始时间 | 目标结课时间 | 当前进度 (动态计算) | 当前状态 | AI 核心进展摘要 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for path, info in SUBJECTS.items():
        start_date = get_git_start_date(path)
        percentage, status, text_content = calculate_progress(path)
        bar = generate_progress_bar(percentage)
        
        ai_summary = get_ai_summary(text_content) if status != "⏸️ 未开始" else "尚未启动进程"
        
        table_lines.append(f"| {info['name']} | {start_date} | {info['end_point']} | {bar} | {status} | {ai_summary} |")

    table_content = "\n".join(table_lines)

    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"()[\s\S]*?()"
    updated_content = re.sub(pattern, f"\\1\n{table_content}\n\\2", content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_content)

if __name__ == "__main__":
    update_readme()