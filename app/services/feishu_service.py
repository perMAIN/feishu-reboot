import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class FeishuService:
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        if not self.app_id or not self.app_secret:
            raise ValueError(
                "未找到飞书配置信息，请检查环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        self.access_token = None

    def get_access_token(self) -> str:
        """获取飞书访问令牌"""
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {
                "Content-Type": "application/json"
            }
            data = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                self.access_token = result.get("tenant_access_token")
                return self.access_token
            else:
                raise Exception(f"获取访问令牌失败: {result.get('msg')}")
        except Exception as e:
            logger.error(f"获取访问令牌时发生错误: {str(e)}")
            raise

    def extract_base_info(self, url: str) -> tuple:
        """从URL中提取多维表的base_id和table_id"""
        try:
            logger.info(f"开始解析URL: {url}")
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            query_params = parse_qs(parsed_url.query)

            # 查找base_id（从路径中查找最后一个非空部分）
            base_id = None
            for part in reversed(path_parts):
                if part and len(part) > 20:  # base_id 通常较长
                    base_id = part
                    break

            if not base_id:
                raise ValueError("未在URL中找到base_id")

            # 从查询参数中获取table_id
            table_id = query_params.get('table', [None])[0]
            if not table_id:
                # 如果URL中没有table参数，尝试从路径中查找
                for part in path_parts:
                    if part.startswith('tbl'):
                        table_id = part
                        break
                
                # 如果仍然没有找到，使用默认值
                if not table_id:
                    table_id = 'tblzscrkKqRba5r6'  # 使用默认的table_id
            
            logger.info(f"从URL中提取到 base_id: {base_id}, table_id: {table_id}")
            logger.info(f"URL解析结果 - 路径部分: {path_parts}")
            logger.info(f"URL解析结果 - 查询参数: {query_params}")

            return base_id, table_id
        except Exception as e:
            logger.error(f"解析URL时发生错误: {str(e)}")
            logger.error(f"URL: {url}")
            logger.error(f"解析后的URL对象: {parsed_url}")
            raise

    def fetch_signup_data(self, signup_link: str) -> List[Dict[str, Any]]:
        """获取接龙数据"""
        try:
            logger.info(f"开始获取接龙数据，链接: {signup_link}")

            if not self.access_token:
                logger.info("获取新的访问令牌")
                self.get_access_token()

            logger.info(f"使用访问令牌: {self.access_token[:10]}...")

            base_id, _ = self.extract_base_info(signup_link)
            logger.info(f"提取到的 base_id: {base_id}")

            # 首先获取多维表的表格列表
            list_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"获取表格列表，URL: {list_url}")
            list_response = requests.get(list_url, headers=headers)
            list_result = list_response.json()
            
            if list_result.get("code") != 0:
                error_msg = f"获取表格列表失败: {list_result.get('msg')} (错误码: {list_result.get('code')})"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            tables = list_result.get("data", {}).get("items", [])
            if not tables:
                error_msg = "未找到任何表格"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 使用第一个表格的ID
            table_id = tables[0].get("table_id")
            logger.info(f"使用第一个表格的ID: {table_id}")

            # 构建API URL
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/records"
            params = {"page_size": 100}

            logger.info(f"准备请求URL: {url}")
            logger.info(f"请求参数: {params}")

            try:
                response = requests.get(url, headers=headers, params=params)
                logger.info(f"API响应状态码: {response.status_code}")
                response_text = response.text
                logger.info(f"API响应内容: {response_text[:500]}...")

                if not response.ok:
                    logger.error(f"API请求失败: 状态码 {response.status_code}")
                    logger.error(f"错误响应: {response_text}")
                    if response.status_code in [401, 403]:
                        logger.info("检测到认证错误，尝试重新获取访问令牌")
                        self.access_token = None
                        self.get_access_token()
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        response = requests.get(url, headers=headers, params=params)
                        logger.info(f"重试请求状态码: {response.status_code}")
                        response_text = response.text

                result = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"发送请求时发生错误: {str(e)}")
                raise
            except ValueError as e:
                logger.error(f"解析JSON响应时发生错误: {str(e)}")
                logger.error(f"原始响应内容: {response_text}")
                raise

            if result.get("code") == 0:
                records = result.get("data", {}).get("items", [])
                logger.info(f"获取到 {len(records)} 条记录")

                signup_data = []
                
                for record in records:
                    fields = record.get("fields", {})
                    signup_info = fields.get("接龙信息", "").strip()
                    logger.info(f"处理接龙信息: {signup_info}")

                    if not signup_info:
                        continue

                    # 将接龙信息按行分割
                    lines = signup_info.split("\n")
                    if not lines:
                        continue

                    current_signup = None
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        if "-" in line:  # 这是昵称行
                            # 如果有之前的报名记录，保存它
                            if current_signup and current_signup["nickname"]:
                                signup_data.append(current_signup)
                                current_signup = None

                            # 解析昵称和专注领域
                            parts = line.split("-")
                            if len(parts) >= 3:
                                nickname = parts[0].strip()
                                # 专注领域在最后一部分
                                focus_area = parts[-1].strip()
                                if nickname:
                                    current_signup = {
                                        "nickname": nickname,
                                        "focus_area": focus_area,
                                        "introduction": "",
                                        "goals": "",
                                        "signup_time": datetime.now()
                                    }
                                    logger.info(f"创建新的报名记录 - 昵称: {nickname}, 专注领域: {focus_area}")
                            else:
                                logger.warning(f"昵称格式不正确: {line}")
                                nickname = line
                                focus_area = "未知"
                                if nickname:
                                    current_signup = {
                                        "nickname": nickname,
                                        "focus_area": focus_area,
                                        "introduction": "",
                                        "goals": "",
                                        "signup_time": datetime.now()
                                    }
                                    logger.info(f"创建新的报名记录（格式不正确） - 昵称: {nickname}, 专注领域: {focus_area}")
                        elif current_signup:
                            # 处理自我介绍和目标
                            if "自我介绍：" in line:
                                current_signup["introduction"] = line.split("自我介绍：")[1].strip()
                                logger.info(f"添加自我介绍 - 昵称: {current_signup['nickname']}")
                            elif "本期目标：" in line:
                                current_signup["goals"] = line.split("本期目标：")[1].strip()
                                logger.info(f"添加目标 - 昵称: {current_signup['nickname']}")

                    # 添加最后一个报名记录
                    if current_signup and current_signup["nickname"]:
                        signup_data.append(current_signup)
                        logger.info(f"添加最后一条报名记录 - 昵称: {current_signup['nickname']}, 专注领域: {current_signup['focus_area']}")

                logger.info("=== 数据处理结果 ===")
                for idx, data in enumerate(signup_data, 1):
                    logger.info(f"处理后的记录 {idx}:")
                    logger.info(f"昵称: {data['nickname']}")
                    logger.info(f"专注领域: {data['focus_area']}")
                    logger.info(f"简介: {data['introduction']}")
                    logger.info(f"目标: {data['goals']}")
                    logger.info("---")

                logger.info(f"成功处理 {len(signup_data)} 条报名数据")
                return signup_data
            else:
                error_msg = f"获取数据失败: {result.get('msg')} (错误码: {result.get('code')})"
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f"获取接龙数据时发生错误: {str(e)}", exc_info=True)
            raise
