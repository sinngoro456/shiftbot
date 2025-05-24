import os
import logging
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage  # 追加インポート
from linebot.exceptions import InvalidSignatureError
from main import handle_text
import boto3
import datetime

def get_jst_date():
    """日本時間の日付をYYYYMMDD形式で取得"""
    return datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y%m%d")

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

# LINE Botの設定
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not channel_secret or not channel_access_token:
    logger.error("LINEチャネルのシークレットまたはアクセストークンが設定されていません")
    raise ValueError(
        "LINEチャネルのシークレットまたはアクセストークンが設定されていません"
    )

line_bot_api = LineBotApi(channel_access_token)
webhook_handler = WebhookHandler(channel_secret)
dynamodb = boto3.resource("dynamodb")
shift_table = dynamodb.Table("Request")

def lambda_handler(event, context):
    # 署名検証用のヘッダーとボディを取得
    signature = event["headers"]["x-line-signature"]
    body = event["body"]

    # 成功時のレスポンス
    ok_response = {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "body": "",
    }

    # エラー時のレスポンス
    error_response = {
        "isBase64Encoded": False,
        "statusCode": 500,
        "headers": {},
        "body": "Error",
    }

    @webhook_handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        # 受信したメッセージをそのまま返信
        received_text = event.message.text
        output_text = handle_text(received_text)

        shift_table.put_item(
            Item={
                "user": "dns.google.com",
                "date": 1
            }
        )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=output_text))

    try:
        webhook_handler.handle(body, signature)
    except InvalidSignatureError:
        return error_response
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return error_response

    return ok_response
