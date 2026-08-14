import os

from flask import Flask, request
from dotenv import load_dotenv

from google import genai

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is missing")

if not LINE_CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_SECRET is missing")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing")


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


# =========================================================
# LINE
# =========================================================

configuration = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN
)

handler = WebhookHandler(
    LINE_CHANNEL_SECRET
)


# =========================================================
# GEMINI
# =========================================================

gemini = genai.Client(
    api_key=GEMINI_API_KEY
)

# IMPORTANT:
# Put the SAME model name that worked in test_gemini.py here.
GEMINI_MODEL = "gemini-3.6-flash"


# =========================================================
# SEND REPLY TO LINE
# =========================================================

def send_reply(reply_token, text):

    with ApiClient(configuration) as api_client:

        messaging_api = MessagingApi(api_client)

        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    TextMessage(text=text)
                ]
            )
        )


# =========================================================
# WEBHOOK
# =========================================================

@app.route("/callback", methods=["POST"])
def callback():

    signature = request.headers.get("X-Line-Signature")

    if not signature:
        return "Missing signature", 400

    body = request.get_data(as_text=True)

    print("\n========== LINE EVENT ==========")
    print(body)
    print("================================\n")

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        print("INVALID SIGNATURE")
        return "Invalid signature", 400

    except Exception as error:
        print("WEBHOOK ERROR:", repr(error))
        return "Internal Server Error", 500

    return "OK", 200


# =========================================================
# TEXT MESSAGE
# =========================================================

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):

    text = event.message.text.strip()

    print("TEXT MESSAGE:", text)

    # -----------------------------------------------------
    # CHAT
    # -----------------------------------------------------

    if text == "/chat":

        reply = (
            "🤖 Chat\n\n"
            "พร้อมคุยแล้วครับ!\n"
            "พิมพ์คำถามมาได้เลย"
        )

        send_reply(event.reply_token, reply)
        return

    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    if text == "/help":

        reply = (
            "📚 Help\n\n"
            "พิมพ์ข้อความเพื่อคุยกับ AI ได้เลย\n"
            "หรือใช้ Rich Menu ด้านล่าง"
        )

        send_reply(event.reply_token, reply)
        return

    # -----------------------------------------------------
    # ABOUT
    # -----------------------------------------------------

    if text == "/about":

        reply = (
            "ℹ️ About\n\n"
            "LINE AI Chatbot\n"
            "Built with Python + LINE Messaging API + Gemini"
        )

        send_reply(event.reply_token, reply)
        return

    # -----------------------------------------------------
    # RESET
    # -----------------------------------------------------

    if text == "/reset":

        reply = (
            "🔄 Reset\n\n"
            "เริ่มการสนทนาใหม่แล้วครับ"
        )

        send_reply(event.reply_token, reply)
        return

    # -----------------------------------------------------
    # CONTACT
    # -----------------------------------------------------

    if text == "/contact":

        reply = (
            "📞 Contact\n\n"
            "ติดต่อผู้ดูแล Bot ได้ที่นี่"
        )

        send_reply(event.reply_token, reply)
        return

    # =====================================================
    # NORMAL GEMINI CHAT
    # =====================================================

    try:

        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=text
        )

        answer = response.text

        if not answer:
            answer = "ขอโทษครับ ตอนนี้ผมยังตอบไม่ได้"

    except Exception as error:

        print("GEMINI ERROR:", repr(error))

        answer = (
            "ขอโทษครับ 😭\n"
            "AI มีปัญหาชั่วคราว ลองใหม่อีกครั้งนะครับ"
        )

    send_reply(
        event.reply_token,
        answer
    )


# =========================================================
# POSTBACK FROM RICH MENU
# =========================================================

@handler.add(PostbackEvent)
def handle_postback(event):

    data = event.postback.data.strip()

    print("POSTBACK DATA:", data)

    # -----------------------------------------------------
    # CHAT
    # -----------------------------------------------------

    if data == "chat":

        reply = (
            "🤖 Chat\n\n"
            "พร้อมคุยแล้วครับ!\n"
            "พิมพ์คำถามมาได้เลย"
        )
        
    elif data == "help":

        reply = (
            "📚 Help\n\n"
            "พิมพ์ข้อความเพื่อคุยกับ AI ได้เลย\n"
            "หรือเลือกเมนูด้านล่าง"
        )

    elif data == "about":

        reply = (
            "ℹ️ About\n\n"
            "LINE AI Chatbot\n"
            "Built with Python + LINE Messaging API + Gemini"
        )


    elif data == "reset":

        reply = (
            "🔄 Reset\n\n"
            "เริ่มต้นใหม่แล้วครับ"
        )

    elif data == "contact":

        reply = (
            "📞 Contact\n\n"
            "ติดต่อผู้ดูแล Bot ได้ที่นี่"
        )


    else:

        reply = (
            "ไม่พบคำสั่งนี้ครับ\n"
            f"Data: {data}"
        )

    send_reply(
        event.reply_token,
        reply
    )


@app.route("/", methods=["GET"])
def home():

    return "LINE AI Bot is running!", 200


if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )