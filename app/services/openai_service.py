from openai import OpenAI
from dotenv import load_dotenv
import os
import httpx

load_dotenv()

# 创建自定义的 httpx 客户端
http_client = httpx.Client(
    proxies=os.getenv("OPENAI_PROXY"),  # 如果需要代理，从环境变量获取
    timeout=30.0
)

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client
)


def generate_ai_feedback(nickname: str, goals: str, content: str, checkin_count: int) -> str:
    """生成AI反馈"""
    prompt = f"""
    用户 {nickname} 刚刚完成了第 {checkin_count + 1} 次打卡。
    
    他的本期目标是：{goals}
    
    今天的打卡内容是：{content}
    
    请以积极鼓励的语气，生成一段不超过100字的反馈，要：
    1. 肯定他的进步
    2. 关联他的目标
    3. 给出具体的夸奖
    4. 鼓励继续坚持
    
    注意：回复要简短有力，富有激励性。
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个积极向上的导师，善于发现他人的进步和亮点，擅长给出有针对性的鼓励。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"太棒了！{nickname}完成了第{checkin_count + 1}次打卡，继续加油！"
