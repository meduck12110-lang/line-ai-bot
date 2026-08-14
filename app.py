import os

from flask import Flask, request
from dotenv import load_dotenv

from google import genai
from google.genai import types

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

# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================

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


# =====================================================
# FLASK
# =====================================================

app = Flask(__name__)


# =====================================================
# LINE SETUP
# =====================================================

configuration = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN
)

handler = WebhookHandler(
    LINE_CHANNEL_SECRET
)


# =====================================================
# GEMINI SETUP
# =====================================================

gemini = genai.Client(
    api_key=GEMINI_API_KEY
)

# ใช้ชื่อเดียวกับที่ test_gemini.py ของคุณใช้ได้
GEMINI_MODEL = "gemini-3.6-flash"


# =====================================================
# MRT AI PERSONALITY / SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
คุณคือ "MRT Local Guide"
ผู้ช่วยแนะนำการท่องเที่ยวรอบสถานี MRT ของ รฟม.

หน้าที่หลัก:
ช่วยผู้ใช้ค้นหาและวางแผนการท่องเที่ยว
โดยเน้นสถานี MRT ชุมชน ร้านอาหาร ตลาด คาเฟ่
วัฒนธรรม สถานที่สำคัญ และสถานที่ท่องเที่ยวใกล้สถานี MRT

กฎการตอบ:

1. ตอบเป็นภาษาไทย
2. ใช้น้ำเสียงเป็นมิตร เหมือนผู้ช่วยแนะนำเที่ยว
3. ตอบให้กระชับ อ่านง่าย และเข้าใจง่าย
4. หากผู้ใช้ถามถึงสถานที่ ให้บอกสถานี MRT ที่ใกล้ที่สุด
5. อธิบายวิธีเดินทางจากสถานีไปยังสถานที่
6. เน้นชุมชนและสถานที่ท้องถิ่น
7. ถ้าเหมาะสม ให้แนะนำ 2-4 สถานที่
8. หากผู้ใช้ต้องการเที่ยวหลายจุด ให้จัดเป็นเส้นทาง
9. สามารถจัดทริป 2-3 ชั่วโมง หรือครึ่งวันได้
10. หากข้อมูลเกี่ยวกับเวลาเปิด-ปิด ค่าเข้าชม
    หรือกิจกรรมอาจเปลี่ยนแปลง ให้แจ้งว่าควรตรวจสอบข้อมูลล่าสุด
11. ห้ามสร้างข้อมูลที่ไม่แน่ใจขึ้นมาเอง
12. หากไม่ทราบข้อมูล ให้บอกตรง ๆ
13. หากคำถามไม่เกี่ยวกับการท่องเที่ยว MRT
    ให้ตอบสั้น ๆ และชวนผู้ใช้กลับมาคุยเรื่องการท่องเที่ยว MRT

เมื่อแนะนำสถานที่ สามารถใช้รูปแบบนี้:

📍 สถานที่:
🚇 MRT ใกล้ที่สุด:
🚶 วิธีเดินทาง:
⭐ ไฮไลต์:
💡 เคล็ดลับ:

เป้าหมาย:
ทำให้ผู้ใช้รู้สึกว่า

"MRT ไม่ได้เป็นแค่ทางผ่าน
แต่เป็นประตูสู่ชุมชนและสถานที่น่าสนใจรอบเมือง"
"""


# =====================================================
# SEND REPLY TO LINE
# =====================================================

def send_reply(reply_token, text):

    try:

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

    except Exception as error:

        print("LINE REPLY ERROR:")
        print(repr(error))


# =====================================================
# WEBHOOK
# =====================================================

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

        handler.handle(
            body,
            signature
        )

    except InvalidSignatureError:

        print("INVALID SIGNATURE")

        return "Invalid signature", 400

    except Exception as error:

        print("WEBHOOK ERROR:")
        print(repr(error))

        return "Internal Server Error", 500

    return "OK", 200


# =====================================================
# RECEIVE MESSAGE FROM LINE
# =====================================================

@handler.add(
    MessageEvent,
    message=TextMessageContent
)
def handle_message(event):

    user_message = event.message.text.strip()

    print("USER MESSAGE:")
    print(user_message)

    # =================================================
    # RICH MENU COMMANDS
    # =================================================

    if user_message == "/chat":

        send_reply(
            event.reply_token,
            "🤖 พร้อมคุยแล้วครับ!\nพิมพ์คำถามมาได้เลย"
        )
        return

    if user_message == "/help":

        send_reply(
            event.reply_token,
            "📚 Help\n\nพิมพ์คำถามเพื่อคุยกับ AI ได้เลย"
        )
        return

    if user_message == "/about":

        send_reply(
            event.reply_token,
            "ℹ️ About\n\n"
            "MRT Local Guide\n"
            "สร้างด้วย Python + LINE Messaging API + Gemini"
        )
        return

    if user_message == "/reset":

        send_reply(
            event.reply_token,
            "🔄 เริ่มต้นการสนทนาใหม่แล้วครับ"
        )
        return

    if user_message == "/contact":

        send_reply(
            event.reply_token,
            "📞 ติดต่อผู้ดูแล Bot ได้ที่นี่"
        )
        return


    # =================================================
    # GEMINI AI
    # =================================================

    try:

        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )

        ai_reply = response.text

        if not ai_reply:

            ai_reply = (
                "ขอโทษครับ ตอนนี้ผมยังสร้างคำตอบไม่ได้"
            )

    except Exception as error:

        print("GEMINI ERROR:")
        print(repr(error))

        ai_reply = (
            "ขอโทษครับ 😭\n"
            "ตอนนี้ AI มีปัญหาชั่วคราว ลองใหม่อีกครั้งนะครับ"
        )

    # =================================================
    # SEND AI RESPONSE
    # =================================================

    send_reply(
        event.reply_token,
        ai_reply
    )


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/", methods=["GET"])
def home():

    return "MRT Local Guide Bot is running!", 200


# =====================================================
# START SERVER
# =====================================================

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "5000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )