#!/usr/bin/env python3
"""
使用 DeepSeek v3.2 模型翻译 RL Environments 项目的脚本
监控翻译进度、错误、警告和 API 余额问题
"""

import requests
import json
import time
from datetime import datetime

PROJECT_ID = "rl-environments-and-rl-for-science-data-foundries"
API_BASE = "http://127.0.0.1:54321"
MODEL = "deepseek-relay"  # 使用 deepseek-relay 别名

def log_message(msg_type, message):
    """记录带时间戳的消息"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{msg_type}] {message}")

def translate_project():
    """调用四步法翻译接口"""
    url = f"{API_BASE}/api/projects/{PROJECT_ID}/translate-four-step"

    log_message("INFO", f"开始翻译项目: {PROJECT_ID}")
    log_message("INFO", f"使用模型: {MODEL}")

    start_time = time.time()

    try:
        response = requests.post(
            url,
            json={"model": MODEL},
            stream=True,
            timeout=7200  # 2小时超时
        )

        if response.status_code != 200:
            log_message("ERROR", f"API 返回错误状态码: {response.status_code}")
            log_message("ERROR", f"响应内容: {response.text}")
            return False

        # 统计信息
        stats = {
            "total": 0,
            "translated": 0,
            "skipped": 0,
            "errors": 0,
            "term_conflicts": 0,
            "current_step": "",
        }

        # 处理 SSE 流
        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')

            # 跳过非数据行
            if not line.startswith('data: '):
                continue

            # 解析 JSON 数据
            try:
                data = json.loads(line[6:])  # 去掉 "data: " 前缀
            except json.JSONDecodeError as e:
                log_message("WARNING", f"无法解析 JSON: {line}")
                continue

            event_type = data.get('type')

            # 处理不同类型的事件
            if event_type == 'start':
                stats['total'] = data.get('total', 0)
                log_message("INFO", f"开始翻译，共 {stats['total']} 个段落")

            elif event_type == 'progress':
                step = data.get('step', '')
                current = data.get('current', 0)
                total = data.get('total', 0)
                stats['current_step'] = step

                # 计算进度百分比
                if total > 0:
                    percentage = (current / total) * 100
                    log_message("PROGRESS", f"{step}: {current}/{total} ({percentage:.1f}%)")
                else:
                    log_message("PROGRESS", f"{step}: {current}/{total}")

            elif event_type == 'translated':
                stats['translated'] += 1
                section_id = data.get('section_id', '')
                paragraph_id = data.get('paragraph_id', '')
                log_message("SUCCESS", f"已翻译段落 {paragraph_id} (章节: {section_id})")

            elif event_type == 'skip':
                stats['skipped'] += 1

            elif event_type == 'error':
                stats['errors'] += 1
                error_msg = data.get('error', '未知错误')
                paragraph_id = data.get('paragraph_id', '')

                # 检查是否是 API 余额不足错误
                if 'insufficient' in error_msg.lower() or 'quota' in error_msg.lower() or 'balance' in error_msg.lower():
                    log_message("CRITICAL", f"API 余额不足！错误: {error_msg}")
                    log_message("CRITICAL", "停止翻译任务")
                    return False

                log_message("ERROR", f"翻译段落 {paragraph_id} 失败: {error_msg}")

            elif event_type == 'term_conflict':
                stats['term_conflicts'] += 1
                conflict = data.get('conflict', {})
                term = conflict.get('term', '')
                log_message("WARNING", f"术语冲突: {term}")
                log_message("WARNING", f"冲突详情: {json.dumps(conflict, ensure_ascii=False)}")

            elif event_type == 'complete':
                elapsed = time.time() - start_time
                translated_count = data.get('translated_count', 0)
                total = data.get('total', 0)

                log_message("SUCCESS", "=" * 60)
                log_message("SUCCESS", "翻译完成！")
                log_message("SUCCESS", f"总段落数: {total}")
                log_message("SUCCESS", f"已翻译: {translated_count}")
                log_message("SUCCESS", f"跳过: {stats['skipped']}")
                log_message("SUCCESS", f"错误: {stats['errors']}")
                log_message("SUCCESS", f"术语冲突: {stats['term_conflicts']}")
                log_message("SUCCESS", f"耗时: {elapsed:.2f} 秒 ({elapsed/60:.2f} 分钟)")
                log_message("SUCCESS", "=" * 60)
                return True

            elif event_type == 'incomplete':
                elapsed = time.time() - start_time
                translated_count = data.get('translated_count', 0)
                total = data.get('total', 0)
                message = data.get('message', '')

                log_message("WARNING", "=" * 60)
                log_message("WARNING", "翻译未完全完成")
                log_message("WARNING", f"消息: {message}")
                log_message("WARNING", f"已翻译: {translated_count}/{total}")
                log_message("WARNING", f"错误数: {stats['errors']}")
                log_message("WARNING", f"耗时: {elapsed:.2f} 秒 ({elapsed/60:.2f} 分钟)")
                log_message("WARNING", "=" * 60)
                return False

            elif event_type == 'cancelled':
                message = data.get('message', '')
                log_message("WARNING", f"翻译已取消: {message}")
                return False

            elif event_type == 'heartbeat':
                # 心跳事件，不记录
                pass

            else:
                log_message("DEBUG", f"未知事件类型: {event_type}, 数据: {json.dumps(data, ensure_ascii=False)}")

        # 如果流结束但没有收到完成事件
        elapsed = time.time() - start_time
        log_message("WARNING", f"流结束但未收到完成事件，耗时: {elapsed:.2f} 秒")
        return False

    except requests.exceptions.Timeout:
        log_message("ERROR", "请求超时")
        return False
    except requests.exceptions.ConnectionError as e:
        log_message("ERROR", f"连接错误: {e}")
        return False
    except Exception as e:
        log_message("ERROR", f"未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    log_message("INFO", "=" * 60)
    log_message("INFO", "RL Environments 项目翻译脚本")
    log_message("INFO", "=" * 60)

    success = translate_project()

    if success:
        log_message("INFO", "翻译任务成功完成")
        exit(0)
    else:
        log_message("ERROR", "翻译任务失败或未完成")
        exit(1)
