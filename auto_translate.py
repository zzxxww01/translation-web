#!/usr/bin/env python3
"""
自动翻译脚本 - 自动处理术语冲突
"""

import requests
import json
import time
import threading
from datetime import datetime

PROJECT_ID = "rl-environments-and-rl-for-science-data-foundries"
API_BASE = "http://127.0.0.1:54321"
MODEL = "deepseek-relay"

def log(msg_type, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    # 移除 emoji 避免 Windows GBK 编码问题
    message = message.replace('✓', '[OK]').replace('⚠️', '[WARN]').replace('⚠', '[WARN]')
    print(f"[{timestamp}] [{msg_type:8s}] {message}", flush=True)

def resolve_conflict(term, chosen_translation):
    """解决术语冲突"""
    try:
        url = f"{API_BASE}/api/projects/{PROJECT_ID}/resolve-conflict-live"
        response = requests.post(
            url,
            json={
                "term": term,
                "chosen_translation": chosen_translation,
                "apply_to_all": True
            },
            timeout=10
        )
        if response.status_code == 200:
            log("RESOLVE", f"已解决冲突: {term} -> {chosen_translation}")
            return True
        else:
            log("ERROR", f"解决冲突失败: {response.status_code}")
            return False
    except Exception as e:
        log("ERROR", f"解决冲突异常: {e}")
        return False

def auto_resolve_conflict(conflict_data):
    """自动决策如何解决冲突"""
    term = conflict_data.get('term', '')
    new_translation = conflict_data.get('new_translation', '')
    existing_translation = conflict_data.get('existing_translation', '')
    context = conflict_data.get('new_context', '')

    # 自动决策规则
    # 1. 如果是专有名词（如公司名、产品名），保持原文
    # 2. 如果有现有翻译，优先使用现有翻译
    # 3. 否则使用新翻译

    if existing_translation:
        chosen = existing_translation
        log("CONFLICT", f"术语冲突: {term}, 使用现有翻译: {chosen}")
    else:
        chosen = new_translation
        log("CONFLICT", f"术语冲突: {term}, 使用新翻译: {chosen}")

    # 在新线程中解决冲突，避免阻塞主流
    threading.Thread(target=resolve_conflict, args=(term, chosen)).start()

def translate():
    """执行翻译"""
    url = f"{API_BASE}/api/projects/{PROJECT_ID}/translate-four-step"

    log("INFO", "=" * 60)
    log("INFO", f"项目: {PROJECT_ID}")
    log("INFO", f"模型: {MODEL}")
    log("INFO", "=" * 60)

    start_time = time.time()
    stats = {
        "total": 0,
        "translated": 0,
        "errors": 0,
        "conflicts": 0,
        "last_step": "",
    }

    try:
        response = requests.post(
            url,
            json={"model": MODEL},
            stream=True,
            timeout=7200
        )

        if response.status_code != 200:
            log("ERROR", f"API 错误: {response.status_code}")
            log("ERROR", response.text)
            return False

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')
            if not line.startswith('data: '):
                continue

            try:
                data = json.loads(line[6:])
            except:
                continue

            event_type = data.get('type')

            if event_type == 'start':
                stats['total'] = data.get('total', 0)
                sections = data.get('total_sections', 0)
                log("INFO", f"开始翻译: {stats['total']} 段落, {sections} 章节")

            elif event_type == 'progress':
                step = data.get('step', '')
                current = data.get('current', 0)
                total = data.get('total', 0)

                # 只显示不同的步骤
                if step != stats['last_step']:
                    if total > 0:
                        pct = (current / total) * 100
                        log("PROGRESS", f"{step} ({current}/{total}, {pct:.1f}%)")
                    else:
                        log("PROGRESS", step)
                    stats['last_step'] = step

            elif event_type == 'term_conflict':
                stats['conflicts'] += 1
                conflict = data.get('conflict', {})
                auto_resolve_conflict(conflict)

            elif event_type == 'error':
                stats['errors'] += 1
                error_msg = data.get('error', '')
                para_id = data.get('paragraph_id', '')

                # 检查 API 余额问题
                error_keywords = ['insufficient', 'quota', 'balance', 'limit', 'exceeded']
                if any(kw in error_msg.lower() for kw in error_keywords):
                    log("CRITICAL", "=" * 60)
                    log("CRITICAL", "[CRITICAL] API 余额不足或超出限制！")
                    log("CRITICAL", f"错误信息: {error_msg}")
                    log("CRITICAL", "=" * 60)
                    return False

                log("ERROR", f"段落 {para_id}: {error_msg}")

            elif event_type == 'complete':
                elapsed = time.time() - start_time
                translated = data.get('translated_count', 0)
                total = data.get('total', 0)

                log("SUCCESS", "=" * 60)
                log("SUCCESS", "[OK] 翻译完成！")
                log("SUCCESS", f"已翻译: {translated}/{total}")
                log("SUCCESS", f"错误数: {stats['errors']}")
                log("SUCCESS", f"冲突数: {stats['conflicts']}")
                log("SUCCESS", f"耗时: {elapsed/60:.1f} 分钟 ({elapsed:.0f} 秒)")
                log("SUCCESS", "=" * 60)
                return True

            elif event_type == 'incomplete':
                elapsed = time.time() - start_time
                translated = data.get('translated_count', 0)
                total = data.get('total', 0)
                message = data.get('message', '')

                log("WARNING", "=" * 60)
                log("WARNING", "[WARN] 翻译未完全完成")
                log("WARNING", f"消息: {message}")
                log("WARNING", f"已翻译: {translated}/{total}")
                log("WARNING", f"错误数: {stats['errors']}")
                log("WARNING", f"冲突数: {stats['conflicts']}")
                log("WARNING", f"耗时: {elapsed/60:.1f} 分钟")
                log("WARNING", "=" * 60)
                return False

            elif event_type == 'cancelled':
                log("WARNING", f"翻译已取消: {data.get('message', '')}")
                return False

            elif event_type == 'heartbeat':
                pass  # 忽略心跳

        log("WARNING", "流结束但未收到完成事件")
        return False

    except KeyboardInterrupt:
        log("INFO", "用户中断")
        return False
    except requests.exceptions.Timeout:
        log("ERROR", "请求超时")
        return False
    except Exception as e:
        log("ERROR", f"异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = translate()
    exit(0 if success else 1)
