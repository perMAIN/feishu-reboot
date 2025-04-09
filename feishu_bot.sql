-- MySQL dump
-- Host: localhost
-- Generation Time: Mar 2024

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `feishu_bot` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `feishu_bot`;

-- 活动期数表
DROP TABLE IF EXISTS `periods`;
CREATE TABLE `periods` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `period_name` varchar(50) NOT NULL,
  `start_date` datetime NOT NULL,
  `end_date` datetime NOT NULL,
  `status` varchar(20) NOT NULL,
  `signup_link` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `period_name` (`period_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 报名记录表
DROP TABLE IF EXISTS `signups`;
CREATE TABLE `signups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `period_id` int(11) NOT NULL,
  `nickname` varchar(50) NOT NULL,
  `focus_area` text DEFAULT NULL,
  `introduction` text DEFAULT NULL,
  `goals` text DEFAULT NULL,
  `signup_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `period_nickname` (`period_id`, `nickname`),
  CONSTRAINT `fk_signup_period` FOREIGN KEY (`period_id`) REFERENCES `periods` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 打卡记录表
DROP TABLE IF EXISTS `checkins`;
CREATE TABLE `checkins` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `signup_id` int(11) NOT NULL,
  `nickname` varchar(100) NOT NULL,
  `checkin_date` date NOT NULL,
  `content` text NOT NULL,
  `checkin_count` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_checkin_signup` (`signup_id`),
  CONSTRAINT `fk_checkin_signup` FOREIGN KEY (`signup_id`) REFERENCES `signups` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建统计视图
DROP VIEW IF EXISTS `period_stats`;
CREATE VIEW `period_stats` AS
SELECT 
  p.period_name,
  s.nickname,
  COUNT(c.id) as checkin_count,
  MAX(c.checkin_date) as last_checkin_date
FROM periods p
JOIN signups s ON p.id = s.period_id
LEFT JOIN checkins c ON s.id = c.signup_id
GROUP BY p.period_name, s.nickname;

SET FOREIGN_KEY_CHECKS = 1;