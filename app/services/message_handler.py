import json
import re
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.database import Period, Signup, Checkin
from .openai_service import generate_ai_feedback
from .feishu_service import FeishuService
import os
import requests
import time

# 配置日志
logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, db: Session):
        self.db = db
        self.feishu_service = FeishuService()
        self._processed_messages = set()  # 用于存储已处理的消息ID

    def handle_message(self, message_content: str, chat_id: str, message_type: str = "text", message_id: str = None) -> str:
        """处理接收到的消息"""
        logger.info(f"开始处理消息，类型: {message_type}, ID: {message_id}")
        
        # 如果消息ID存在且已处理过，则跳过
        if message_id:
            if message_id in self._processed_messages:
                logger.info(f"消息 {message_id} 已经处理过，跳过")
                return None
            self._processed_messages.add(message_id)
            
            # 保持集合大小在合理范围内，避免内存泄漏
            if len(self._processed_messages) > 1000:
                self._processed_messages.clear()

        logger.info(f"消息内容: {message_content}")

        if message_type == "interactive":
            try:
                content_json = json.loads(message_content)
                title = content_json.get("title", "").strip()
                logger.info(f"处理 interactive 消息，标题: {title}")

                # 检查是否为接龙消息
                if title == "🌟本期目标制定":
                    logger.info("检测到目标制定标题")
                    elements = content_json.get("elements", [])
                    logger.info(f"消息元素: {elements}")
                    
                    # 检查是否包含接龙说明文本和参与人数文本
                    has_signup_text = False
                    has_participants_text = False
                    has_link = False
                    
                    # 遍历所有元素组
                    for element_group in elements:
                        if isinstance(element_group, list):
                            # 检查每个元素组中的文本元素
                            for element in element_group:
                                if element.get("tag") == "text":
                                    text = element.get("text", "")
                                    # 检查接龙说明文本
                                    if "修改群昵称" in text and "自我介绍" in text and "本期目标" in text:
                                        has_signup_text = True
                                        logger.info("找到接龙说明文本")
                                    # 检查参与人数文本
                                    elif "当前" in text and "人参加群接龙" in text:
                                        has_participants_text = True
                                        logger.info(f"找到参与人数文本: {text}")
                                # 检查链接元素
                                elif element.get("tag") == "a" and element.get("href"):
                                    has_link = True
                                    logger.info("找到链接元素")
                    
                    logger.info(f"检查结果 - 接龙说明: {has_signup_text}, 参与人数: {has_participants_text}, 链接: {has_link}")
                    
                    # 只有在有接龙说明、有链接但没有参与人数时才创建新期数
                    if has_link and not has_participants_text:
                        logger.info("检测到新接龙消息，开始创建新期数")
                        return self.create_new_period(chat_id, message_content)
                    else:
                        if has_participants_text:
                            logger.info("检测到参与接龙消息，不进行处理")
                        else:
                            logger.info("消息格式不符合要求")
                        return None
                else:
                    logger.info(f"不是目标制定消息，标题为: {title}")

            except json.JSONDecodeError as e:
                logger.error(f"解析消息内容失败: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"处理消息时发生错误: {str(e)}")
                return None
        elif message_type == "text":
            if message_content.strip() == '#接龙结束':
                return self.handle_signup_end(chat_id)
            elif message_content.strip() == '#活动结束':
                return self.handle_activity_end(chat_id)
            elif message_content.startswith('#打卡'):
                return self.handle_checkin(message_content, chat_id)
        return None

    def create_new_period(self, chat_id: str, message_content: str) -> str:
        """创建新的活动期数"""
        try:
            logger.info("开始检查是否有正在进行的活动期数")
            # 检查是否有正在进行的活动期数
            existing_period = self.db.query(Period)\
                .filter(Period.status.in_(['报名中', '进行中']))\
                .first()

            if existing_period:
                error_msg = f"接龙失败：当前已有活动在进行中（{existing_period.period_name}，状态：{existing_period.status}）"
                logger.info(error_msg)
                return error_msg

            logger.info("获取最新的期数")
            try:
                # 解析消息内容获取接龙链接
                content_json = json.loads(message_content)
                elements = content_json.get("elements", [])
                signup_link = None

                # 查找链接元素
                for element_group in elements:
                    if isinstance(element_group, list):
                        for element in element_group:
                            if element.get("tag") == "a" and element.get("href"):
                                signup_link = element.get("href")
                                break
                    if signup_link:
                        break

                if not signup_link:
                    logger.warning("未找到接龙链接")

                # 获取最新的期数
                latest_period = self.db.query(Period)\
                    .order_by(Period.id.desc())\
                    .first()

                # 生成新的期数名称（格式：YYYY-MM）
                now = datetime.now()
                period_name = now.strftime("%Y-%m")

                if latest_period and latest_period.period_name == period_name:
                    # 如果同月已有期数，在月份后面加上字母
                    last_char = latest_period.period_name[-1]
                    if last_char.isalpha():
                        # 如果已经有字母，递增字母
                        next_char = chr(ord(last_char) + 1)
                        period_name = f"{period_name[:-1]}{next_char}"
                    else:
                        # 如果没有字母，添加字母a
                        period_name = f"{period_name}a"

                logger.info(f"准备创建新期数: {period_name}")
                # 创建新的活动期数，包含接龙链接
                new_period = Period(
                    period_name=period_name,
                    start_date=now,
                    end_date=now + timedelta(days=30),
                    status='报名中',
                    signup_link=signup_link
                )
                self.db.add(new_period)
                self.db.commit()
                logger.info(f"成功创建新期数: {period_name}")

                return "本期接龙已开启，请大家踊跃报名！"

            except Exception as e:
                error_msg = f"接龙失败：创建新期数时发生错误 - {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.db.rollback()
                return error_msg

        except Exception as e:
            error_msg = f"接龙失败：检查活动状态时发生错误 - {str(e)}"
            logger.error(error_msg, exc_info=True)
            if 'session' in dir(self.db):
                self.db.rollback()
            return error_msg

    def handle_signup_end(self, chat_id: str) -> str:
        """处理接龙结束命令"""
        try:
            logger.info("开始处理接龙结束命令")
            # 获取当前报名中的活动期数
            current_period = self.db.query(Period)\
                .filter(Period.status == '报名中')\
                .first()

            if not current_period:
                error_msg = "接龙结束失败：没有正在进行的接龙活动"
                logger.info(error_msg)
                return error_msg

            if not current_period.signup_link:
                error_msg = "接龙结束失败：未找到接龙链接"
                logger.info(error_msg)
                return error_msg

            try:
                # 从飞书多维表获取数据
                logger.info(f"开始从多维表获取数据: {current_period.signup_link}")
                signup_data = self.feishu_service.fetch_signup_data(current_period.signup_link)
                
                if not signup_data:
                    error_msg = "接龙结束失败：未获取到有效的报名数据"
                    logger.error(error_msg)
                    return error_msg

                # 清除当前期数的所有报名记录
                self.db.query(Signup)\
                    .filter(Signup.period_id == current_period.id)\
                    .delete()
                logger.info(f"已清除期数 {current_period.period_name} 的现有报名记录")

                # 处理并添加新的报名记录
                success_count = 0
                developers = []
                for record in signup_data:
                    try:
                        # 获取昵称和专注领域
                        nickname = record.get('nickname', '').strip()
                        focus_area = record.get('focus_area', '未知').strip()
                        introduction = record.get('introduction', '').strip()
                        goals = record.get('goals', '').strip()
                        signup_time = record.get('signup_time', datetime.now())

                        if not nickname:
                            logger.warning("跳过空昵称的记录")
                            continue

                        logger.info(f"处理报名记录 - 昵称: {nickname}, 专注领域: {focus_area}")
                        logger.info(f"自我介绍: {introduction}")
                        logger.info(f"目标: {goals}")

                        # 创建新的报名记录
                        signup = Signup(
                            period_id=current_period.id,
                            nickname=nickname,
                            focus_area=focus_area,
                            introduction=introduction,
                            goals=goals,
                            signup_time=signup_time
                        )
                        self.db.add(signup)
                        success_count += 1
                        
                        # 收集开发者信息用于总结
                        developers.append({
                            'nickname': nickname,
                            'focus_area': focus_area
                        })
                        
                        logger.info(f"成功添加报名记录: {nickname}")
                    except Exception as e:
                        logger.error(f"处理报名记录时出错: {str(e)}")
                        continue

                if success_count == 0:
                    error_msg = "接龙结束失败：没有成功添加任何报名记录"
                    logger.error(error_msg)
                    self.db.rollback()
                    return error_msg

                # 更新活动状态为已结束
                current_period.status = '进行中'
                self.db.commit()
                logger.info(f"成功更新活动期数 {current_period.period_name} 状态为已结束")
                logger.info(f"总共处理了 {success_count} 条报名记录")

                # 生成报名统计信息
                total_signups = len(developers)
                focus_area_groups = {}
                
                for dev in developers:
                    focus_area = dev['focus_area']
                    if focus_area not in focus_area_groups:
                        focus_area_groups[focus_area] = []
                    focus_area_groups[focus_area].append(dev['nickname'])
                
                # 构建响应消息
                response_lines = ["✨ 本期接龙结束，祝大家开发旅途愉快！\n"]
                response_lines.append(f"📊 {current_period.period_name}期接龙数据汇总")
                response_lines.append(f"总参与人数：{total_signups}人\n")
                
                # 按专注领域分组显示
                response_lines.append("🌟 参与者名单：")
                for focus_area, nicknames in focus_area_groups.items():
                    response_lines.append(f"\n{focus_area}：")
                    for nickname in nicknames:
                        response_lines.append(f"- {nickname}")
                
                response_lines.append("\n\n祝愿大家在本期活动中收获满满！🎉")
                
                return "\n".join(response_lines)

            except Exception as e:
                error_msg = f"接龙结束失败：更新数据时发生错误 - {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.db.rollback()
                return error_msg

        except Exception as e:
            error_msg = f"接龙结束失败：处理命令时发生错误 - {str(e)}"
            logger.error(error_msg, exc_info=True)
            if 'session' in dir(self.db):
                self.db.rollback()
            return error_msg

    def handle_checkin(self, message_content: str, chat_id: str) -> str:
        """处理打卡消息"""
        logger.info(f"开始处理打卡消息: {message_content}")
        
        # 解析打卡信息
        pattern = r'#打卡\s+([\w-]+)\s+(.+)(?:\n|$)'
        match = re.search(pattern, message_content)

        if not match:
            error_msg = "📝 打卡格式不正确\n正确格式：#打卡 昵称 工作内容\n示例：#打卡 张三 完成了登录功能的开发"
            logger.info(f"打卡格式错误: {message_content}")
            return error_msg

        nickname = match.group(1)
        content = match.group(2).strip()

        # 检查工作内容
        if len(content) < 2:
            error_msg = "📝 打卡内容太短，请详细描述您的工作内容"
            logger.info(f"打卡内容过短: {content}")
            return error_msg
        
        if len(content) > 500:
            error_msg = "📝 打卡内容过长，请控制在500字以内"
            logger.info(f"打卡内容过长: {len(content)}字")
            return error_msg

        # 获取当前活动期数
        current_period = self.db.query(Period)\
            .filter(Period.status == '进行中')\
            .first()

        if not current_period:
            error_msg = "⚠️ 当前没有进行中的活动期数，请等待新的活动开始"
            logger.info("打卡失败：没有进行中的活动期数")
            return error_msg

        # 查找用户报名记录
        signup = self.db.query(Signup)\
            .filter(Signup.period_id == current_period.id)\
            .filter(Signup.nickname == nickname)\
            .first()

        if not signup:
            error_msg = f"⚠️ 未找到昵称为 {nickname} 的报名记录\n请先完成接龙或检查昵称是否正确"
            logger.info(f"打卡失败：未找到报名记录 - {nickname}")
            return error_msg

        try:
            # 检查是否重复打卡
            today = datetime.now().date()
            existing_checkin = self.db.query(Checkin)\
                .filter(Checkin.signup_id == signup.id)\
                .filter(Checkin.checkin_date == today)\
                .first()
            
            if existing_checkin:
                error_msg = "⚠️ 您今天已经打过卡了，明天再来吧！"
                logger.info(f"打卡失败：重复打卡 - {nickname}")
                return error_msg

            # 获取用户所有打卡记录
            user_checkins = self.db.query(Checkin)\
                .filter(Checkin.signup_id == signup.id)\
                .order_by(Checkin.checkin_date)\
                .all()

            # 创建打卡记录
            logger.info(f"创建打卡记录 - 用户: {nickname}, 内容长度: {len(content)}")
            checkin = Checkin(
                signup_id=signup.id,
                nickname=nickname,
                checkin_date=today,
                content=content,
                checkin_count=len(user_checkins) + 1
            )
            
            try:
                self.db.add(checkin)
                self.db.commit()
                logger.info(f"打卡记录添加成功 - 用户: {nickname}, 第 {len(user_checkins) + 1} 次打卡")
            except Exception as db_error:
                logger.error(f"数据库更新失败: {str(db_error)}")
                self.db.rollback()
                return "❌ 打卡失败，请稍后重试"

            # 生成打卡反馈
            try:
                logger.info(f"开始生成AI反馈 - 用户: {nickname}")
                retry_count = 3  # 最大重试次数
                ai_feedback = None
                
                while retry_count > 0:
                    try:
                        ai_feedback = generate_ai_feedback(
                            db=self.db,
                            signup_id=signup.id,
                            nickname=nickname,
                            goals=signup.goals,
                            content=content,
                            checkin_count=len(user_checkins) + 1
                        )
                        if ai_feedback:
                            break
                    except Exception as e:
                        logger.error(f"生成AI反馈失败 (还剩{retry_count-1}次重试): {str(e)}")
                        retry_count -= 1
                        if retry_count > 0:
                            # 短暂等待后重试
                            time.sleep(1)
                
                if ai_feedback:
                    return ai_feedback
                else:
                    return f"✨ 打卡成功！\n📝 第 {len(user_checkins) + 1}/21 次打卡\n\n继续加油，你的每一步进展都很棒！ 🌟"
                
            except Exception as ai_error:
                logger.error(f"AI反馈生成失败: {str(ai_error)}")
                return f"✨ 打卡成功！\n📝 第 {len(user_checkins) + 1}/21 次打卡\n\n继续加油，你的每一步进展都很棒！ 🌟"
            
        except Exception as e:
            error_msg = f"打卡失败：{str(e)}"
            logger.error(error_msg, exc_info=True)
            self.db.rollback()
            return "❌ 打卡失败，请稍后重试或联系管理员"

    async def handle_activity_end(self, message_id: str) -> str:
        """处理活动结束"""
        try:
            # 获取当前进行中的活动期数
            current_period = self.db.query(Period)\
                .filter(Period.status == '进行中')\
                .first()

            if not current_period:
                error_msg = "活动结束失败：没有正在进行的活动"
                logger.info(error_msg)
                return error_msg

            try:
                # 获取所有报名记录
                signups = self.db.query(Signup)\
                    .filter(Signup.period_id == current_period.id)\
                    .all()

                # 收集每个开发者的打卡统计和成果
                developer_stats = []
                qualified_developers = []  # 达标开发者
                
                for signup in signups:
                    # 获取该开发者的所有打卡记录
                    checkins = self.db.query(Checkin)\
                        .filter(Checkin.signup_id == signup.id)\
                        .order_by(Checkin.checkin_date)\
                        .all()
                    
                    checkin_count = len(checkins)
                    
                    # 检查是否达标（9次有效打卡）
                    is_qualified = checkin_count >= 9
                    
                    # 生成开发者的AI表扬语
                    praise = ""
                    if checkin_count > 0:
                        retry_count = 3  # 最大重试次数
                        while retry_count > 0:
                            try:
                                # 使用最后一次打卡内容生成表扬
                                latest_checkin = checkins[-1]
                                praise = generate_ai_feedback(
                                    db=self.db,
                                    signup_id=signup.id,
                                    nickname=signup.nickname,
                                    goals=signup.goals,
                                    content=latest_checkin.content,
                                    checkin_count=checkin_count,
                                    is_final=True  # 标记这是结束总结
                                )
                                if praise:
                                    praise = praise.split('\n\n')[-1]  # 只取AI反馈部分
                                    break
                            except Exception as e:
                                logger.error(f"生成AI表扬失败 (还剩{retry_count-1}次重试): {str(e)}")
                                retry_count -= 1
                                if retry_count == 0:
                                    praise = "很棒的表现！期待下次再见！"  # 默认表扬语
                            
                    developer_stats.append({
                        'nickname': signup.nickname,
                        'focus_area': signup.focus_area,
                        'checkin_count': checkin_count,
                        'is_qualified': is_qualified,
                        'praise': praise
                    })
                    
                    if is_qualified:
                        qualified_developers.append(signup.nickname)

                # 更新活动状态为已结束
                current_period.status = '已结束'
                self.db.commit()
                logger.info(f"成功更新活动期数 {current_period.period_name} 状态为已结束")

                # 构建响应消息
                response_lines = [
                    f"✨ {current_period.period_name}期活动圆满结束！",
                    "感谢大家的积极参与和付出！\n"
                ]
                
                # 添加开发者统计信息
                response_lines.append("📊 开发者打卡统计：")
                for dev in developer_stats:
                    response_lines.append(f"\n{dev['nickname']} ({dev['focus_area']})：")
                    response_lines.append(f"- 打卡进度：{dev['checkin_count']}/21次")
                    response_lines.append(f"- {dev['praise']}")
                
                # 添加达标情况说明
                response_lines.append("\n🎯 达标情况：")
                response_lines.append("- 达标要求：21天内完成9次有效打卡 + 实现自定目标")
                
                if qualified_developers:
                    response_lines.append("\n🏆 本期达标开发者：")
                    for dev in qualified_developers:
                        response_lines.append(f"- {dev}")
                else:
                    response_lines.append("\n本期暂无达标开发者，继续加油！")
                
                # 添加奖励机制说明
                response_lines.extend([
                    "\n🌟 完成达标有机会获得：",
                    "1. 社区网站展示机会",
                    "2. 公众号专题报道机会",
                    "3. 创新项目Demo日展示机会"
                ])
                
                # 对未达标者的简短鼓励
                if len(qualified_developers) < len(developer_stats):
                    response_lines.extend([
                        "\n💪 未达标的小伙伴也请不要灰心，",
                        "这只是开始，继续坚持，下期一定能达标！"
                    ])
                
                # 更新结束语
                response_lines.extend([
                    "\n🌈 让我们继续努力，",
                    "下期再战，更多惊喜奖励等你来挑战！ 🚀"
                ])
                
                return "\n".join(response_lines)

            except Exception as e:
                error_msg = f"活动结束失败：更新状态时发生错误 - {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.db.rollback()
                return error_msg

        except Exception as e:
            if "EOF occurred in violation of protocol" in str(e):
                # 如果是 SSL 错误，回滚事务并返回错误消息
                self.db.rollback()
                return "服务异常，请重试"
            # 其他错误照常处理
            logger.error(f"处理活动结束时出错: {str(e)}")
            raise e
