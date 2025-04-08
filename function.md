# 开发者共创活动机器人功能设计

## 1. 活动管理功能

### 1.1 期数管理
- 自动生成每期活动ID（如：2024-03）
- 支持设置活动起止时间
- 活动状态管理（报名中/进行中/已结束）
- 自动发送活动开始，即活动接龙，和结束提醒，即打卡总结

### 1.2 接龙处理
#### 报名格式
```
#接龙
🌟本期目标制定：
1⃣ 修改群昵称为「昵称-开发者/观察者-专注领域」
2⃣ 自我介绍并抛出你本期的目标

快来加入我们，一起在公开环境中构建未来吧！Let's build it openly! 💻⛓🤖

示例：
1. 张三-开发者-前端开发
   简介：3年前端开发经验，热爱开源
   目标：完成一个开源组件库的开发
```

#### 功能实现
- 自动识别接龙消息格式
- 解析并存储成员信息：
  - 昵称
  - 角色（开发者/观察者）
  - 专注领域
  - 自我介绍
  - 本期目标
- 生成接龙汇总报告

## 2. 打卡功能

### 2.1 打卡规则
- 触发格式：`#打卡 姓名 工作内容`

### 2.2 数据处理
- 数据库表设计：
  ```sql
  -- 活动期数表
  periods (
    id SERIAL PRIMARY KEY,
    period_name VARCHAR(20),    -- 例如：2024-03
    start_date TIMESTAMP,       -- 活动开始时间
    end_date TIMESTAMP,         -- 活动结束时间
    status VARCHAR(20)          -- 报名中/进行中/已结束
  )

  -- 接龙记录表
  signups (
    id SERIAL PRIMARY KEY,
    period_id INTEGER REFERENCES periods(id),
    nickname VARCHAR(50),       -- 昵称
    role VARCHAR(20),          -- 开发者/观察者
    focus_area TEXT,           -- 专注领域
    introduction TEXT,         -- 自我介绍
    goals TEXT,               -- 本期目标
    signup_time TIMESTAMP,    -- 接龙时间
    UNIQUE(period_id, nickname)
  )

  -- 打卡记录表
  checkins (
    id SERIAL PRIMARY KEY,
    signup_id INTEGER REFERENCES signups(id),  -- 关联到接龙记录
    checkin_date DATE,         -- 打卡日期
    content TEXT,              -- 打卡内容
    ai_feedback TEXT,          -- AI反馈内容
    created_at TIMESTAMP       -- 打卡时间
  )

  -- 统计视图（便于查询）
  CREATE VIEW period_stats AS
  SELECT 
    p.period_name,
    s.nickname,
    s.role,
    COUNT(c.id) as checkin_count,
    MAX(c.checkin_date) as last_checkin_date
  FROM periods p
  JOIN signups s ON p.id = s.period_id
  LEFT JOIN checkins c ON s.id = c.signup_id
  GROUP BY p.period_name, s.nickname, s.role;
  ```

- 数据关联逻辑：
  1. 每个活动期数创建一条 periods 记录
  2. 用户接龙时创建 signups 记录
  3. 打卡时通过 nickname 关联到 signups 记录
  4. 统计时可通过视图快速获取数据

### 2.3 AI 反馈
- 识别"#打卡"标签，自动反馈，实现夸奖打卡者
- 根据以下维度生成反馈：
  - 本期目标进度（从 signups 表获取目标）
  - 历史打卡内容（从 checkins 表获取）
  - 个人特点（基于 introduction 和历史数据）
  - 夸奖鼓励
- AI 回复模板设计
- 敏感词过滤

### 2.4 数据查询示例
```sql
-- 获取某期活动的打卡情况
SELECT 
  s.nickname,
  s.goals,
  COUNT(c.id) as checkin_count
FROM signups s
LEFT JOIN checkins c ON s.id = c.signup_id
WHERE s.period_id = ?
GROUP BY s.nickname, s.goals;

-- 获取某用户的打卡历史
SELECT 
  c.checkin_date,
  c.content,
  c.ai_feedback
FROM signups s
JOIN checkins c ON s.id = c.signup_id
WHERE s.nickname = ? AND s.period_id = ?
ORDER BY c.checkin_date DESC;

-- 获取当日未打卡成员
SELECT s.nickname
FROM signups s
LEFT JOIN checkins c ON s.id = c.signup_id 
  AND c.checkin_date = CURRENT_DATE
WHERE s.period_id = ? AND c.id IS NULL;
```

## 3. 数据统计与可视化

### 3.1 实时统计
- 当前期数参与情况
- 每日打卡率
- 成员活跃度排名
- 目标完成进度

### 3.2 定期报告
- 周报（每周日晚自动生成）
  - 本周打卡情况
  - 活跃成员TOP3
  - 精选打卡内容
- 月报（每月最后一天生成）
  - 月度统计数据
  - 目标达成情况
  - 优秀成员展示

### 3.3 数据导出
- 支持导出Excel格式
- 支持生成飞书文档

## 4. 技术实现与维护

### 4.1 基础架构
- 后端：Python + FastAPI
- 数据库：PostgreSQL
- 缓存：Redis
- 部署：Docker + 云服务器

### 4.2 监控告警
- 接口响应时间监控
- 错误日志监控
- 系统资源监控
- 异常情况告警

### 4.3 数据安全
- 数据定期备份
- 敏感信息加密
- 访问权限控制
- 操作日志记录

### 4.4 性能优化
- 消息队列处理并发
- 数据库查询优化
- 缓存策略优化
- 定时任务调度

## 5. 后续规划

### 5.1 功能迭代
- 支持多群组管理
- 引入积分机制
- 添加项目展示功能
- 集成代码仓库数据

### 5.2 用户体验
- 自定义打卡提醒
- 个性化数据展示
- 互动功能增强
- 操作指令简化