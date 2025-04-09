from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import pymysql
pymysql.install_as_MySQLdb()


Base = declarative_base()


class Period(Base):
    __tablename__ = 'periods'

    id = Column(Integer, primary_key=True)
    period_name = Column(String(50), unique=True, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False)  # 报名中/进行中/已结束
    signup_link = Column(String(500))  # 新增：存储接龙链接

    signups = relationship(
        "Signup", back_populates="period", cascade="all, delete-orphan")


class Signup(Base):
    __tablename__ = 'signups'

    id = Column(Integer, primary_key=True)
    period_id = Column(Integer, ForeignKey('periods.id'), nullable=False)
    nickname = Column(String(50), nullable=False)
    focus_area = Column(Text)
    introduction = Column(Text)
    goals = Column(Text)
    signup_time = Column(DateTime, default=datetime.now)

    period = relationship("Period", back_populates="signups")
    checkins = relationship("Checkin", back_populates="signup")

    __table_args__ = (UniqueConstraint('period_id', 'nickname'),)


class Checkin(Base):
    __tablename__ = 'checkins'

    id = Column(Integer, primary_key=True)
    signup_id = Column(Integer, ForeignKey('signups.id'), nullable=False)
    nickname = Column(String(100), nullable=False)  # 添加昵称字段
    checkin_date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    checkin_count = Column(Integer)  # 添加打卡次数字段

    signup = relationship("Signup", back_populates="checkins")


# 数据库连接

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://root:123456@localhost:3306/feishu_bot")
engine = create_engine(DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
