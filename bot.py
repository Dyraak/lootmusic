import logging, json, random, os, difflib
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8987496039:AAFV4bJjICt6jqJxLAuzmx0g0swdQYhFLUc"
ADMIN_ID = 5391216648
DATA_FILE = "lootmusic_data.json"
RATINGS_FILE = "lootmusic_ratings.json"
TRACKS_FILE = "lootmusic_tracks.json"
MUSIC_DIR = "music"

os.makedirs(MUSIC_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)

def load(f): return json.load(open(f)) if os.path.exists(f) else {}
def save(f,d): json.dump(d,open(f,"w"),indent=2)
def get_users(): return load(DATA_FILE)
def get_ratings(): return load(RATINGS_FILE)
def get_tracks(): return json.load(open(TRACKS_FILE)) if os.path.exists(TRACKS_FILE) else []

def add_track(title, artist, file_path, rarity="common"):
    tracks = get_tracks()
    tracks.append({"title":title,"artist":artist,"file":file_path,"rarity":rarity})
    save(TRACKS_FILE,tracks)

def remove_track(title):
    tracks = [t for t in get_tracks() if t["title"].lower() != title.lower()]
    save(TRACKS_FILE,tracks)

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
        if t["title"] in ratings and ratings[t["title"]]:
            avg = sum(ratings[t["title"]])/len(ratings[t["title"]])
        w = get_rarity_weight(t.get("rarity","common"), avg)
        weights.append(w)
    total = sum(weights)
    r = random.uniform(0, total)
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
        save(DATA_FILE,users)
    u = users[uid]
    if u.get("banned"):
        await update.message.reply_text("🚫 Вы забанены.")
        return
    kb = [[InlineKeyboardButton("🎁 Открыть кейс",callback_data="open")],
          [InlineKeyboardButton("📦 Коллекция",callback_data="col")],
          [InlineKeyboardButton("👤 Профиль",callback_data="profile")],
          [InlineKeyboardButton("🔍 Найти трек",callback_data="shazam_info")]]
    await update.message.reply_text("🎵 LootMusic Bot\nОткрывай кейсы, собирай треки, оценивай!\nПоддержка: @dyraak0",reply_markup=InlineKeyboardMarkup(kb))

async def button(update: Update, context):
    q = update.callback_query; await q.answer()
    uid = str(q.from_user.id)
    users = get_users(); ratings = get_ratings(); tracks = get_tracks()
    if uid not in users:
        users[uid] = {"nick":q.from_user.first_name,"username":q.from_user.username or "","collection":[],"last_open":None,"created_at":datetime.now().isoformat(),"banned":False}
        save(DATA_FILE,users)
    u = users[uid]
    if u.get("banned"): await q.message.reply_text("🚫 Забанены."); return

    if q.data == "open":
        if u.get("last_open"):
            last = datetime.fromisoformat(u["last_open"])
            if datetime.now() - last < timedelta(hours=2):
                left = timedelta(hours=2) - (datetime.now() - last)
                h,m = left.seconds//3600, (left.seconds%3600)//60
                await q.message.reply_text(f"⏳ Следующий кейс через {h}ч {m}м"); return
        if not tracks: await q.message.reply_text("Нет треков."); return
        collected = [t["title"] for t in u["collection"]]
        available = [t for t in tracks if t["title"] not in collected]
        if not available: await q.message.reply_text("🎉 Вся коллекция собрана!"); return
        track = weighted_choice(available, ratings).copy()
        track["obtained_at"] = datetime.now().isoformat()
        track["rated"] = False
        u["last_open"] = datetime.now().isoformat()
        u["collection"].append(track)
        save(DATA_FILE,users)
        idx = len(u["collection"])-1
        kb = [[InlineKeyboardButton(f"⭐ {i}",callback_data=f"rate_{i}_{idx}")] for i in range(1,6)]
        await q.message.reply_text(f"🎁 {track['title']} — {track['artist']}\nОцени:",reply_markup=InlineKeyboardMarkup(kb))
        if os.path.exists(track.get("file","")): 
            with open(track["file"],"rb") as f: await context.bot.send_audio(chat_id=uid,audio=f,title=track["title"],performer=track["artist"])
        else: await q.message.reply_text("⚠ Файл не найден.")

    elif q.data.startswith("rate_"):
        _,r,idx = q.data.split("_"); r,idx = int(r),int(idx)
        if idx < len(u["collection"]) and not u["collection"][idx].get("rated"):
            u["collection"][idx]["rated"] = True; u["collection"][idx]["rating"] = r
            save(DATA_FILE,users)
            t = u["collection"][idx]["title"]
            if t not in ratings: ratings[t] = []
            ratings[t].append(r); save(RATINGS_FILE,ratings)
            avg = sum(ratings[t])/len(ratings[t])
            await q.message.reply_text(f"⭐ {r}/5 | Средняя: {avg:.1f} ({len(ratings[t])})")
        else: await q.message.reply_text("Уже оценено!")

    elif q.data == "col":
        if not u.get("collection"): await q.message.reply_text("📦 Пусто.")
        else:
            kb = []
            for i,t in enumerate(u["collection"]):
                r = f"⭐{t.get('rating','?')}" if t.get("rated") else "—"
                kb.append([InlineKeyboardButton(f"{i+1}. {t['title']} — {t['artist']} {r}",callback_data=f"listen_{i}")])
            kb.append([InlineKeyboardButton("🎁 Подарить",callback_data="gift_menu"),
                       InlineKeyboardButton("🔄 Обмен",callback_data="trade_menu")])
            kb.append([InlineKeyboardButton("« Назад",callback_data="main_menu")])
            await q.message.reply_text("📦 Коллекция:",reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("listen_"):
        idx = int(q.data.split("_")[1])
        if idx < len(u["collection"]):
            t = u["collection"][idx]
            if os.path.exists(t.get("file","")):
                with open(t["file"],"rb") as f: await context.bot.send_audio(chat_id=uid,audio=f,title=t["title"],performer=t["artist"])
            else: await q.message.reply_text("⚠ Файл не найден.")

    elif q.data == "gift_menu":
        if not u.get("collection"): await q.message.reply_text("Нечего дарить.")
        else:
            kb = [[InlineKeyboardButton(f"{t['title']} — {t['artist']}",callback_data=f"gift_{i}")] for i,t in enumerate(u["collection"])]
            kb.append([InlineKeyboardButton("« Назад",callback_data="col")])
            await q.message.reply_text("Выбери трек для подарка:",reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("gift_"):
        idx = int(q.data.split("_")[1])
        context.user_data["gift_idx"] = idx
        await q.message.reply_text("Введи @username получателя:")

    elif q.data == "trade_menu":
        if len(u.get("collection",[])) < 1: await q.message.reply_text("Нечего менять.")
        else:
            kb = [[InlineKeyboardButton(f"{t['title']} — {t['artist']}",callback_data=f"trade_my_{i}")] for i,t in enumerate(u["collection"])]
            kb.append([InlineKeyboardButton("« Назад",callback_data="col")])
            await q.message.reply_text("Выбери свой трек для обмена:",reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("trade_my_"):
        idx = int(q.data.split("_")[2])
        context.user_data["trade_my_idx"] = idx
        await q.message.reply_text("Введи @username игрока:")

    elif q.data == "profile":
        rd = u.get("created_at","?")
        if rd!="?": rd = datetime.fromisoformat(rd).strftime("%d.%m.%Y")
        my_ratings = sum(1 for t in u["collection"] if t.get("rated"))
        await q.message.reply_text(f"👤 {u['nick']}\n🆔 {uid}\n📅 {rd}\n🎵 {len(u['collection'])} треков\n⭐ Оценок: {my_ratings}")

    elif q.data == "shazam_info":
        await q.message.reply_text("🔍 Отправь мне аудиофайл или название трека — я поищу его в системе.")

    elif q.data == "main_menu":
        kb = [[InlineKeyboardButton("🎁 Открыть кейс",callback_data="open")],
              [InlineKeyboardButton("📦 Коллекция",callback_data="col")],
              [InlineKeyboardButton("👤 Профиль",callback_data="profile")],
              [InlineKeyboardButton("🔍 Найти трек",callback_data="shazam_info")]]
        await q.message.reply_text("🎵 Меню:",reply_markup=InlineKeyboardMarkup(kb))

async def handle_text(update: Update, context):
    uid = str(update.effective_user.id)
    text = update.message.text.strip()
    users = get_users(); ratings = get_ratings(); tracks = get_tracks()

    if update.effective_user.id == ADMIN_ID:
        if text.startswith("/broadcast "):
            msg = text[len("/broadcast "):]
            for u in users:
                try: await context.bot.send_message(chat_id=u,text=f"📢 {msg}")
                except: pass
            await update.message.reply_text("✅ Рассылка отправлена."); return
        if text.startswith("/stats"):
            await update.message.reply_text(f"👥 {len(users)}\n🎵 {len(tracks)}\n⭐ {sum(len(v) for v in ratings.values())}"); return
        if text.startswith("/delete "):
            remove_track(text[len("/delete "):]); await update.message.reply_text("🗑 Удалён."); return
        if text.startswith("/ban "):
            t = text[len("/ban "):].replace("@","")
            for uid,u in users.items():
                if u.get("username","").lower()==t.lower() or u.get("nick","").lower()==t.lower():
                    u["banned"]=True; save(DATA_FILE,users); await update.message.reply_text(f"🚫 {t}"); return
            await update.message.reply_text("Не найден."); return
        if text.startswith("/unban "):
            t = text[len("/unban "):].replace("@","")
            for uid,u in users.items():
                if u.get("username","").lower()==t.lower() or u.get("nick","").lower()==t.lower():
                    u["banned"]=False; save(DATA_FILE,users); await update.message.reply_text(f"✅ {t}"); return
            await update.message.reply_text("Не найден."); return

    if "gift_idx" in context.user_data:
        target = text.replace("@","").strip(); tid = None
        for i,u in users.items():
            if u.get("username","").lower()==target.lower(): tid=i; break
        if not tid: await update.message.reply_text("❌ Не найден."); del context.user_data["gift_idx"]; return
        idx = context.user_data["gift_idx"]; track = users[uid]["collection"][idx]
        if track["title"] in [t["title"] for t in users[tid]["collection"]]:
            await update.message.reply_text("❌ Уже есть."); del context.user_data["gift_idx"]; return
        users[tid]["collection"].append(track); users[uid]["collection"].pop(idx)
        save(DATA_FILE,users)
        await update.message.reply_text(f"🎁 '{track['title']}' → @{target}!")
        try: await context.bot.send_message(chat_id=tid,text=f"🎁 @{users[uid].get('username',uid)} подарил: {track['title']} — {track['artist']}")
        except: pass
        del context.user_data["gift_idx"]; return

    if "trade_my_idx" in context.user_data:
        target = text.replace("@","").strip(); tid = None
        for i,u in users.items():
            if u.get("username","").lower()==target.lower(): tid=i; break
        if not tid: await update.message.reply_text("❌ Не найден."); del context.user_data["trade_my_idx"]; return
        my_idx = context.user_data["trade_my_idx"]; my_track = users[uid]["collection"][my_idx]
        if my_track["title"] in [t["title"] for t in users[tid]["collection"]]:
            await update.message.reply_text("❌ Уже есть."); del context.user_data["trade_my_idx"]; return
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
        if their_idx is None: await update.message.reply_text("❌ Не найден."); return
        their_track = tc[their_idx]
        if their_track["title"] in [t["title"] for t in users[uid]["collection"]]:
            await update.message.reply_text("❌ Уже есть."); return
        my_idx = context.user_data["trade_my_track"]; my_track = users[uid]["collection"][my_idx]
        kb = [[InlineKeyboardButton("✅",callback_data=f"trade_acc_{uid}_{my_idx}_{tid}_{their_idx}"),
               InlineKeyboardButton("❌",callback_data=f"trade_dec_{tid}_{uid}")]]
        await context.bot.send_message(chat_id=tid,text=f"🔄 {users[uid]['username']or uid}: {my_track['title']} ↔ {their_track['title']}",reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ Запрос отправлен!")
        for k in ["trade_my_idx","trade_target","trade_my_track"]:
            if k in context.user_data: del context.user_data[k]; return

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
        kb=[[InlineKeyboardButton("📩 Отправить запрос",callback_data="req_admin")]]
        await update.message.reply_text("❌ Не найдено. Отправить запрос?",reply_markup=InlineKeyboardMarkup(kb))

async def handle_audio(update: Update, context):
    uid = update.effective_user.id; users=get_users(); ratings=get_ratings(); tracks=get_tracks()
    audio = update.message.audio or update.message.voice
    if not audio: return
    if uid == ADMIN_ID:
        title = audio.file_name or "Без названия"
        artist = "Неизвестен"
        file = await context.bot.get_file(audio.file_id)
        file_path = os.path.join(MUSIC_DIR, f"{audio.file_id}.mp3")
        await file.download_to_drive(file_path)
        kb = [[InlineKeyboardButton(r.capitalize(),callback_data=f"addrar_{r}")] for r in ["common","rare","epic","legendary"]]
        context.user_data["new_track"]={"title":title,"artist":artist,"file_path":file_path}
        await update.message.reply_text(f"🎵 {title}\nРедкость:",reply_markup=InlineKeyboardMarkup(kb)); return
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
        kb=[[InlineKeyboardButton("📩 Отправить запрос",callback_data="req_admin")]]
        context.user_data["shazam_request"]=title
        await update.message.reply_text("❌ Не найдено. Отправить запрос?",reply_markup=InlineKeyboardMarkup(kb))

async def button_admin(update: Update, context):
    q=update.callback_query; await q.answer()
    if q.data.startswith("addrar_"):
        r=q.data.split("_")[1]
        if "new_track" in context.user_data:
            t=context.user_data["new_track"]; add_track(t["title"],t["artist"],t["file_path"],r)
            await q.message.reply_text(f"✅ {t['title']} ({r})"); del context.user_data["new_track"]; return
    if q.data.startswith("trade_acc_"):
        _,_,fu,mi,tu,ti=q.data.split("_"); mi,ti=int(mi),int(ti); users=get_users()
        mt=users[fu]["collection"].pop(mi); tt=users[tu]["collection"].pop(ti)
        users[fu]["collection"].append(tt); users[tu]["collection"].append(mt)
        save(DATA_FILE,users); await q.message.reply_text("✅ Обмен!")
        await context.bot.send_message(chat_id=fu,text=f"✅ {mt['title']} ↔ {tt['title']}"); return
    if q.data.startswith("trade_dec_"):
        _,_,fu,tu=q.data.split("_")
        await context.bot.send_message(chat_id=fu,text="❌ Отклонён."); await q.message.reply_text("Отклонён."); return
    if q.data=="req_admin":
        users=get_users(); uid=str(q.from_user.id)
        req=context.user_data.get("shazam_request","?")
        await context.bot.send_message(chat_id=ADMIN_ID,text=f"📩 @{users[uid].get('username',uid)}: добавить '{req}'")
        if "shazam_request" in context.user_data: del context.user_data["shazam_request"]
        await q.message.reply_text("✅ Отправлено!"); return

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(button,pattern="^(?!addrar_|trade_acc_|trade_dec_|req_admin).*"))
    app.add_handler(CallbackQueryHandler(button_admin,pattern="^(addrar_|trade_acc_|trade_dec_|req_admin)"))
    app.add_handler(MessageHandler(filters.TEXT,handle_text))
    app.add_handler(MessageHandler(filters.AUDIO,handle_audio))
    print("Бот запущен!")
    app.run_polling()

if __name__=="__main__":
    main()
