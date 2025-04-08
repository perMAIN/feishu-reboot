-- 创建活动期数表
CREATE TABLE IF NOT EXISTS periods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    period_name VARCHAR(20) NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- 创建接龙记录表
CREATE TABLE IF NOT EXISTS signups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    period_id INT,
    nickname VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    focus_area TEXT,
    introduction TEXT,
    goals TEXT,
    signup_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_id, nickname),
    FOREIGN KEY (period_id) REFERENCES periods(id)
);

-- 创建打卡记录表
CREATE TABLE IF NOT EXISTS checkins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    signup_id INT,
    checkin_date DATE NOT NULL,
    content TEXT NOT NULL,
    ai_feedback TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signup_id) REFERENCES signups(id)
);

-- 创建统计视图
CREATE OR REPLACE VIEW period_stats AS
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

-- 插入测试期数
INSERT INTO periods (period_name, start_date, end_date, status)
SELECT 
    DATE_FORMAT(CURRENT_DATE, '%Y-%m'),
    CURRENT_TIMESTAMP,
    DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 30 DAY),
    '报名中'
WHERE NOT EXISTS (
    SELECT 1 FROM periods 
    WHERE status IN ('报名中', '进行中')
); 