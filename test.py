import logging
from app.services.feishu_service import FeishuService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def test_fetch_signup_data():
    try:
        # 创建 FeishuService 实例
        service = FeishuService()

        # 测试链接
        test_url = "https://hackathonweekly.feishu.cn/base/W5MxbvxwzaPe4yss6uacOKaMnsh?table=tblzscrkKqRba5r6&view=vewgZcoSqS"

        print("\n=== 开始测试多维表数据获取 ===")
        print(f"测试链接: {test_url}")

        # 获取数据
        signup_data = service.fetch_signup_data(test_url)

        print("\n=== 测试完成 ===")
        print(f"成功获取 {len(signup_data)} 条记录")

        return True
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        return False


if __name__ == "__main__":
    test_fetch_signup_data()
