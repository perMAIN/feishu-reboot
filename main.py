import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import json
import os
from dotenv import load_dotenv
import logging
from app.services.message_handler import MessageHandler
from app.models.database import init_db, get_db

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 获取配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

if not all([FEISHU_APP_ID, FEISHU_APP_SECRET]):
    raise ValueError(
        "Missing required environment variables: FEISHU_APP_ID or FEISHU_APP_SECRET")

try:
    # 初始化数据库
    init_db()
    logger.info("数据库初始化成功")
except Exception as e:
    logger.error(f"数据库初始化失败: {str(e)}")
    raise

# 注册接收消息事件，处理接收到的消息。
# Register event handler to handle received messages.
# https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive


def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    try:
        # 检查是否已经处理过该消息
        message_id = data.event.message.message_id
        event_id = data.header.event_id
        
        # 使用Redis或内存缓存来存储已处理的消息ID
        processed_events = getattr(do_p2_im_message_receive_v1, 'processed_events', set())
        if event_id in processed_events:
            logger.info(f"事件 {event_id} 已经处理过，跳过")
            return
        
        # 添加到已处理集合
        processed_events.add(event_id)
        setattr(do_p2_im_message_receive_v1, 'processed_events', processed_events)
        
        # 如果集合太大，清理一下
        if len(processed_events) > 1000:
            processed_events.clear()
        
        logger.info("收到新消息")
        res_content = ""
        message_type = data.event.message.message_type
        logger.info(f"消息类型: {message_type}")

        # 使用消息处理器处理消息
        db = next(get_db())
        handler = MessageHandler(db)
        logger.info("开始处理消息...")

        if message_type == "text":
            content_json = json.loads(data.event.message.content)
            res_content = content_json.get("text", "")
            logger.info(f"消息内容: {res_content}")
        else:
            res_content = data.event.message.content
            logger.info(f"消息内容: {res_content}")

        response = handler.handle_message(
            res_content, 
            data.event.message.chat_id, 
            message_type,
            message_id
        )
        logger.info(f"消息处理结果: {response}")

        if response:
            content = json.dumps({"text": response})
            logger.info(f"准备发送回复: {content}")

            if data.event.message.chat_type == "p2p":
                logger.info("私聊消息，使用 create 接口发送")
                request = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(data.event.message.chat_id)
                        .msg_type("text")
                        .content(content)
                        .build()
                    )
                    .build()
                )
                # 使用OpenAPI发送消息
                # Use send OpenAPI to send messages
                # https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
                response = client.im.v1.message.create(request)
            else:
                logger.info("群聊消息，使用 reply 接口发送")
                request = (
                    ReplyMessageRequest.builder()
                    .message_id(message_id)
                    .request_body(
                        ReplyMessageRequestBody.builder()
                        .content(content)
                        .msg_type("text")
                        .build()
                    )
                    .build()
                )
                # 使用OpenAPI回复消息
                # Reply to messages using send OpenAPI
                # https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/reply
                response = client.im.v1.message.reply(request)

            if not response.success():
                logger.error(
                    f"发送消息失败: {response.msg}, log_id: {response.get_log_id()}")
            else:
                logger.info("消息发送成功")
    except Exception as e:
        logger.error(f"消息处理失败: {str(e)}", exc_info=True)


# 注册事件回调
# Register event handler.
event_handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
    .build()
)


# 创建 LarkClient 对象，用于请求OpenAPI, 并创建 LarkWSClient 对象，用于使用长连接接收事件。
# Create LarkClient object for requesting OpenAPI, and create LarkWSClient object for receiving events using long connection.
client = lark.Client.builder().app_id(
    FEISHU_APP_ID).app_secret(FEISHU_APP_SECRET).build()
wsClient = lark.ws.Client(
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    event_handler=event_handler,
    log_level=lark.LogLevel.DEBUG,
)


def main():
    try:
        logger.info("启动飞书机器人服务...")
        #  启动长连接，并注册事件处理器。
        #  Start long connection and register event handler.
        wsClient.start()
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        raise


if __name__ == "__main__":
    main()
