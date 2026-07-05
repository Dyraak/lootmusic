import logging, json, random, os, difflib, threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import firebase_admin
from firebase_admin import credentials, firestore

TOKEN = "8987496039:AAFV4bJjICt6jqJxLAuzmx0g0swdQYhFLUc"
ADMIN_ID = 5391216648

logging.basicConfig(level=logging.INFO)

# Firebase
cred = credentials.Certificate({
  "type": "service_account",
  "project_id": "lootmusic-e6049",
  "private_key_id": "0ef2d12f930b68a5ba25a55f60c715cb8fd8c889",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCqIsMeZPN6PInY\nHwEwg23edBaxfp5jHqzST3Kmeqm+nloCcZ+6i6BOHEYpdsX61VW9+2oXkOoLgZdw\n/JkDC7HUMs9y2oXgyls84CLw6Fc4rRYgs2IXMoWF7eYS57yl0ggB2vLI2aQpFefP\njQpXjJZmQLOzv9kyN4hzfPQ08Oq6U4ZgJ9/8BXEjTBxmzfj74IA0vG2GP32d5Dgn\nfgW6U15igFzfDj3Md0Va71kHh04a1Lx/eCHD7vKaJ50j3FReNCQ03PUJ7kdv4aV8\nHdHtQpnVcgHOexQ+VIHOXES9J7wQBJi77ol2iO4n09nUjopc9gp5VwPB893wVhmi\nIvaKhnj5AgMBAAECggEABNmwmxpY7CJTcjVBEw1eKZ5A4t7HnG8MkYLZE4ix8+if\nC4yKd5ahM3TgJbC4iHQCSaQkJEeZ+om/Y+XZpWH1GAX6Ts2OzUerlfbUXC6dhPS/\nSZ+fk2Z58sVjXqTbZpVQK+BedU4qHU898Hd2hOQxyfi8fsqAgktdwSAd9K/tGzJ4\nPZMVDBlswybUU1DRQ98a9Y5sV3enRvX2wv2Pnjm/OAP7pn4VCA+7dgMndi3HbCtp\ni85sh7KQEPsxr7cxqwXlMfMix8wZ3s+CQ6bcFDye7x0aT74moqM3ZULXb2VDdymE\nQStaBl6c8Nrp4akk2/U+18sBHZDij7MTdXS5N4hfAQKBgQDXXKaCwK6chhZn+rbk\n4TKqa8dih6+xEm55p0cFrOUSvvRAR7q59r+a6ds2Sdl9XY4CVA8ytXystiHiii+o\nlXyyNS1k26hOYkZJGSV4myMrZndo8OGbIuRZt+fVpnG8ak4x6IaM2d8ua08tt6wr\ncdmkZS5RE8XNzvz7YIGwTaxrAQKBgQDKPWcBggtEaOzQitS735LiCwQGrRsCbajs\nhx/P7+wNBSlm8Y374G/qvObsa1UvehMgsnqdRk1ymo/9pgFdH5gW/TD2N297uoFV\nndG60AgUrAykbjWfBYBauAALg1arrtOdaz3CPxhzZ6fnnp6CmPRh9oP/lsRaja0F\nCnA3Lptl+QKBgQCwKXFq8wHhty0M0OBaSHuRO6hUyHjGdzU2/cXytoKK2vggvIvZ\nIiWJKlHODoqBKc3HycrEx/+7pyAAlth1JhJiE22WWrdJpsmncZJdHUmfbqmuhZuF\nsvznBq/067mNTce4u2OUQ4N0DQMvelazEuXcu4cveuUKfI4jccWj2WV4AQKBgFPy\n0QMrPAoVk9etCUlDMPFrqSwsRv3nDyu/m1DxQobVEa6NrmZTb6F88E5K731Zqv7z\nlzoZqKRdzE95zS8eoj9Isj5CHKC7dlxXumtVV0VddZH7vX5ZBkKiBkLBLgTt+SFr\nFqO/FSMyb9wRV7LWUvsnHPvHVZJRJPTmtFXznsXhAoGAETsk58TQlYcfYEmDsxxf\n/qHthbAbJbM/ZJC9zSiHwjJnGGUo6MoDXZuNHrh8oh3DKnDCPk3nxLmp50JxPhuA\n3fMPu323w5y30jiIXIhmGsdeVoBS6ol0h2fJ7iQ6zHAD0o96c+IkyiRAMgB/9nKu\njz2HoyPfffXqtBNUHRuwda8=\n-----END PRIVATE KEY-----\n",
  "client_email": "lootmusic-bot@lootmusic-e6049.iam.gserviceaccount.com",
  "client_id": "106898834451394716825",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/lootmusic-bot%40lootmusic-e6049.iam.gserviceaccount.com"
})
firebase_admin.initialize_app(cred)
db = firestore.client()

# Фейковый веб-сервер для Render
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', 10000), DummyHandler).serve_forever(), daemon=True).start()

def get_users():
    users = {}
    for doc in db.collection("bot_users").stream(): users[doc.id] = doc.to_dict()
    return users

def save_user(uid, data): db.collection("bot_users").document(uid).set(data)

def get_tracks():
    tracks = []
    for doc in db.collection("bot_tracks").stream():
        t = doc.to_dict(); t["id"] = doc.id; tracks.append(t)
    return tracks

def add_track(title, artist, file_id, rarity="common"):
    db.collection("bot_tracks").add({"title":title,"artist":artist,"file_id":file_id,"rarity":rarity})

def remove_track(title):
    for doc in db.collection("bot_tracks").where("title","==",title).stream(): doc.reference.delete()

def get_ratings():
    doc = db.collection("bot_ratings").document("data").get()
    return doc.to_dict() if doc.exists else {}

def save_ratings(data): db.collection("bot_ratings").document("data").set(data)

def get_rarity_weight(rarity, rating_avg=None):
    base = {"common":50,"rare":25,"epic":10,"legendary":3}.get(rarity,50)
    if rating_avg and rating_avg > 0:
        if rating_avg >= 4.5: base = max(3, base-20)
        elif rating_avg >= 3.5: base = max(5, base-10)
        elif rating_avg < 2: base = min(60, base+15)
    return base

def weighted_choice(tracks, ratings):
    weights = []
    for t in tracks:
        avg = None
        if t["title"] in ratings and ratings[t["title"]]: avg = sum(ratings[t["title"]])/len(ratings[t["title"]])
        weights.append(get_rarity_weight(t.get("rarity","common"), avg))
    r = random.uniform(0, sum(weights))
    acc = 0
    for i,w in enumerate(weights):
        acc += w
        if r <= acc: return tracks[i]
    return tracks[-1]

async def start(update: Update, context):
    uid = str(update.effective_user.id)
    users = get_users()
    if uid not in users:
        users[uid] = {"nick":update.effective_user.first_name or "Игрок","username":update.effective_user.username or "","collection":[],"last_open":None,"created_at":datetime.now().isoformat(),"banned":False}
        save_user(uid, users[uid])
    u = users[uid]
    if u.get("banned"): await update.message.reply_text("🚫"); return
    msg = "🎵 LootMusic Bot\nОткрывай кейсы, собирай треки, оценивай!\nПоддержка: @dyraak0"
    if u.get("last_open"):
        if datetime.now() - datetime.fromisoformat(u["last_open"]) >= timedelta(hours=2): msg = "🔔 Твой кейс готов!\n\n" + msg
    kb = [[InlineKeyboardButton("🎁 Открыть кейс",callback_data="open")],
          [InlineKeyboardButton("📦 Коллекция",callback_data="col")],
          [InlineKeyboardButton("👤 Профиль",callback_data="profile")],
          [InlineKeyboardButton("🔍 Найти трек",callback_data="shazam_info")]]
    await update.message.reply_text(msg,reply_markup=InlineKeyboardMarkup(kb))

async def button(update: Update, context):
    q = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    users = get_users(); ratings = get_ratings(); tracks = get_tracks()
    if uid not in users:
        users[uid] = {"nick":q.from_user.first_name,"username":q.from_user.username or "","collection":[],"last_open":None,"created_at":datetime.now().isoformat(),"banned":False}
        save_user(uid, users[uid])
    u = users[uid]
    if u.get("banned"): await q.message.reply_text("🚫"); return

    if q.data == "open":
        if u.get("last_open") and datetime.now() - datetime.fromisoformat(u["last_open"]) < timedelta(hours=2):
            left = timedelta(hours=2) - (datetime.now() - datetime.fromisoformat(u["last_open"]))
            h,m = left.seconds//3600, (left.seconds%3600)//60
            await q.message.reply_text(f"⏳ {h}ч {m}м"); return
        if not tracks: await q.message.reply_text("Нет треков."); return
        collected = [t["title"] for t in u["collection"]]
        available = [t for t in tracks if t["title"] not in collected]
        if not available: await q.message.reply_text("🎉 Всё собрано!"); return
        track = weighted_choice(available, ratings).copy()
        track["obtained_at"] = datetime.now().isoformat(); track["rated"] = False
        u["last_open"] = datetime.now().isoformat(); u["collection"].append(track)
        save_user(uid, u)
        idx = len(u["collection"])-1
        kb = [[InlineKeyboardButton(f"⭐ {i}",callback_data=f"rate_{i}_{idx}")] for i in range(1,6)]
        await q.message.reply_text(f"🎁 {track['title']} — {track['artist']}\nОцени:",reply_markup=InlineKeyboardMarkup(kb))
        if track.get("file_id"): await context.bot.send_audio(chat_id=uid,audio=track["file_id"],title=track["title"],performer=track["artist"])

    elif q.data.startswith("rate_"):
        _,r,idx = q.data.split("_"); r,idx = int(r),int(idx)
        if idx < len(u["collection"]) and not u["collection"][idx].get("rated"):
            u["collection"][idx]["rated"] = True; u["collection"][idx]["rating"] = r
            save_user(uid, u)
            t = u["collection"][idx]["title"]
            rats = ratings.get(t, []); rats.append(r); ratings[t] = rats; save_ratings(ratings)
            await q.message.reply_text(f"⭐ {r}/5 | Средняя: {sum(rats)/len(rats):.1f} ({len(rats)})")
        else: await q.message.reply_text("Уже оценено!")

    elif q.data == "col":
        if not u.get("collection"): await q.message.reply_text("📦 Пусто.")
        else:
            kb = []
            for i,t in enumerate(u["collection"]):
                r = f"⭐{t.get('rating','?')}" if t.get("rated") else "—"
                kb.append([InlineKeyboardButton(f"{i+1}. {t['title']} — {t['artist']} {r}",callback_data=f"listen_{i}")])
            kb.append([InlineKeyboardButton("🎁 Подарить",callback_data="gift_menu"),InlineKeyboardButton("🔄 Обмен",callback_data="trade_menu")])
            kb.append([InlineKeyboardButton("« Назад",callback_data="main_menu")])
            await q.message.reply_text("📦",reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("listen_"):
        idx = int(q.data.split("_")[1])
        if idx < len(u["collection"]) and u["collection"][idx].get("file_id"):
            t = u["collection"][idx]
            await context.bot.send_audio(chat_id=uid,audio=t["file_id"],title=t["title"],performer=t["artist"])

    elif q.data == "gift_menu":
        if not u.get("collection"): await q.message.reply_text("Нечего дарить.")
        else:
            kb = [[InlineKeyboardButton(f"{t['title']} — {t['artist']}",callback_data=f"gift_{i}")] for i,t in enumerate(u["collection"])]
            kb.append([InlineKeyboardButton("«",callback_data="col")])
            await q.message.reply_text("Выбери:",reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("gift_"):
        context.user_data["gift_idx"] = int(q.data.split("_")[1])
        await q.message.reply_text("Введи @username:")

    elif q.data == "trade_menu":
        if not u.get("collection"): await q.message.reply_text("Нечего менять.")
        else:
            kb = [[InlineKeyboardButton(f"{t['title']} — {t['artist']}",callback_data=f"trade_my_{i}")] for i,t in enumerate(u["collection"])]
            kb.append([InlineKeyboardButton("«",callback_data="col")])
            await q.message.reply_text("Выбери свой трек:",reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("trade_my_"):
        context.user_data["trade_my_idx"] = int(q.data.split("_")[2])
        await q.message.reply_text("Введи @username:")

    elif q.data == "profile":
        rd = u.get("created_at","?")
        if rd!="?": rd = datetime.fromisoformat(rd).strftime("%d.%m.%Y")
        await q.message.reply_text(f"👤 {u['nick']}\n🆔 {uid}\n📅 {rd}\n🎵 {len(u['collection'])} треков")

    elif q.data == "shazam_info": await q.message.reply_text("🔍 Отправь аудио или название.")

    elif q.data == "main_menu":
        kb = [[InlineKeyboardButton("🎁 Открыть кейс",callback_data="open")],
              [InlineKeyboardButton("📦 Коллекция",callback_data="col")],
              [InlineKeyboardButton("👤 Профиль",callback_data="profile")],
              [InlineKeyboardButton("🔍 Найти трек",callback_data="shazam_info")]]
        await q.message.reply_text("🎵",reply_markup=InlineKeyboardMarkup(kb))

async def handle_text(update: Update, context):
    uid = str(update.effective_user.id)
    text = update.message.text.strip()
    users = get_users(); ratings = get_ratings(); tracks = get_tracks()

    if update.effective_user.id == ADMIN_ID:
        if text == "/test":
            if not tracks: await update.message.reply_text("Нет.")
            else:
                track = weighted_choice(tracks, ratings)
                await update.message.reply_text(f"🧪 {track['title']} — {track['artist']} ({track.get('rarity','common')})")
                if track.get("file_id"): await context.bot.send_audio(chat_id=uid,audio=track["file_id"],title=track["title"],performer=track["artist"])
            return
        if "pending_file_id" in context.user_data:
            if " — " in text: title, artist = text.split(" — ",1)
            elif "-" in text: title, artist = text.split("-",1)
            else: title, artist = text, "Неизвестен"
            context.user_data["new_title"] = title.strip(); context.user_data["new_artist"] = artist.strip()
            kb = [[InlineKeyboardButton(r.capitalize(),callback_data=f"addrar_{r}")] for r in ["common","rare","epic","legendary"]]
            await update.message.reply_text(f"🎵 {title.strip()} — {artist.strip()}\nРедкость:",reply_markup=InlineKeyboardMarkup(kb))
            return
        if text.startswith("/broadcast "):
            for u in users:
                try: await context.bot.send_message(chat_id=u,text=f"📢 {text[11:]}")
                except: pass
            await update.message.reply_text("✅"); return
        if text == "/stats": await update.message.reply_text(f"👥 {len(users)}\n🎵 {len(tracks)}\n⭐ {sum(len(v) for v in ratings.values())}"); return
        if text.startswith("/delete "): remove_track(text[8:]); await update.message.reply_text("🗑"); return
        if text.startswith("/ban "):
            t = text[5:].replace("@","")
            for i,u in users.items():
                if u.get("username","")==t or u.get("nick","")==t: u["banned"]=True; save_user(i,u); await update.message.reply_text(f"🚫 {t}"); return
            await update.message.reply_text("Не найден."); return
        if text.startswith("/unban "):
            t = text[7:].replace("@","")
            for i,u in users.items():
                if u.get("username","")==t or u.get("nick","")==t: u["banned"]=False; save_user(i,u); await update.message.reply_text(f"✅ {t}"); return
            await update.message.reply_text("Не найден."); return

    if "gift_idx" in context.user_data:
        target = text.replace("@","").strip(); tid = None
        for i,u in users.items():
            if u.get("username","")==target: tid=i; break
        if not tid: await update.message.reply_text("❌"); del context.user_data["gift_idx"]; return
        idx = context.user_data["gift_idx"]; track = users[uid]["collection"][idx]
        if track["title"] in [t["title"] for t in users[tid]["collection"]]: await update.message.reply_text("❌ Уже есть."); del context.user_data["gift_idx"]; return
        users[tid]["collection"].append(track); users[uid]["collection"].pop(idx)
        save_user(uid,users[uid]); save_user(tid,users[tid])
        await update.message.reply_text(f"🎁 '{track['title']}' → @{target}!")
        try: await context.bot.send_message(chat_id=tid,text=f"🎁 @{users[uid].get('username',uid)}: {track['title']} — {track['artist']}")
        except: pass
        del context.user_data["gift_idx"]; return

    if "trade_my_idx" in context.user_data:
        target = text.replace("@","").strip(); tid = None
        for i,u in users.items():
            if u.get("username","")==target: tid=i; break
        if not tid: await update.message.reply_text("❌"); del context.user_data["trade_my_idx"]; return
        my_idx = context.user_data["trade_my_idx"]; my_track = users[uid]["collection"][my_idx]
        if my_track["title"] in [t["title"] for t in users[tid]["collection"]]: await update.message.reply_text("❌ Уже есть."); del context.user_data["trade_my_idx"]; return
        context.user_data["trade_target"]=tid; context.user_data["trade_my_track"]=my_idx
        tc = users[tid]["collection"]
        if not tc: await update.message.reply_text("Пусто."); del context.user_data["trade_my_idx"]; return
        txt = f"🎵 @{target}:\n"
        for i,t in enumerate(tc,1): txt+=f"{i}. {t['title']} — {t['artist']}\n"
        await update.message.reply_text(txt[:4000]+"\nВведи номер или название:"); return

    if "trade_target" in context.user_data:
        tid = context.user_data["trade_target"]; tc = users[tid]["collection"]
        ch = text.strip(); their_idx = None
        if ch.isdigit():
            i=int(ch)-1
            if 0<=i<len(tc): their_idx=i
        else:
            for i,t in enumerate(tc):
                if t["title"].lower()==ch.lower(): their_idx=i; break
        if their_idx is None: await update.message.reply_text("❌"); return
        their_track = tc[their_idx]
        if their_track["title"] in [t["title"] for t in users[uid]["collection"]]: await update.message.reply_text("❌ Уже есть."); return
        my_idx = context.user_data["trade_my_track"]; my_track = users[uid]["collection"][my_idx]
        kb = [[InlineKeyboardButton("✅",callback_data=f"trade_acc_{uid}_{my_idx}_{tid}_{their_idx}"),InlineKeyboardButton("❌",callback_data=f"trade_dec_{tid}_{uid}")]]
        await context.bot.send_message(chat_id=tid,text=f"🔄 {users[uid]['username']or uid}: {my_track['title']} ↔ {their_track['title']}",reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ Запрос отправлен!")
        for k in ["trade_my_idx","trade_target","trade_my_track"]:
            if k in context.user_data: del context.user_data[k]; return

    if "awaiting_request" in context.user_data:
        await context.bot.send_message(chat_id=ADMIN_ID,text=f"📩 @{users[uid].get('username',uid)} хочет добавить:\n{text}")
        del context.user_data["awaiting_request"]; await update.message.reply_text("✅"); return

    query = text.lower().strip()
    matches = difflib.get_close_matches(query,[t["title"].lower() for t in tracks],n=3,cutoff=0.4)
    if matches:
        txt = "🔍 Найдено:\n"
        for m in matches:
            for t in tracks:
                if t["title"].lower()==m:
                    avg=""
                    if t["title"] in ratings and ratings[t["title"]]: avg=f" — ⭐{sum(ratings[t['title']])/len(ratings[t['title']]):.1f}"
                    txt+=f"• {t['title']} — {t['artist']}{avg}\n"
        await update.message.reply_text(txt[:4000])
    else:
        await update.message.reply_text("❌ Не найдено. Отправить запрос?",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 Отправить",callback_data="req_admin")]]))

async def handle_audio(update: Update, context):
    uid = update.effective_user.id; tracks = get_tracks(); ratings = get_ratings()
    audio = update.message.audio or update.message.voice
    if not audio: return
    if uid == ADMIN_ID:
        context.user_data["pending_file_id"] = audio.file_id
        await update.message.reply_text("🎵 Введи название и исполнителя:\n`Название — Исполнитель`", parse_mode="Markdown")
        return
    title = (audio.file_name or "").lower().strip()
    matches = difflib.get_close_matches(title,[t["title"].lower() for t in tracks],n=3,cutoff=0.4)
    if matches:
        txt="🔍 Найдено:\n"
        for m in matches:
            for t in tracks:
                if t["title"].lower()==m:
                    avg=""
                    if t["title"] in ratings and ratings[t["title"]]: avg=f" — ⭐{sum(ratings[t['title']])/len(ratings[t['title']]):.1f}"
                    txt+=f"• {t['title']} — {t['artist']}{avg}\n"
        await update.message.reply_text(txt[:4000])
    else:
        await update.message.reply_text("❌ Не найдено. Отправить запрос?",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 Отправить",callback_data="req_admin")]]))

async def button_admin(update: Update, context):
    q=update.callback_query; await q.answer()
    if q.data.startswith("addrar_"):
        r=q.data.split("_")[1]
        if "pending_file_id" in context.user_data and "new_title" in context.user_data:
            add_track(context.user_data["new_title"],context.user_data.get("new_artist","Неизвестен"),context.user_data["pending_file_id"],r)
            await q.message.reply_text(f"✅ {context.user_data['new_title']} ({r})")
            for k in ["pending_file_id","new_title","new_artist"]:
                if k in context.user_data: del context.user_data[k]; return
    if q.data.startswith("trade_acc_"):
        _,_,fu,mi,tu,ti=q.data.split("_"); mi,ti=int(mi),int(ti); users=get_users()
        mt=users[fu]["collection"].pop(mi); tt=users[tu]["collection"].pop(ti)
        users[fu]["collection"].append(tt); users[tu]["collection"].append(mt)
        save_user(fu,users[fu]); save_user(tu,users[tu])
        await q.message.reply_text("✅"); await context.bot.send_message(chat_id=fu,text=f"✅ {mt['title']} ↔ {tt['title']}"); return
    if q.data.startswith("trade_dec_"):
        _,_,fu,tu=q.data.split("_"); await context.bot.send_message(chat_id=fu,text="❌ Отклонён."); await q.message.reply_text("Отклонён."); return
    if q.data=="req_admin":
        context.user_data["awaiting_request"] = True
        await q.message.reply_text("📝 Какую песню хотите видеть в боте? Напиши название и исполнителя:"); return

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(button,pattern="^(?!addrar_|trade_acc_|trade_dec_|req_admin).*"))
    app.add_handler(CallbackQueryHandler(button_admin,pattern="^(addrar_|trade_acc_|trade_dec_|req_admin)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_text))
    app.add_handler(MessageHandler(filters.AUDIO,handle_audio))
    print("Бот запущен!")
    app.run_polling()

if __name__=="__main__":
    main()
