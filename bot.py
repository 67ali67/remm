import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from pydub import AudioSegment
from subprocess import Popen, PIPE

TOKEN = "8005567836:AAG6rp6_pbWMh3u_whfdJt4CIuTtWhCLTqk"
DATA_FOLDER = "data"
REMINDER_FILE = "reminders.json"
os.makedirs(DATA_FOLDER, exist_ok=True)

if os.path.exists(REMINDER_FILE):
    with open(REMINDER_FILE, "r", encoding="utf-8") as f:
        reminders = json.load(f)
else:
    reminders = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! ویس بفرست تا برات متنش رو استخراج کنم و یادآوری کنم.")

def voice_to_text(ogg_path):
    wav_path = ogg_path.replace(".ogg", ".wav")
    AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")
    process = Popen(["./whisper-cli", "--model", "for-tests-ggml-base.bin", wav_path], stdout=PIPE, stderr=PIPE)
    out, err = process.communicate()
    text = out.decode("utf-8").strip()
    return text

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = os.path.join(DATA_FOLDER, f"{voice.file_id}.ogg")
    await file.download_to_drive(ogg_path)
    text = voice_to_text(ogg_path)
    remind_time = (datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    reminders[voice.file_id] = {"text": text, "chat_id": update.message.chat_id, "time": remind_time}
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)
    await update.message.reply_text(f"متنت استخراج شد:\n{text}\nیادآوری تنظیم شد: {remind_time}")

async def check_reminders(app):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    to_remove = []
    for k, v in reminders.items():
        if v["time"] <= now:
            try:
                await app.bot.send_message(chat_id=v["chat_id"], text=f"⏰ یادآوری:\n{v['text']}")
            except:
                pass
            to_remove.append(k)
    for k in to_remove:
        reminders.pop(k)
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

async def scheduler(app):
    while True:
        await check_reminders(app)
        await asyncio.sleep(10)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.VOICE, voice_handler))

async def main():
    asyncio.create_task(scheduler(app))
    await app.run_polling()

asyncio.run(main())
