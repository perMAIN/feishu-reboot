from app.models.database import Base, engine, init_db
from datetime import datetime, timedelta


def create_tables():
    """创建所有数据表"""
    print("开始创建数据表...")
    init_db()
    print("数据表创建完成！")


def create_test_period():
    """创建测试期数"""
    from app.models.database import Period, SessionLocal

    db = SessionLocal()
    try:
        # 检查是否已存在活动期数
        existing_period = db.query(Period).filter(
            Period.status.in_(['报名中', '进行中'])).first()
        if not existing_period:
            # 创建新的活动期数
            now = datetime.now()
            new_period = Period(
                period_name=now.strftime("%Y-%m"),
                start_date=now,
                end_date=now + timedelta(days=30),
                status="报名中"
            )
            db.add(new_period)
            db.commit()
            print(f"创建测试期数成功：{new_period.period_name}")
        else:
            print(f"已存在活动期数：{existing_period.period_name}")
    except Exception as e:
        print(f"创建测试期数失败：{str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    create_test_period()
