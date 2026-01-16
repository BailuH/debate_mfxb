#!/usr/bin/env python3
"""
System test for the Digital Courtroom API
"""

import asyncio
import json
from src.services.court_service import court_service


async def test_court_system():
    """测试法庭系统"""
    print("🧪 开始测试法庭系统...\n")

    # 测试1: 创建会话
    print("1. 测试创建会话...")
    try:
        session_id = await court_service.create_session(
            case_info="张三于2023年1月向李四借款10万元，约定3个月归还，但至今未还。",
            case_evidence=[
                {"speaker": "原告律师", "content": "借条照片：显示张三于2023年1月15日借款10万元"}
            ],
            human_role=None,  # 纯AI模式
        )
        print(f"✅ 会话创建成功: {session_id}\n")
    except Exception as e:
        print(f"❌ 会话创建失败: {str(e)}\n")
        return

    # 测试2: 获取会话状态
    print("2. 测试获取会话状态...")
    try:
        session_data = await court_service.get_session(session_id)
        print(f"✅ 获取状态成功:")
        print(f"   - 当前阶段: {session_data['current_phase']}")
        print(f"   - 当前发言人: {session_data['current_speaker']}")
        print(f"   - 消息数: {len(session_data['messages'])}")
        print(f"   - 轮次: {session_data['rounds']}\n")
    except Exception as e:
        print(f"❌ 获取状态失败: {str(e)}\n")
        return

    # 测试3: 推进辩论
    print("3. 测试推进辩论...")
    try:
        for i in range(3):  # 推进3步
            print(f"   第{i+1}步...")
            session_data = await court_service.advance_debate(session_id)

            if session_data['messages']:
                last_msg = session_data['messages'][-1]
                print(f"   💬 {last_msg['sender']}: {last_msg['content'][:100]}...")

            await asyncio.sleep(1)  # 等待1秒

        print(f"✅ 辩论推进完成\n")
    except Exception as e:
        print(f"❌ 辩论推进失败: {str(e)}\n")
        return

    # 测试4: 最终状态
    print("4. 测试最终状态...")
    try:
        session_data = await court_service.get_session(session_id)
        print(f"✅ 最终状态:")
        print(f"   - 当前阶段: {session_data['current_phase']}")
        print(f"   - 当前发言人: {session_data['current_speaker']}")
        print(f"   - 总消息数: {len(session_data['messages'])}")
        print(f"   - 总轮次: {session_data['rounds']}\n")
    except Exception as e:
        print(f"❌ 获取最终状态失败: {str(e)}\n")
        return

    # 显示完整对话
    print("5. 完整对话记录:")
    print("=" * 80)
    for msg in session_data['messages']:
        print(f"\n{msg['sender']}:")
        print(f"{msg['content']}")
    print("\n" + "=" * 80)

    # 清理
    await court_service.cleanup_session(session_id)
    print("\n✅ 测试完成，会话已清理")


if __name__ == "__main__":
    asyncio.run(test_court_system())
