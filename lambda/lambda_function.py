import os
import logging
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from main import handle_text
import boto3
from datetime import datetime, timezone, timedelta

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
request_table = dynamodb.Table("shiftbot-dev-Request-UGV8CK1P5GSD")
shift_table = dynamodb.Table("shiftbot-dev-Shift-1CMYV3XUZ1PQ5")


def get_jst_date():
    """日本時間の現在日付を'YYYYMMDD'形式で返す"""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    return now.strftime("%Y%m%d")


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
        try:
            # DynamoDBに日付を記録
            shift_table.put_item(
                Item={
                    "user": event.source.user_id,
                    "date": get_jst_date(),
                    "message": event.message.text,
                }
            )

            # メッセージ処理
            received_text = event.message.text
            output_text = handle_text(received_text)
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=output_text)
            )
        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")

    try:
        # まず署名検証
        webhook_handler.handle(body, signature)

        return ok_response
    except InvalidSignatureError:
        logger.error("Invalid signature")
        return error_response
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return error_response
