import os

from flask import Flask, request
from dotenv import load_dotenv
from google import genai

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

# =========================
# Load environment variables
# =========================

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


# =========================
# Flask
# =========================

app = Flask(__name__)


# =========================
# LINE
# =========================

configuration = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN
)

handler = WebhookHandler(
    LINE_CHANNEL_SECRET
)


# =========================
# Gemini
# =========================

gemini = genai.Client(
    api_key=GEMINI_API_KEY
)

# IMPORTANT:
# Put the SAME model name that worked in test_gemini.py
GEMINI_MODEL = "gemini-3.6-flash"


# =========================
# Send reply to LINE
# =========================

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


# =========================
# LINE Webhook
# =========================

@app.route("/callback", methods=["POST"])
def callback():

    signature = request.headers.get("X-Line-Signature")

    if not signature:
        return "Missing signature", 400

    body = request.get_data(as_text=True)

    print("========== LINE EVENT ==========")
    print(body)
    print("================================")

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        print("Invalid LINE signature")
        return "Invalid signature", 400

    except Exception as error:
        print("Webhook error:", repr(error))
        return "Internal Server Error", 500

    return "OK", 200


# =========================
# Receive text messages
# =========================

@handler.add(
    MessageEvent,
    message=TextMessageContent
)
def handle_message(event):

    user_message = event.message.text.strip()

    print("USER MESSAGE:", user_message)

    # -------------------------
    # Rich Menu: Chat
    # -------------------------

    if user_message == "/chat":

        reply = (
            "🤖 Chat\n\n"
            "พร้อมคุยแล้วครับ!\n"
            "พิมพ์คำถามมาได้เลย"
        )

        send_reply(event.reply_token, reply)
        return

    # -------------------------
    # Rich Menu: Help
    # -------------------------

    if user_message == "/help":

        reply = (
            "📚 Help\n\n"
            "พิมพ์คำถามเพื่อคุยกับ AI ได้เลย\n"
            "หรือใช้ Rich Menu ด้านล่าง"
        )

        send_reply(event.reply_token, reply)
        return

    # -------------------------
    # Rich Menu: About
    # -------------------------

    if user_message == "/about":

        reply = (
            "ℹ️ About\n\n"
            "LINE AI Chatbot\n\n"
            "สร้างด้วย Python + LINE Messaging API + Gemini"
        )

        send_reply(event.reply_token, reply)
        return

    # -------------------------
    # Rich Menu: Reset
    # -------------------------

    if user_message == "/reset":

        reply = (
            "🔄 Reset\n\n"
            "เริ่มการสนทนาใหม่แล้วครับ"
        )

        send_reply(event.reply_token, reply)
        return

    # -------------------------
    # Rich Menu: Contact
    # -------------------------

    if user_message == "/contact":

        reply = (
            "📞 Contact\n\n"
            "ติดต่อผู้ดูแล Bot ได้ที่นี่"
        )

        send_reply(event.reply_token, reply)
        return

    # =========================
    # Normal Gemini Chat
    # =========================

    try:

        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message
        )

        ai_reply = response.text

        if not ai_reply:
            ai_reply = "ขอโทษครับ ตอนนี้ยังตอบไม่ได้"

    except Exception as error:

        print("Gemini error:", repr(error))

        ai_reply = (
            "ขอโทษครับ 😭\n"
            "ตอนนี้ AI มีปัญหาชั่วคราว ลองใหม่อีกครั้งครับ"
        )

    send_reply(
        event.reply_token,
        ai_reply
    )


# =========================
# Home page
# =========================

@app.route("/", methods=["GET"])
def home():

    return "LINE AI Bot is running!", 200


if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "5000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )