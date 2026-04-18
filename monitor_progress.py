#!/usr/bin/env python3
"""监控翻译进度"""
import time
from pathlib import Path

project_dir = Path("projects/rl-environments-and-rl-for-science-data-foundries/sections")
total_sections = 13

while True:
    translation_files = list(project_dir.glob("*/translation.md"))
    completed = len(translation_files)

    print(f"\r[{time.strftime('%H:%M:%S')}] 已完成章节: {completed}/{total_sections} ({completed/total_sections*100:.1f}%)", end="", flush=True)

    if completed >= total_sections:
        print("\n翻译完成！")
        break

    time.sleep(10)
