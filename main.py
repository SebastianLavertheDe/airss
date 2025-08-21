#!/usr/bin/env python3
"""
RSS Hub AI - 智能社交媒体RSS监控工具
重构后的主入口文件
"""

import gc
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入重构后的模块
from src.core.monitor import SocialMediaMonitor


def main():
    """主函数"""
    try:
        monitor = SocialMediaMonitor()
        
        print("🌟 智能社交媒体RSS监控工具 (重构版)")
        print("=" * 50)
        print("✨ 模块化架构，清晰的代码结构!")
        
        # 显示支持的平台
        platforms = monitor.config.get_platforms()
        print(f"🎯 支持平台: {', '.join(p.upper() for p in platforms)}")
        print("=" * 50)
        
        # 显示用户列表
        monitor.list_users()
        
        # 显示平台统计
        # monitor.get_platform_stats()
        
        # 测试：只监控特定用户
        monitor.monitor_specific_user("dotey")
        
        # 监控所有用户
        # monitor.monitor_all_users()
        
        # 示例：监控特定用户
        # monitor.monitor_specific_user("GitHub_Daily")
        
        # 示例：动态添加用户（需要指定平台）
        # monitor.add_user("elonmusk", "Elon Musk", "twitter")
        # monitor.add_user("5722964389", "某微博用户", "weibo")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断监控")
    except Exception as e:
        print(f"❌ 程序执行出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        gc.collect()
        print("\n🔚 监控结束")


if __name__ == "__main__":
    main()
