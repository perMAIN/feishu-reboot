 

一个基于 Python + FastAPI 开发的飞书机器人，用于管理"Build In Public - 独立开发者21天线上活动"。该机器人支持活动报名管理、打卡统计、AI 反馈等功能。

## 功能特性

### 1. 活动管理
- 自动生成活动期数（YYYY-MM 格式）
- 活动状态流转（报名中 -> 进行中 -> 已结束）
- 接龙数据同步（支持飞书多维表格）
- 防重复创建机制

### 2. 打卡系统
- 支持每日打卡记录
- AI 智能反馈
- 打卡统计和进度追踪
- 自动去重和验证

### 3. 智能反馈
- 基于 DeepSeek API 的智能反馈
- 考虑历史打卡记录
- 个性化鼓励和建议
- 活泼友好的互动风格

## 技术栈

- 后端框架：Python + FastAPI
- 数据库：MySQL
- ORM：SQLAlchemy
- AI 服务：DeepSeek API
- 消息平台：飞书开放平台

## 部署步骤

### 1. 环境要求
- Python 3.x
- MySQL 5.7+
- 飞书开放平台账号
- DeepSeek API 密钥

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 数据库配置
```bash
# 创建数据库和表
mysql -u root -p < feishu_bot.sql
```

### 4. 环境变量配置
复制 `.env.example` 到 `.env` 并配置以下参数：
```env
# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/feishu_bot

# DeepSeek API配置
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_API_ENDPOINT=https://xxxx

# 飞书配置
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
```

### 5. 启动服务
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 机器人命令

### 活动管理命令
- 发起接龙：发送接龙卡片
- `#接龙结束`：结束报名，同步数据
- `#活动结束`：结束当前活动期

### 打卡命令
```
#打卡 昵称 工作内容
```
- 限制：
  - 内容长度：2-500字
  - 频率：每人每天一次
  - 条件：活动进行中且已报名

## 数据库结构

### 主要表
1. periods（活动期数表）
   - 管理活动期数和状态
   - 存储接龙表格链接

2. signups（报名记录表）
   - 记录用户报名信息
   - 存储用户目标和专注领域

3. checkins（打卡记录表）
   - 记录每日打卡内容
   - 追踪打卡次数和时间

详细的数据库结构见 `feishu_bot.sql`

## 开发说明

### 目录结构
```
app/
├── models/         # 数据模型
│   └── database.py # 数据库模型定义
├── services/       # 业务逻辑
│   ├── message_handler.py  # 消息处理
│   ├── feishu_service.py   # 飞书API
│   └── openai_service.py   # AI服务
└── utils/          # 工具函数
```

### 关键文件
- `main.py`：应用入口和路由配置
- `app/services/message_handler.py`：消息处理核心逻辑
- `app/services/feishu_service.py`：飞书API交互
- `app/services/openai_service.py`：AI反馈生成

## 错误处理

### 常见问题
1. 数据库连接失败
   - 检查数据库配置
   - 确保MySQL服务运行中
   
2. API调用失败
   - 验证API密钥配置
   - 检查网络连接

3. 消息重复处理
   - 系统已包含消息去重机制
   - 检查日志中的消息ID

## 日志说明

系统使用分级日志：
- INFO：常规操作日志
- WARNING：需要注意的异常情况
- ERROR：严重错误

## 维护建议

1. 定期检查
   - 数据库连接状态
   - API 调用额度
   - 日志文件大小

2. 数据备份
   - 定期备份数据库
   - 保存重要日志

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或联系管理员。