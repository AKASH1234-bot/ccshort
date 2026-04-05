import asyncio
import re
import ast
import math
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, LOG_CHANNEL
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, temp, get_settings, save_group_settings, get_shortlink
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.filters_mdb import del_all, find_filter, get_filters
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}

# Channel buttons — shown only when file is delivered to user
CHANNEL_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🎬 Movie Search",  url="https://t.me/+AngJ8lGmH4wwNWY1"),
        InlineKeyboardButton("📢 Movie Updates", url="https://t.me/cinemaclubnew"),
    ],
    [InlineKeyboardButton("📰 Movie News", url="https://t.me/ccl_news")],
])


# ── Helpers ────────────────────────────────────────────────────────

def _caption(files):
    title = files.file_name
    size  = get_size(files.file_size)
    cap   = files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            cap = CUSTOM_FILE_CAPTION.format(
                file_name=title or '', file_size=size or '', file_caption=cap or '')
        except Exception:
            pass
    return cap or title or ''


def _file_btns(files, settings):
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings['button']:
        return [[InlineKeyboardButton(
            f"📁 [{get_size(f.file_size)}] {f.file_name}",
            url=f"https://telegram.dog/{temp.U_NAME}?start=files_{f.file_id}"
        )] for f in files]
    return [[
        InlineKeyboardButton(f.file_name,        callback_data=f'{pre}#{f.file_id}'),
        InlineKeyboardButton(get_size(f.file_size), callback_data=f'{pre}#{f.file_id}'),
    ] for f in files]


# ── Handlers ───────────────────────────────────────────────────────

@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def give_filter(client, message):
    if not await manual_filters(client, message):
        await auto_filter(client, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    _, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer("Not for you!", show_alert=True)
    try: offset = int(offset)
    except: offset = 0
    search = BUTTONS.get(key)
    if not search:
        return await query.answer("Old message — search again.", show_alert=True)
    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try: n_offset = int(n_offset)
    except: n_offset = 0
    if not files: return
    settings = await get_settings(query.message.chat.id)
    btn = _file_btns(files, settings)
    off_set = 0 if 0 < offset <= 10 else (None if offset == 0 else offset - 10)
    page = f"🗓 {math.ceil(offset/10)+1}/{math.ceil(total/10)}"
    if n_offset == 0:
        btn.append([InlineKeyboardButton("⏪ Back", callback_data=f"next_{req}_{key}_{off_set}"), InlineKeyboardButton(page, callback_data="pages")])
    elif off_set is None:
        btn.append([InlineKeyboardButton(page, callback_data="pages"), InlineKeyboardButton("Next ⏩", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append([InlineKeyboardButton("⏪ Back", callback_data=f"next_{req}_{key}_{off_set}"), InlineKeyboardButton(page, callback_data="pages"), InlineKeyboardButton("Next ⏩", callback_data=f"next_{req}_{key}_{n_offset}")])
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^spolling"))
async def spoll_handler(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("Not for you!", show_alert=True)
    movie = await get_poster(id, id=True)
    search = movie.get('title')
    await query.answer('Searching...')
    files, offset, total = await get_search_results(search, offset=0, filter=True)
    if files:
        await auto_filter(bot, query, (search, files, offset, total))
    else:
        k = await query.message.edit(f"<b>No results for '{search}'</b>")
        await asyncio.sleep(10)
        await k.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    d = query.data

    if d == "close_data":
        return await query.message.delete()

    if d == "pages":
        return await query.answer()

    if d == "delallconfirm":
        uid = query.from_user.id
        ct  = query.message.chat.type
        if ct == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(uid))
            if not grpid:
                return await query.message.edit_text("Not connected to any group.")
            try:
                chat = await client.get_chat(grpid)
                grp_id, title = grpid, chat.title
            except:
                return await query.message.edit_text("Make sure I'm in your group!")
        elif ct in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id, title = query.message.chat.id, query.message.chat.title
        else:
            return
        st = await client.get_chat_member(grp_id, uid)
        if st.status == enums.ChatMemberStatus.OWNER or str(uid) in ADMINS:
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("Only group owner can do this!", show_alert=True)
        return

    if d == "delallcancel":
        if query.message.chat.type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()
        else:
            st = await client.get_chat_member(query.message.chat.id, query.from_user.id)
            if st.status == enums.ChatMemberStatus.OWNER or str(query.from_user.id) in ADMINS:
                await query.message.delete()
                try: await query.message.reply_to_message.delete()
                except: pass
            else:
                await query.answer("Not for you!", show_alert=True)
        return

    if "groupcb" in d:
        await query.answer()
        gid = d.split(":")[1]; act = d.split(":")[2]
        hr   = await client.get_chat(int(gid))
        stat = "DISCONNECT" if act else "CONNECT"; cb = "disconnect" if act else "connectcb"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(stat, callback_data=f"{cb}:{gid}"), InlineKeyboardButton("DELETE", callback_data=f"deletecb:{gid}")], [InlineKeyboardButton("Back", callback_data="backcb")]])
        await query.message.edit_text(f"Group: **{hr.title}**\nID: `{gid}`", reply_markup=kb, parse_mode=enums.ParseMode.MARKDOWN)
        return

    if "connectcb" in d:
        await query.answer()
        gid = d.split(":")[1]; hr = await client.get_chat(int(gid))
        ok  = await make_active(str(query.from_user.id), str(gid))
        await query.message.edit_text(f"Connected to **{hr.title}**" if ok else "Error!", parse_mode=enums.ParseMode.MARKDOWN)
        return

    if "disconnect" in d:
        await query.answer()
        gid = d.split(":")[1]; hr = await client.get_chat(int(gid))
        ok  = await make_inactive(str(query.from_user.id))
        await query.message.edit_text(f"Disconnected from **{hr.title}**" if ok else "Error!", parse_mode=enums.ParseMode.MARKDOWN)
        return

    if "deletecb" in d:
        await query.answer()
        gid = d.split(":")[1]
        ok  = await delete_connection(str(query.from_user.id), str(gid))
        await query.message.edit_text("Connection deleted." if ok else "Error!")
        return

    if d == "backcb":
        await query.answer()
        gids = await all_connections(str(query.from_user.id))
        if not gids:
            return await query.message.edit_text("No active connections.")
        btns = []
        for gid in gids:
            try:
                ttl    = await client.get_chat(int(gid))
                active = await if_active(str(query.from_user.id), str(gid))
                act    = " — ACTIVE" if active else ""
                btns.append([InlineKeyboardButton(f"{ttl.title}{act}", callback_data=f"groupcb:{gid}:{act}")])
            except: pass
        if btns:
            await query.message.edit_text("Your connected groups:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if "alertmessage" in d:
        gid  = query.message.chat.id
        i    = d.split(":")[1]; kw = d.split(":")[2]
        _, btn, alerts, _ = await find_filter(gid, kw)
        if alerts:
            alerts = ast.literal_eval(alerts)
            await query.answer(alerts[int(i)].replace("\\n","\n").replace("\\t","\t"), show_alert=True)
        return

    if d.startswith("file"):
        ident, file_id = d.split("#")
        files_ = await get_file_details(file_id)
        if not files_: return await query.answer('File not found.')
        f_caption = _caption(files_[0])
        settings  = await get_settings(query.message.chat.id)
        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                return await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
            if settings['botpm']:
                return await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
            await client.send_cached_media(
                chat_id=query.from_user.id, file_id=file_id,
                caption=f_caption, protect_content=(ident=="filep"),
                reply_markup=CHANNEL_BUTTONS)
            await query.answer('File sent to your PM!', show_alert=True)
        except UserIsBlocked:
            await query.answer('Please unblock the bot!', show_alert=True)
        except (PeerIdInvalid, Exception):
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        return

    if d.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            return await query.answer("Join required channels first!", show_alert=True)
        ident, file_id = d.split("#")
        files_ = await get_file_details(file_id)
        if not files_: return await query.answer('File not found.')
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id, file_id=file_id,
            caption=_caption(files_[0]), protect_content=(ident=='checksubp'),
            reply_markup=CHANNEL_BUTTONS)
        return

    if d == "start":
        btns = [
            [InlineKeyboardButton('➕ Add Me To Your Group', url=f'http://t.me/{temp.U_NAME}?startgroup=true')],
            [InlineKeyboardButton('🎬 Movie Search Group', url='https://t.me/+AngJ8lGmH4wwNWY1')],
            [InlineKeyboardButton('📢 Movie Updates', url='https://t.me/cinemaclubnew')],
        ]
        await query.message.edit_text(script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME), reply_markup=InlineKeyboardMarkup(btns), parse_mode=enums.ParseMode.HTML)
        return await query.answer()

    if d == "help":
        btns = [
            [InlineKeyboardButton('Manual Filter', callback_data='manuelfilter'), InlineKeyboardButton('Auto Filter', callback_data='autofilter')],
            [InlineKeyboardButton('Connection', callback_data='coct'), InlineKeyboardButton('Extra Mods', callback_data='extra')],
            [InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('📊 Status', callback_data='stats')],
        ]
        await query.message.edit_text(script.HELP_TXT.format(query.from_user.mention), reply_markup=InlineKeyboardMarkup(btns), parse_mode=enums.ParseMode.HTML)
        return await query.answer()

    if d == "about":
        btns = [[InlineKeyboardButton('🏠 Home', callback_data='start'), InlineKeyboardButton('🔐 Close', callback_data='close_data')]]
        await query.message.edit_text(script.ABOUT_TXT.format(temp.B_NAME), reply_markup=InlineKeyboardMarkup(btns), parse_mode=enums.ParseMode.HTML)
        return await query.answer()

    txt_map = {
        "manuelfilter": (script.MANUELFILTER_TXT, [[InlineKeyboardButton('Back', callback_data='help'), InlineKeyboardButton('Buttons', callback_data='button')]]),
        "autofilter":   (script.AUTOFILTER_TXT,   [[InlineKeyboardButton('Back', callback_data='help')]]),
        "coct":         (script.CONNECTION_TXT,    [[InlineKeyboardButton('Back', callback_data='help')]]),
        "extra":        (script.EXTRAMOD_TXT,      [[InlineKeyboardButton('Back', callback_data='help'), InlineKeyboardButton('Admin', callback_data='admin')]]),
        "admin":        (script.ADMIN_TXT,         [[InlineKeyboardButton('Back', callback_data='extra')]]),
        "button":       (script.BUTTON_TXT,        [[InlineKeyboardButton('Back', callback_data='manuelfilter')]]),
        "source":       (script.SOURCE_TXT,        [[InlineKeyboardButton('Back', callback_data='about')]]),
    }
    if d in txt_map:
        txt, btns = txt_map[d]
        await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode=enums.ParseMode.HTML)
        return await query.answer()

    if d in ("stats", "rfrsh"):
        total   = await Media.count_documents()
        users   = await db.total_users_count()
        chats   = await db.total_chat_count()
        monsize = await db.get_db_size()
        btns = [[InlineKeyboardButton('Back', callback_data='help'), InlineKeyboardButton('♻️', callback_data='rfrsh')]]
        await query.message.edit_text(
            script.STATUS_TXT.format(total, users, chats, get_size(monsize), get_size(536870912 - monsize)),
            reply_markup=InlineKeyboardMarkup(btns), parse_mode=enums.ParseMode.HTML)
        return await query.answer()

    if d.startswith("setgs"):
        _, set_type, status, grp_id = d.split("#")
        grpid = await active_connection(str(query.from_user.id))
        if str(grp_id) != str(grpid):
            await query.message.edit("Active connection changed. Go to /settings.")
            return await query.answer()
        await save_group_settings(grpid, set_type, status != "True")
        settings = await get_settings(grpid)
        if settings:
            def s(k): return '✅' if settings[k] else '❌'
            btns = [
                [InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings["button"]}#{grp_id}'), InlineKeyboardButton('Single' if settings["button"] else 'Double', callback_data=f'setgs#button#{settings["button"]}#{grp_id}')],
                [InlineKeyboardButton('Bot PM',       callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}'),        InlineKeyboardButton(s("botpm"),       callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}')],
                [InlineKeyboardButton('File Secure',  callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'), InlineKeyboardButton(s("file_secure"), callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')],
                [InlineKeyboardButton('IMDB',         callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),          InlineKeyboardButton(s("imdb"),        callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')],
                [InlineKeyboardButton('Spell Check',  callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'), InlineKeyboardButton(s("spell_check"), callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')],
                [InlineKeyboardButton('Welcome',      callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}'),    InlineKeyboardButton(s("welcome"),     callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}')],
            ]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(btns))
        return await query.answer()

    await query.answer()


# ── Auto filter ────────────────────────────────────────────────────

async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message  = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/") or re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if not (2 < len(message.text) < 100):
            return
        search = message.text
        files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
        if not files:
            return await spell_check(msg) if settings["spell_check"] else None
    else:
        settings = await get_settings(msg.message.chat.id)
        message  = msg.message.reply_to_message
        search, files, offset, total_results = spoll
        await msg.message.delete()

    btn = _file_btns(files, settings)
    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append([
            InlineKeyboardButton(f"🗓 1/{math.ceil(int(total_results)/10)}", callback_data="pages"),
            InlineKeyboardButton("Next ⏩", callback_data=f"next_{req}_{key}_{offset}"),
        ])
    else:
        btn.append([InlineKeyboardButton("🗓 1/1", callback_data="pages")])

    imdb = await get_poster(search, file=files[0].file_name) if settings["imdb"] else None
    if imdb:
        try:
            cap = settings['template'].format(
                query=search, title=imdb['title'], votes=imdb['votes'],
                aka=imdb["aka"], seasons=imdb["seasons"], box_office=imdb['box_office'],
                localized_title=imdb['localized_title'], kind=imdb['kind'],
                imdb_id=imdb["imdb_id"], cast=imdb["cast"], runtime=imdb["runtime"],
                countries=imdb["countries"], certificates=imdb["certificates"],
                languages=imdb["languages"], director=imdb["director"],
                writer=imdb["writer"], producer=imdb["producer"],
                composer=imdb["composer"], cinematographer=imdb["cinematographer"],
                music_team=imdb["music_team"], distributors=imdb["distributors"],
                release_date=imdb['release_date'], year=imdb['year'],
                genres=imdb['genres'], poster=imdb['poster'],
                plot=imdb['plot'], rating=imdb['rating'], url=imdb['url'],
                **locals()
            )
        except Exception:
            cap = f"<b>Results for: {search}</b>"
    else:
        cap = f"<b>Results for: {search}</b>"

    markup = InlineKeyboardMarkup(btn)
    if imdb and imdb.get('poster'):
        try:
            await message.reply_photo(photo=imdb['poster'], caption=cap[:1024], reply_markup=markup)
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            await message.reply_photo(photo=imdb['poster'].replace('.jpg','._V1_UX360.jpg'), caption=cap[:1024], reply_markup=markup)
        except Exception as e:
            logger.exception(e)
            await message.reply_text(cap, reply_markup=markup)
    else:
        dll = await message.reply_text(cap, reply_markup=markup)
        await asyncio.sleep(180)
        fll = await dll.edit_text("<b>🗑 Results removed. Search again!</b>")
        await asyncio.sleep(180)
        await fll.delete()
        await message.delete()


async def spell_check(msg):
    search = msg.text
    btn = [[InlineKeyboardButton("🔎 Search Google", url=f"https://www.google.com/search?q={search.replace(' ', '+')}")]]
    try:
        movies = await get_poster(search, bulk=True)
    except:
        movies = None
    if not movies:
        n = await msg.reply_text(f"<b>No results for '{search}'</b>", reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try: await msg.delete()
        except: pass
        return
    user    = msg.from_user.id if msg.from_user else 0
    buttons = [[InlineKeyboardButton(m.get('title'), callback_data=f"spolling#{m.movieID}#{user}")] for m in movies]
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])
    s = await msg.reply_text(f"<b>No match for '{search}'. Did you mean:</b>", reply_markup=InlineKeyboardMarkup(buttons))
    await asyncio.sleep(120)
    await s.delete()
    try: await msg.delete()
    except: pass


async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name     = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        if re.search(r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])", name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)
            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")
            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            dm = await client.send_message(group_id, reply_text, disable_web_page_preview=True, reply_to_message_id=reply_id)
                        else:
                            dm = await client.send_message(group_id, reply_text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(eval(btn)), reply_to_message_id=reply_id)
                    elif btn == "[]":
                        dm = await client.send_cached_media(group_id, fileid, caption=reply_text or "", reply_to_message_id=reply_id)
                    else:
                        dm = await message.reply_cached_media(fileid, caption=reply_text or "", reply_markup=InlineKeyboardMarkup(eval(btn)), reply_to_message_id=reply_id)
                    await asyncio.sleep(30)
                    await dm.delete()
                    await message.delete()
                except Exception as e:
                    logger.exception(e)
            return True
    return False
