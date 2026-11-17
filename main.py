import builtins
builtins.print = lambda *args, **kwargs: None
import asyncio
import gzip
import html
import http.client
import io
import json
import os
import random
import re
import string
import subprocess
import sys
import time
import zlib
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import brotli
except ImportError:
    brotli = None

try:
    from getids import get_date_as_string
except ImportError:
    import subprocess, sys
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "git+https://github.com/AmanoTeam/python-getids.git",
             "--break-system-packages", "--quiet"],
            timeout=60,
        )
        from getids import get_date_as_string
    except Exception:
        get_date_as_string = None

from telethon import TelegramClient, events, functions, types
from telethon.errors import (
    ChatAdminRequiredError,
    FloodWaitError,
    MessageIdInvalidError,
    MessageNotModifiedError,
    UserAdminInvalidError,
    UsernameNotOccupiedError,
    ChannelPrivateError,
    ChannelBannedError,
    UserIdInvalidError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UserBannedInChannelError,
    UsersTooMuchError,
)
from telethon.sessions import StringSession
from telethon.tl.functions.channels import EditAdminRequest, EditBannedRequest
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.types import (
    ChatAdminRights,
    ChatBannedRights,
    MessageEntityMentionName,
    ChatInvite,
    ChatInviteAlready,
    User,
    Channel,
    Chat,
    DocumentAttributeAudio,        # ← أضف هذا
    DocumentAttributeFilename,     # ← وأضف هذا
)

import shutil
import tempfile
import concurrent.futures
import urllib.request
import urllib.parse
import urllib.error
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
THUMBNAIL_PATH = os.path.join(DATA_DIR, "yt_thumb.jpg")   # ← أضف هذا السطر

def load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {}
    else:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    cfg["API_ID"] = int(cfg.get("API_ID") or os.environ.get("API_ID") or 0)
    cfg["API_HASH"] = cfg.get("API_HASH") or os.environ.get("API_HASH") or ""
    _PLACEHOLDER_HASHES = ("", "your_api_hash_here", "YOUR_API_HASH_HERE", "0123456789abcdef0123456789abcdef")
    if cfg["API_HASH"].strip() in _PLACEHOLDER_HASHES:
        cfg["API_HASH"] = ""
    if cfg["API_ID"] in (0, 1234567):
        cfg["API_ID"] = 0
    cfg["STRING_SESSION"] = (
        cfg.get("STRING_SESSION") or os.environ.get("STRING_SESSION") or ""
    )
    cfg["PREFIX"] = cfg.get("PREFIX") or "."
    cfg["OWNER_NAME"] = cfg.get("OWNER_NAME") or "الجوكر"
    if not cfg["API_ID"] or not cfg["API_HASH"]:
        print("=" * 45)
        pass
        print("=" * 45)
        try:
            aid = input("* API_ID: ").strip()
            ahash = input("* API_HASH: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("تم الإلغاء")
            sys.exit(1)
        cfg["API_ID"] = int(aid) if aid.isdigit() else 0
        cfg["API_HASH"] = ahash
        if not cfg["API_ID"] or not cfg["API_HASH"]:
            print("بيانات غير صحيحة")
            sys.exit(1)
        _save_cfg_basic(cfg)
        print("✓ تم حفظ API_ID و API_HASH")
    return cfg


def _save_cfg_basic(cfg):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data["API_ID"] = cfg["API_ID"]
    data["API_HASH"] = cfg["API_HASH"]
    data["PREFIX"] = cfg["PREFIX"]
    data["OWNER_NAME"] = cfg["OWNER_NAME"]
    data["STRING_SESSION"] = cfg.get("STRING_SESSION", "")
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_session(session_str):
    """حفظ كود السيشن المولّد تلقائياً في config.json"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data["STRING_SESSION"] = session_str
    data.setdefault("API_ID", CONFIG["API_ID"])
    data.setdefault("API_HASH", CONFIG["API_HASH"])
    data.setdefault("PREFIX", CONFIG["PREFIX"])
    data.setdefault("OWNER_NAME", CONFIG["OWNER_NAME"])
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


CONFIG = load_config()
PREFIX = CONFIG["PREFIX"]
OWNER_NAME = CONFIG["OWNER_NAME"]



def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def db_read(name, default=None):
    """قراءة ملف json | كل ميزة لها ملفها الخاص"""
    p = _path(name)
    if not os.path.exists(p):
        return {} if default is None else default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def db_write(name, data):
    """كتابة ملف json"""
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def db_get(name, key, default=None):
    return db_read(name).get(str(key), default)


def db_set(name, key, value):
    data = db_read(name)
    data[str(key)] = value
    db_write(name, data)


def db_del(name, key):
    data = db_read(name)
    if str(key) in data:
        del data[str(key)]
        db_write(name, data)
        return True
    return False



client = TelegramClient(
    StringSession(CONFIG["STRING_SESSION"]),
    CONFIG["API_ID"],
    CONFIG["API_HASH"],
    device_model="rkkyk Userbot",
    system_version="Android 12",
    app_version="rkkyk 2.3",
    lang_code="ar",
    system_lang_code="ar",
    auto_reconnect=True,
    connection_retries=10,
    retry_delay=2,
    flood_sleep_threshold=60,
)

START_TIME = time.time()
CMD_SECTIONS = {}




def cmd(pattern, groups_only=False, private_only=False, edited=True):
    """
    ديكوريتر تسجيل امر جديد
    pattern: النمط بعد البادئة | مثال: r"حظر(?:\\s|$)([\\s\\S]*)"
    """
    reg = re.compile("^\\" + PREFIX + pattern)

    def decorator(func):
        async def wrapper(event):
            if groups_only and not event.is_group:
                return await edit_delete(event, "- هذا الأمر للمجموعات فقط", 8)
            if private_only and not event.is_private:
                return await edit_delete(event, "- هذا الأمر للخاص فقط", 8)
            try:
                await func(event)
            except events.StopPropagation:
                raise
            except MessageNotModifiedError:
                pass
            except MessageIdInvalidError:
                pass
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 3)
            except ChatAdminRequiredError:
                await edit_delete(event, "- لا أملك صلاحيات كافية هنا", 8)
            except Exception as e:
                await edit_delete(event, f"- خطأ:\n`{e}`", 12)

        client.add_event_handler(
            wrapper, events.NewMessage(pattern=reg, outgoing=True)
        )
        if edited:
            client.add_event_handler(
                wrapper, events.MessageEdited(pattern=reg, outgoing=True)
            )
        return wrapper

    return decorator




async def edit_or_reply(event, text, link_preview=False, **kwargs):
    """يعدّل رسالتك أو يرد | يتعامل مع النص الطويل كملف | مع fallback عند فشل الإرسال"""
    text = str(text)
    try:
        if len(text) < 4096:
            try:
                return await event.edit(text, link_preview=link_preview, **kwargs)
            except Exception:
                return await event.reply(text, link_preview=link_preview, **kwargs)
        return await _send_as_file(event, text)
    except MessageNotModifiedError:
        return event
    except Exception:
        try:
            return await _send_as_file(event, text)
        except Exception:
            return event


async def _send_as_file(event, text):
    """يرسل النص كملف نصي مع تجنّب خطأ الإرسال"""
    try:
        file = io.BytesIO(text.encode("utf-8"))
        file.name = "result.txt"
        reply = await event.get_reply_message()
        target = reply or event
        sent = await target.reply("الناتج طويل/كبير — تم إرساله كملف ", file=file)
        try:
            await event.delete()
        except Exception:
            pass
        return sent
    except Exception as e:
        return await _send_chunks(event, text, str(e))


async def _send_chunks(event, text, err=""):
    limit = 4000
    parts = [text[i:i + limit] for i in range(0, len(text), limit)]
    out = []
    for i, p in enumerate(parts, 1):
        prefix = f"(جزء {i}/{len(parts)}) " if len(parts) > 1 else ""
        try:
            out.append(await event.reply(prefix + p))
        except Exception:
            pass
    if not out and err:
        try:
            await event.reply(f"تعذّر الإرسال: {err}")
        except Exception:
            pass
    return out


async def edit_delete(event, text, seconds=8, link_preview=False):
    """يعدّل الرسالة ثم يحذفها بعد وقت"""
    try:
        msg = await event.edit(text, link_preview=link_preview)
    except Exception:
        try:
            msg = await event.reply(text, link_preview=link_preview)
        except Exception:
            return
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        pass


async def get_target_user(event):
    """يجلب المستخدم المستهدف: بالرد أو بالمعرف/الايدي مع الأمر"""
    reply = await event.get_reply_message()
    if reply:
        try:
            user = await event.client.get_entity(reply.sender_id)
            return user, reply.sender_id
        except Exception:
            return None, reply.sender_id
    args = event.pattern_match.group(1)
    if args and args.strip():
        arg = args.strip().split()[0]
        try:
            if arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
                user = await event.client.get_entity(int(arg))
            else:
                user = await event.client.get_entity(arg)
            return user, user.id
        except Exception:
            return None, None
    return None, None


def get_display_name(user):
    if user is None:
        return "مجهول"
    name = user.first_name or ""
    if getattr(user, "last_name", None):
        name += f" {user.last_name}"
    return name.strip() or "مجهول"


def mention(user):
    if user is None:
        return "مجهول"
    return f"[{get_display_name(user)}](tg://user?id={user.id})"


def readable_time(seconds):
    seconds = int(seconds)
    result = ""
    for unit, count in (("ي", 86400), ("س", 3600), ("د", 60), ("ث", 1)):
        if seconds >= count:
            val = seconds // count
            seconds %= count
            result += f"{val}{unit} "
    return result.strip() or "0ث"



MENU_MAIN = f"""✦ ────『قـائـمـة اوامر سورس الـجـوكر』──── ✦
مرحبا بك عزيزي {OWNER_NAME}

• `{PREFIX}م1` ➪ اوامـر الاداره
• `{PREFIX}م2` ➪ اوامـر المجموعه
• `{PREFIX}م3` ➪ اوامـر الكشف والايدي
• `{PREFIX}م4` ➪ اوامـر الردود
• `{PREFIX}م5` ➪ اوامـر الترحيب
• `{PREFIX}م6` ➪ اوامـر حمايه الخاص
• `{PREFIX}م7` ➪ اوامـر الاذاعه
• `{PREFIX}م8` ➪ اوامـر البوت
• `{PREFIX}م9` ➪ اوامـر المنع والترجمه
• `{PREFIX}م10` ➪ اوامـر السبام والصملات
• `{PREFIX}م11` ➪ اوامـر البروفايل
• `{PREFIX}م12` ➪ اوامـر الصيغ
• `{PREFIX}م13` ➪ اوامـر التسليه
• `{PREFIX}م14` ➪ اوامـر التحكم
• `{PREFIX}م15` ➪ اوامـر الذكاء الاصطناعي
• `{PREFIX}م16` ➪ اوامـر التحديثات
• `{PREFIX}م17` ➪ اوامـر الفحص والبلاغات
• `{PREFIX}م18` ➪ اوامـر الاسم الوقتي
• `{PREFIX}م19` ➪ اوامـر محوّل الصوت
• `{PREFIX}م20` ➪ اوامـر الكتم
• `{PREFIX}م21` ➪ اوامـر التفليش
• `{PREFIX}م22` ➪ اوامـر التحميل
• `{PREFIX}م23` ➪ اوامـر النشر التلقائي
• `{PREFIX}م24` ➪ اوامـر حفظ المؤقتة
✦ ─────────────────────────── ✦"""
# ═══════════════════════════════════════════════════════════
#  م24 — الحفظ التلقائي للوسائط ذاتية التدمير
# ═══════════════════════════════════════════════════════════

def _selfsave_enabled():
    return db_get("settings", "selfsave_enabled", False)

@cmd(r"تشغيل حفظ المؤقتة$")
async def _(event):
    db_set("settings", "selfsave_enabled", True)
    await edit_or_reply(event,
        "✅ تم **تفعيل** الحفظ التلقائي\n\n"
        "🔒 كل وسائط ذاتية التدمير (صورة/فيديو) تُرسل لك في الخاص، "
        "سيتم نسخها فوراً إلى المحفوظات مع معلومات المرسل."
    )


@cmd(r"تعطيل حفظ المؤقتة$")
async def _(event):
    db_set("settings", "selfsave_enabled", False)
    await edit_or_reply(event, "🛑 تم **تعطيل** الحفظ التلقائي")


@cmd(r"حفظ المؤقتة$")
async def _(event):
    status = "🟢 **مفعل**" if _selfsave_enabled() else "🔴 **معطل**"
    await edit_or_reply(event,
    f"**⚙️ حالة حفظ المؤقتة:** {status}\n\n"
    f"📌 يلتقط الوسائط ذاتية التدمير فوراً وينسخها للمحفوظات مع اسم المرسل والآيدي والوقت.\n\n"
    f"▶️ `.تشغيل حفظ المؤقتة`\n"
    f"⏹️ `.تعطيل حفظ المؤقتة`"
)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and e.media))
async def _save_self_destruct(event):
    if not _selfsave_enabled():
        return

    try:
        media = event.message.media
        if media is None:
            return

        ttl = getattr(media, "ttl_seconds", 0) or 0
        if not ttl:
            ttl = getattr(event.message, "ttl_period", 0) or 0
        if not ttl:
            return

        sender = await event.get_sender()
        if not sender:
            return

        sender_id = sender.id

        # 🔹 جلب بيانات كاملة
        try:
            fresh = await client.get_entity(sender_id)
            if fresh:
                sender = fresh
        except Exception as e:
            print(f"[selfsave] get_entity: {e}")

        try:
            pfull = await client(functions.users.GetFullUserRequest(sender))
            users_list = getattr(pfull, "users", None) or []
            for u in users_list:
                if getattr(u, "id", None) == sender_id:
                    sender = u
                    break
        except Exception as e:
            print(f"[selfsave] get_full: {e}")

        first = getattr(sender, "first_name", "") or ""
        last = getattr(sender, "last_name", "") or ""
        sender_name = (first + " " + last).strip() or "مجهول"

        # 🔹 اليوزر
        sender_username = getattr(sender, "username", None)
        if not sender_username:
            usernames_list = getattr(sender, "usernames", None) or []
            for un in usernames_list:
                if getattr(un, "active", False):
                    sender_username = getattr(un, "username", None)
                    break
            if not sender_username and usernames_list:
                sender_username = getattr(usernames_list[0], "username", None)

        username_str = f"@{sender_username}" if sender_username else "لا يوجد"

        # 🔹 الوقت
        now_obj = datetime.now()
        hour = int(now_obj.strftime("%I"))
        minute = now_obj.strftime("%M")
        am_pm = "م" if now_obj.strftime("%p") == "PM" else "ص"
        time_str = f"{hour}:{minute} {am_pm}"
        date_str = now_obj.strftime("%Y-%m-%d")

        media_type = "🖼️ صورة"
        if "Document" in type(media).__name__:
            media_type = "🎬 فيديو"

        if ttl >= 2147483640 or ttl > 86400:
            duration_str = "🔥 مشاهدة واحدة"
        elif ttl >= 3600:
            h = ttl // 3600
            m = (ttl % 3600) // 60
            duration_str = f"{h}س {m}د" if m else f"{h} ساعة"
        elif ttl >= 60:
            duration_str = f"{ttl // 60} دقيقة"
        else:
            duration_str = f"{ttl} ثانية"

        # 🔹 بناء النص والتنسيقات (الاسم كرابط tg://user?id=)
        parts = []
        ents = []

        def add(text, ent_cls=None, **kw):
            offset = sum(len(p) for p in parts)
            parts.append(text)
            if ent_cls:
                ents.append(ent_cls(offset=offset, length=len(text), **kw))

        add("🔒 ")
        add("وسائط ذاتية التدمير", types.MessageEntityBold)
        add("\n\n👤 ")
        add("المرسل: ", types.MessageEntityBold)
        # 🔗 الاسم كرابط مباشر للحساب
        add(
            sender_name,
            types.MessageEntityTextUrl,
            url=f"tg://user?id={sender_id}",
        )
        add("\n🆔 ")
        add("الآيدي: ", types.MessageEntityBold)
        add(str(sender_id), types.MessageEntityCode)
        add("\n🔗 ")
        add("المعرف: ", types.MessageEntityBold)
        add(username_str)
        add("\n📅 ")
        add("التاريخ: ", types.MessageEntityBold)
        add(date_str, types.MessageEntityCode)
        add("\n⏰ ")
        add("الوقت: ", types.MessageEntityBold)
        add(time_str, types.MessageEntityCode)
        add("\n⏱️ ")
        add("المدة: ", types.MessageEntityBold)
        add(duration_str)
        add("\n📎 ")
        add("النوع: ", types.MessageEntityBold)
        add(media_type)

        full_caption = "".join(parts)

        try:
            file_path = await event.download_media()
        except Exception as e:
            print(f"[selfsave] download: {e}")
            return

        if not file_path or not os.path.exists(file_path):
            return

        try:
            await client.send_file(
                "me",
                file_path,
                caption=full_caption,
                formatting_entities=ents,
                force_document=False,
            )
            print(f"[selfsave] ✅ {sender_name} | {sender_id} | {username_str}")
        except Exception as e:
            print(f"[selfsave] send: {e}")

        try:
            os.remove(file_path)
        except Exception:
            pass

    except Exception as e:
        print(f"[selfsave] error: {e}")

def _fmt_section(txt):
    """يحوّل قوالب `{p}` و `{header_opa ...}` و `{b}` و `{e}` و `{cmd}` إلى نص منسق"""
    txt = re.sub(r"\{header_opa\s+(.+?)\}", r"╭─────────────────────╮\n    ◆ \1\n╰─────────────────────╯", txt)
    txt = txt.replace("{b}", "  • ")
    txt = txt.replace("{cmd}", PREFIX)
    txt = txt.replace("{e}", "")
    return txt

MENU = {
    "م1": """{header_opa امر الاداره}

{b}`{cmd}حظر`{e} — بالرد أو المعرف لحظر شخص
{b}`{cmd}الغاء حظر`{e} — لفك حظر شخص
{b}`{cmd}طرد`{e} — طرد شخص من المجموعة
{b}`{cmd}رفع مشرف`{e} — رفع شخص مشرف
{b}`{cmd}تنزيل مشرف`{e} — تنزيل مشرف
{b}`{cmd}تثبيت`{e} — تثبيت رسالة بالرد
{b}`{cmd}الغاء تثبيت`{e} — إلغاء التثبيت
{b}`{cmd}مسح`{e} — حذف رسائل بالعدد
{b}`{cmd}تحذير`{e} — تحذير عضو
{b}`{cmd}التحذيرات`{e} — عرض تحذيرات عضو
{b}`{cmd}حذف التحذيرات`{e} — مسح تحذيرات عضو""",
    "م2": """{header_opa امر المجموعه}

{b}`{cmd}المشرفين`{e} — عرض مشرفي المجموعة
{b}`{cmd}الاعضاء`{e} — عرض عدد الأعضاء
{b}`{cmd}معلومات`{e} — عرض معلومات المجموعة
{b}`{cmd}البوتات`{e} — عرض البوتات في المجموعة""",
    "م3": """{header_opa امر الكشف والايدي}

{b}`{cmd}الايدي`{e} — بالرد أو المعرف لعرض الايدي
{b}`{cmd}كشف`{e} — عرض معلومات مستخدم
{b}`{cmd}صورة`{e} — جلب صورة مستخدم
{b}`{cmd}انشاء`{e} — بالرد/المعرف لعرض تاريخ الإنشاء ودولة الحساب""",
    "م4": """{header_opa امر الردود}

{b}`{cmd}اضف رد`{e} — بالرد لإضافة رد على كلمة
{b}`{cmd}حذف رد`{e} — حذف رد
{b}`{cmd}الردود`{e} — عرض جميع الردود
{b}`{cmd}مسح الردود`{e} — حذف كل الردود""",
    "م5": """{header_opa امر الترحيب}

{b}`{cmd}ضبط ترحيب`{e} — ضبط رسالة ترحيب
{b}`{cmd}الترحيب`{e} — عرض الترحيب الحالي
{b}`{cmd}حذف الترحيب`{e} — إلغاء الترحيب""",
    "م6": """{header_opa امر حمايه الخاص}

{b}`{cmd}الحماية تشغيل`{e} — تشغيل حماية الخاص
{b}`{cmd}الحماية تعطيل`{e} — تعطيل حماية الخاص
{b}`{cmd}سماح`{e} — السماح لشخص بالخاص
{b}`{cmd}رفض`{e} — رفض شخص من الخاص
{b}`{cmd}المسموحين`{e} — عرض المسموح لهم""",
    "م7": """{header_opa امر الاذاعه}

{b}`{cmd}للكروبات`{e} — نشر رسالة بكل مجموعاتك
{b}`{cmd}للخاص`{e} — إرسال رسالة لكل محادثاتك الخاصة""",
    "م8": """{header_opa امر البوت}

{b}`{cmd}فحص`{e} — عرض معلومات السورس
{b}`{cmd}بنك`{e} — عرض سرعة الاستجابة
{b}`{cmd}اعادة تشغيل`{e} — إعادة تشغيل السورس
{b}`{cmd}الوقت`{e} — عرض مدة التشغيل""",
    "م9": """{header_opa امر المنع والترجمه}

{b}`{cmd}منع`{e} — منع كلمة في المجموعة
{b}`{cmd}الغاء منع`{e} — إلغاء منع كلمة
{b}`{cmd}قائمة المنع`{e} — عرض الكلمات الممنوعة
{b}`{cmd}ترجمة`{e} — بالرد لترجمة النص""",
    "م10": """{header_opa امر السبام والصملات}

{b}`{cmd}نيكه`{e} — سبام بتحديد أكثر من هدف (يوزرات/رد)
{b}`{cmd}خلاص`{e} — إيقاف السبام من كل الأهداف
{b}`{cmd}الأهداف`{e} — عرض أهداف الإرسال الجارية
{b}`{cmd}سرعه`{e} — ضبط سرعة الإرسال
{b}`{cmd}دفعة`{e} — عدد رسائل كل دفعة (مثل 1 ~ 10)
{b}`{cmd}سب ذكاء`{e} — توغل السب بـ AI بدل المولّد المحلي
{b}`{cmd}تتبع`{e} — رد تلقائي على رسائل شخص في الخاص أو المجموعات
{b}`{cmd}كافي`{e} — إيقاف الرد التلقائي
{b}`{cmd}معاينة سب`{e} — عرض عينات من المولّد
{b}`{cmd}عدد السب`{e} — عرض عدد التركيبات الممكنة
{b}`{cmd}اضف سب`{e} — لإثراء المكتبة
{b}`{cmd}حماية الفلود`{e} — تشغيل/إيقاف الحماية
{b}`{cmd}الفلود`{e} — عرض إحصائيات الحماية
{b}`{cmd}تحديد`{e} — بالرد لإضافة رسالة من المحفوظات (بدون حدود)
{b}`{cmd}الغاء تحديد`{e} — بالرد لإزالة رسالة محددة
{b}`{cmd}المحددات`{e} — عرض كل الرسائل المحددة
{b}`{cmd}مسح كل محدد`{e} — مسح كل الرسائل المحددة
{b}`{cmd}تشغيل التحويل`{e} — بدء التحويل من المحفوظات
{b}`{cmd}ايقاف التحويل`{e} — إيقاف التحويل
{b}`{cmd}ديلاي`{e} — ضبط زمن التحويل""",
        "م11": """{header_opa امر البروفايل}

{b}`{cmd}تغيير اسم`{e} — تغيير اسمك
{b}`{cmd}تغيير بايو`{e} — تغيير نبذتك
{b}`{cmd}تغيير صورة`{e} — بالرد لتغيير صورتك
{b}`{cmd}حسابي`{e} — عرض معلومات حسابك
{b}`{cmd}انتحال`{e} — انتحال هوية شخص (اسم + صورة + بايو)""",
    "م12": """{header_opa امر الصيغ}

{b}`{cmd}ملصق`{e} — بالرد على صورة لتحويلها ملصق
{b}`{cmd}صورة`{e} — بالرد على ملصق لتحويله صورة
{b}`{cmd}صوت`{e} — بالرد على مقطع لتحويله بصمة صوت""",
    "م13": """{header_opa امر التسليه}

{b}`{cmd}نسبة الحب`{e} — عرض نسبة الحب
{b}`{cmd}نسبة الغباء`{e} — عرض نسبة الغباء
{b}`{cmd}قلوب`{e} — عرض قلوب متحركة
{b}`{cmd}عد`{e} — العد التنازلي
{b}`{cmd}نرد`{e} — رمي النرد""",
    "م14": """{header_opa امر التحكم}

{b}`{cmd}التحكم تشغيل`{e} — تفعيل تحكم مستخدمين آخرين
{b}`{cmd}التحكم تعطيل`{e} — تعطيل التحكم
{b}`{cmd}اضف متحكم`{e} — بالرد لإضافة متحكم
{b}`{cmd}ازالة متحكم`{e} — بالرد لإزالة متحكم
{b}`{cmd}المتحكمين`{e} — عرض المتحكمين""",
    "م15": """{header_opa امر الذكاء الاصطناعي}

{b}`{cmd}ذكاء`{e} — محادثة تفاعلية + تنفيذ أدوات
{b}`{cmd}ذكاء مفعل`{e} — تفعيل الوضع الشامل
{b}`{cmd}ذكاء تشغيل`{e} — رد تلقائي بالخاص
{b}`{cmd}ذكاء تعطيل`{e} — إيقاف الرد التلقائي
{b}`{cmd}ذكاء سياق`{e} — عدد رسائل السياق
{b}`{cmd}ذكاء ذاكرة`{e} — عرض/مسح الذاكرة
{b}`{cmd}ذكاء جلسة`{e} — عرض/مسح جلسة المحادثة
{b}`{cmd}دليل الذكاء`{e} — توليد دليل السورس
{b}`{cmd}ادوات الذكاء`{e} — عرض الأدوات
{b}`{cmd}تعليمات الذكاء`{e} — عرض/تعديل التعليمات""",
    "م16": """{header_opa امر التحديثات}

{b}`{cmd}تحديث`{e} — تنزيل آخر تحديث وإعادة التشغيل
{b}`{cmd}تحديثات`{e} — عرض آخر التحديثات
{b}`{cmd}اخر_تحديث`{e} — عرض آخر إصدار منشور""",
    "م17": """{header_opa امر الفحص والبلاغات}

{b}`{cmd}فحص`{e} — فحص قناة/حساب
{b}`{cmd}فحص_دفعه`{e} — فحص رابط دعوة
{b}`{cmd}فحص_مجموعه`{e} — فحص المجموعة الحالية
{b}`{cmd}شد_هدف`{e} — ضبط هدف البلاغ
{b}`{cmd}شد_نوع`{e} — نوع البلاغ
{b}`{cmd}شد_رساله`{e} — نص البلاغ
{b}`{cmd}شد_سرعه`{e} — التأخير بين البلاغات
{b}`{cmd}شد`{e} — بدء بلاغ مستمر
{b}`{cmd}شد_ايقاف`{e} — إيقاف البلاغ
{b}`{cmd}شد_اعداد`{e} — عرض الإعدادات""",
    "م18": """{header_opa امر الاسم الوقتي}

{b}`{cmd}وقتي`{e} — عرض الحالة والمعاينة والتوقيت
{b}`{cmd}وقتي تشغيل`{e} — يفعّل التحديث كل دقيقة
{b}`{cmd}وقتي ايقاف`{e} — يوقفه
{b}`{cmd}وقتي شكل`{e} — يختار شكل زخرفة الأرقام
{b}`{cmd}وقتي توقيت`{e} — يختار التوقيت""",
    "م19": """{header_opa امر محوّل الصوت}

{b}`{cmd}صوتي`{e} — عرض قائمة التأثيرات
{b}`{cmd}صوتي`{e} — بالرد على مقطع لتطبيق التأثير
{b}`{cmd}صوتي سجل`{e} — التسجيل في خادم الصوت""",
    "م20": """{header_opa امر الكتم}

{b}`{cmd}كتم`{e} — لكتم شخص تُحذف رسائله تلقائياً
{b}`{cmd}الغاء كتم`{e} — لفك كتم شخص
{b}`{cmd}المكتومين`{e} — عرض قائمة المكتومين
{b}`{cmd}مسح كل المكتومين`{e} — فك كتم الجميع""",
    "م21": """{header_opa امر التفليش}

{b}`{cmd}تفليش`{e} — مسح الأعضاء عبر API مباشر
{b}`{cmd}تفلش`{e} — مسح الأعضاء عبر بوت (بالآيدي)
{b}`{cmd}تفلش2`{e} — مسح الأعضاء عبر بوت (باليوزر)
{b}`{cmd}وقف`{e} — إيقاف عملية التفليش""",
    "م22": """{header_opa امر التحميل}

{b}`{cmd}تيك`{e} — تحميل من تيك توك (فيديو/صورة/مزيكا)
{b}`{cmd}يوت`{e} — بحث في يوتيوب وتحميل الأغنية MP3""",


        "م23": """{header_opa اوامر النشر التلقائي}

⚠️ **تنبيه هام:**
النشر التلقائي على مسؤوليتك الشخصية. قد يعرض حسابك للحظر بسبب سياسة تيليجرام.
يُفضل تفعيله بوقت طويل (30 دقيقة أو أكثر) ولعدد قليل من المجموعات (أقل من 10).

{b}`{cmd}المجموعات`{e} — عرض كل مجموعاتك بالأرقام
{b}`{cmd}اضف 1 2 3`{e} — أضف مجموعات بالأرقام
{b}`{cmd}اضف الكل`{e} — أضف جميع المجموعات
{b}`{cmd}حذف 1 2`{e} — احذف مجموعات بالأرقام
{b}`{cmd}حذف الكل`{e} — احذف جميع المجموعات المضافة
{b}`{cmd}مجموعاتي`{e} — عرض المجموعات المضافة (مرقمة)
{b}`{cmd}تعيين رساله`{e} — بالرد لتعيين الرسالة
{b}`{cmd}الرساله`{e} — عرض الرسالة الحالية
{b}`{cmd}مسح الرساله`{e} — مسح الرسالة
{b}`{cmd}وقت النشر`{e} — ضبط وقت الإعادة بالدقائق
{b}`{cmd}بدء النشر`{e} — بدء النشر التلقائي
{b}`{cmd}ايقاف النشر`{e} — إيقاف النشر
{b}`{cmd}حالة النشر`{e} — عرض الحالة والإحصائيات""",
        "م24": """{header_opa اوامر حفظ المؤقتة}

{b}`{cmd}حفظ المؤقتة`{e} — عرض الحالة والشرح
{b}`{cmd}تشغيل حفظ المؤقتة`{e} — تشغيل حفظ المؤقتة
{b}`{cmd}تعطيل حفظ المؤقتة`{e} — تعطيل حفظ المؤقتة
""",}
@cmd(r"الاوامر$")
async def _(event):
    await edit_or_reply(event, MENU_MAIN)


for _sec, _txt in MENU.items():
    def _make(txt):
        async def handler(event):
            await edit_or_reply(event, _fmt_section(txt))
        return handler
    client.add_event_handler(
        _make(_txt),
        events.NewMessage(pattern=re.compile("^\\" + PREFIX + _sec + "$"), outgoing=True),
    )
    client.add_event_handler(
        _make(_txt),
        events.MessageEdited(pattern=re.compile("^\\" + PREFIX + _sec + "$"), outgoing=True),
    )



BAN_RIGHTS = ChatBannedRights(until_date=None, view_messages=True)
UNBAN_RIGHTS = ChatBannedRights(
    until_date=None, view_messages=False, send_messages=False,
    send_media=False, send_stickers=False, send_gifs=False,
    send_games=False, send_inline=False, embed_links=False,
)
MUTE_RIGHTS = ChatBannedRights(until_date=None, send_messages=True)
UNMUTE_RIGHTS = ChatBannedRights(until_date=None, send_messages=False)


@cmd(r"حظر(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    try:
        await event.client(EditBannedRequest(event.chat_id, uid, BAN_RIGHTS))
    except Exception as e:
        return await edit_delete(event, f"- تعذر الحظر: `{e}`", 8)
    await edit_or_reply(event, f"تم حظر {mention(user)} ✓")


@cmd(r"الغاء حظر(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    try:
        await event.client(EditBannedRequest(event.chat_id, uid, UNBAN_RIGHTS))
    except Exception as e:
        return await edit_delete(event, f"- تعذر فك الحظر: `{e}`", 8)
    await edit_or_reply(event, f"تم فك حظر {mention(user)} ✓")


def _mutes_read():
    return db_read("mutes", {})


def _mutes_write(data):
    db_write("mutes", data)


def _muted_global_ids():
    return set(int(k) for k in _mutes_read().keys())


@cmd(r"كتم(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    data = _mutes_read()
    data[str(uid)] = get_display_name(user)
    _mutes_write(data)
    await edit_or_reply(event, f"تم كتم {mention(user)} — ستُحذف رسائله في كل الأماكن ✓")


@cmd(r"الغاء كتم(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    data = _mutes_read()
    if str(uid) in data:
        del data[str(uid)]
        _mutes_write(data)
        await edit_or_reply(event, f"تم فك كتم {mention(user)} ✓")
    else:
        await edit_delete(event, "- هذا الشخص ليس مكتوماً", 8)


@cmd(r"المكتومين$")
async def _(event):
    data = _mutes_read()
    if not data:
        return await edit_or_reply(event, "- لا يوجد مكتومون")
    lines = []
    for uid, name in data.items():
        lines.append(f"• {name} — `{uid}`")
    await edit_or_reply(event, "**| المكتومون (تُحذف رسائلهم في كل الأماكن):**\n\n" + "\n".join(lines))


@cmd(r"مسح كل المكتومين$")
async def _(event):
    _mutes_write({})
    await edit_or_reply(event, "تم فك كتم جميع المكتومين ✓")


@client.on(events.NewMessage(incoming=True))
async def _mutes_watcher(event):
    if not event.sender_id:
        return
    if event.sender_id in _muted_global_ids():
        try:
            await event.delete()
        except Exception:
            pass


@cmd(r"طرد(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    try:
        await event.client.kick_participant(event.chat_id, uid)
    except Exception as e:
        return await edit_delete(event, f"- تعذر الطرد: `{e}`", 8)
    await edit_or_reply(event, f"تم طرد {mention(user)} ✓")


@cmd(r"رفع مشرف(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    reply = await event.get_reply_message()
    title = OWNER_NAME
    args = event.pattern_match.group(1)
    uid = None
    if reply:
        uid = reply.sender_id
        if args and args.strip():
            title = args.strip()
    elif args and args.strip():
        parts = args.strip().split(maxsplit=1)
        try:
            uid = (await event.client.get_entity(parts[0])).id
        except Exception:
            return await edit_delete(event, "- لم أجد المستخدم", 8)
        if len(parts) > 1:
            title = parts[1]
    if not uid:
        return await edit_delete(event, "- رد على شخص لرفعه", 8)
    rights = ChatAdminRights(
        change_info=True, post_messages=True, edit_messages=True,
        delete_messages=True, ban_users=True, invite_users=True,
        pin_messages=True, add_admins=False, manage_call=True,
    )
    try:
        await event.client(EditAdminRequest(event.chat_id, uid, rights, title[:16]))
    except Exception as e:
        return await edit_delete(event, f"- تعذر الرفع: `{e}`", 8)
    user, _ = await get_target_user(event)
    await edit_or_reply(event, f"تم رفع {mention(user)} مشرفاً ✓")


@cmd(r"تنزيل مشرف(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    rights = ChatAdminRights(
        change_info=False, post_messages=False, edit_messages=False,
        delete_messages=False, ban_users=False, invite_users=False,
        pin_messages=False, add_admins=False,
    )
    try:
        await event.client(EditAdminRequest(event.chat_id, uid, rights, ""))
    except Exception as e:
        return await edit_delete(event, f"- تعذر التنزيل: `{e}`", 8)
    await edit_or_reply(event, f"تم تنزيل {mention(user)} من الإشراف ✓")


@cmd(r"تثبيت$", groups_only=True)
async def _(event):
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(event, "- رد على رسالة لتثبيتها", 8)
    try:
        await event.client.pin_message(event.chat_id, reply.id, notify=True)
    except Exception as e:
        return await edit_delete(event, f"- تعذر التثبيت: `{e}`", 8)
    await edit_delete(event, "تم التثبيت ✓", 5)


@cmd(r"الغاء تثبيت$", groups_only=True)
async def _(event):
    reply = await event.get_reply_message()
    try:
        if reply:
            await event.client.unpin_message(event.chat_id, reply.id)
        else:
            await event.client.unpin_message(event.chat_id)
    except Exception as e:
        return await edit_delete(event, f"- تعذر الإلغاء: `{e}`", 8)
    await edit_delete(event, "تم إلغاء التثبيت ✓", 5)


@cmd(r"مسح(?:\s|$)(?!كل محدد)([\s\S]*)", groups_only=True)
async def _(event):
    reply = await event.get_reply_message()
    args = event.pattern_match.group(1)
    count = 0
    if reply:
        msgs = []
        async for msg in event.client.iter_messages(
            event.chat_id, min_id=reply.id - 1, reverse=True
        ):
            msgs.append(msg.id)
            if len(msgs) >= 500:
                break
        if msgs:
            await event.client.delete_messages(event.chat_id, msgs)
            count = len(msgs)
    elif args and args.strip().isdigit():
        n = int(args.strip())
        msgs = []
        async for msg in event.client.iter_messages(event.chat_id, limit=n + 1):
            msgs.append(msg.id)
        if msgs:
            await event.client.delete_messages(event.chat_id, msgs)
            count = len(msgs)
    else:
        return await edit_delete(event, "- رد على رسالة أو ضع عدداً", 8)
    m = await event.client.send_message(event.chat_id, f"تم حذف {count} رسالة ✓")
    await asyncio.sleep(4)
    await m.delete()


@cmd(r"تحذير(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص لتحذيره", 8)
    key = f"{event.chat_id}"
    warns = db_read("warns")
    chat = warns.get(key, {})
    chat[str(uid)] = chat.get(str(uid), 0) + 1
    warns[key] = chat
    db_write("warns", warns)
    n = chat[str(uid)]
    text = f"تم تحذير {mention(user)}\nعدد التحذيرات: {n}/3"
    if n >= 3:
        try:
            await event.client(EditBannedRequest(event.chat_id, uid, MUTE_RIGHTS))
            text += "\nتم كتمه لتجاوزه الحد ✓"
        except Exception:
            pass
        chat[str(uid)] = 0
        warns[key] = chat
        db_write("warns", warns)
    await edit_or_reply(event, text)


@cmd(r"التحذيرات(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص", 8)
    n = db_read("warns").get(f"{event.chat_id}", {}).get(str(uid), 0)
    await edit_or_reply(event, f"تحذيرات {mention(user)}: {n}/3")


@cmd(r"حذف التحذيرات(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص", 8)
    warns = db_read("warns")
    key = f"{event.chat_id}"
    if key in warns and str(uid) in warns[key]:
        warns[key][str(uid)] = 0
        db_write("warns", warns)
    await edit_or_reply(event, f"تم حذف تحذيرات {mention(user)} ✓")




@cmd(r"الايدي(?:\s|$)([\s\S]*)")
async def _(event):
    args = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    if args and args.strip():
        try:
            p = await event.client.get_entity(args.strip())
        except Exception as e:
            return await edit_delete(event, f"`{e}`", 6)
        name = getattr(p, "title", None) or get_display_name(p)
        return await edit_or_reply(event, f"ايدي `{name}` هو `{p.id}`")
    if reply:
        txt = f"**ايدي الدردشة:** `{event.chat_id}`\n**ايدي المرسل:** `{reply.sender_id}`"
        if reply.media:
            txt += "\n**نوع:** ميديا"
        return await edit_or_reply(event, txt)
    await edit_or_reply(event, f"**ايدي الدردشة:** `{event.chat_id}`")


@cmd(r"كشف(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not user:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    txt = f"""**| كشف المستخدم :**
**الاسم:** {get_display_name(user)}
**الايدي:** `{user.id}`
**المعرف:** @{user.username if user.username else 'لا يوجد'}
**بوت:** {'نعم' if user.bot else 'لا'}
**مقيد:** {'نعم' if getattr(user, 'restricted', False) else 'لا'}
**الرابط:** [هنا](tg://user?id={user.id})"""
    await edit_or_reply(event, txt)


_ID_DATES = [
    (1, 1376448000), (1000000, 1383264000), (5000000, 1384905600),
    (10000000, 1389744000), (50000000, 1404950400), (100000000, 1425513600),
    (200000000, 1462060800), (500000000, 1515542400), (1000000000, 1573776000),
    (1500000000, 1604188800), (2000000000, 1634256000), (2500000000, 1648771200),
    (3000000000, 1663200000), (3500000000, 1675209600), (4000000000, 1688169600),
    (4500000000, 1701388800), (5000000000, 1714521600), (5500000000, 1727740800),
    (6000000000, 1740787200), (8956099155, 1750958248),
]


def _now_date():
    return datetime.now().strftime("%Y-%m-%d")


def _estimate_id_date(uid):
    pts = sorted(_ID_DATES, key=lambda x: x[0])
    for pid, ptime in pts:
        if uid == pid:
            dt = datetime.fromtimestamp(ptime)
            return (dt.strftime("%Y-%m-%d"), "ضبط") if dt <= datetime.now() else (_now_date(), "جديد")
    if uid < pts[0][0]:
        return datetime.fromtimestamp(pts[0][1]).strftime("%Y-%m-%d"), "قديم"
    if uid > pts[-1][0]:
        return _now_date(), "جديد"
    for i in range(len(pts) - 1):
        if pts[i][0] < uid < pts[i + 1][0]:
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            frac = (uid - x0) / (x1 - x0) if x1 != x0 else 0
            ts = y0 + (y1 - y0) * frac
            dt = datetime.fromtimestamp(ts)
            if dt > datetime.now():
                return _now_date(), "جديد"
            return dt.strftime("%Y-%m-%d"), "aprox"
    return _now_date(), "جديد"


def _flag_from_country(code):
    if not code or len(code) != 2:
        return ""
    return chr(0x1F1E6 + ord(code[0]) - 65) + chr(0x1F1E6 + ord(code[1]) - 65)


@cmd(r"انشاء(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not user:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    m = await event.edit("- جاري جلب المعلومات...")
    try:
        result = await client(functions.users.GetFullUserRequest(user))
        settings = result.settings
    except Exception:
        settings = None
    reg = getattr(settings, "registration_month", None) if settings else None
    country_code = getattr(settings, "phone_country", None) if settings else None
    flag = _flag_from_country(country_code) if country_code else ""
    est_date, est_status = _estimate_id_date(user.id)
    lines = [f"• تاريخ الانشاء هو"]
    lines.append(f"• {est_date} ({est_status})")
    if country_code:
        lines.append(f"• دولة: {flag} {country_code}")
    await edit_or_reply(m, "\n".join(lines))


@cmd(r"صورة(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not user:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)
    m = await event.edit("- جاري الجلب...")
    try:
        photo = await event.client.download_profile_photo(user.id)
        if not photo:
            return await edit_delete(event, "- لا يوجد صورة", 6)
        await event.client.send_file(
            event.chat_id, photo, caption=f"صورة {mention(user)}"
        )
        os.remove(photo)
        await m.delete()
    except Exception as e:
        await edit_delete(event, f"`{e}`", 6)


@cmd(r"المشرفين$", groups_only=True)
async def _(event):
    admins = []
    async for u in event.client.iter_participants(
        event.chat_id, filter=types.ChannelParticipantsAdmins
    ):
        admins.append(f"• {mention(u)} — `{u.id}`")
    txt = "**| مشرفو المجموعة :**\n\n" + "\n".join(admins)
    await edit_or_reply(event, txt)


@cmd(r"الاعضاء$", groups_only=True)
async def _(event):
    chat = await event.get_chat()
    full = await event.client.get_participants(event.chat_id, limit=0)
    await edit_or_reply(
        event, f"**عدد أعضاء** {chat.title}: `{full.total}`"
    )


@cmd(r"البوتات$", groups_only=True)
async def _(event):
    bots = []
    async for u in event.client.iter_participants(event.chat_id):
        if u.bot:
            bots.append(f"• {mention(u)} — `{u.id}`")
    if not bots:
        return await edit_or_reply(event, "- لا يوجد بوتات في هذه المجموعة")
    await edit_or_reply(event, "**| البوتات :**\n\n" + "\n".join(bots))


@cmd(r"معلومات$", groups_only=True)
async def _(event):
    chat = await event.get_chat()
    full = await event.client.get_participants(event.chat_id, limit=0)
    txt = f"""**| معلومات المجموعة :**
**الاسم:** {chat.title}
**الايدي:** `{event.chat_id}`
**عدد الأعضاء:** `{full.total}`
**المعرف:** @{chat.username if getattr(chat, 'username', None) else 'خاصة'}"""
    await edit_or_reply(event, txt)




@cmd(r"اضف رد(?:\s|$)([\s\S]*)")
async def _(event):
    reply = await event.get_reply_message()
    word = event.pattern_match.group(1)
    if not reply or not word or not word.strip():
        return await edit_delete(event, "- رد على النص واكتب: اضف رد <الكلمة>", 8)
    if not reply.text:
        return await edit_delete(event, "- الرد يجب أن يكون نصاً", 8)
    db_set("replies", word.strip(), reply.text)
    await edit_or_reply(event, f"تم إضافة رد على: `{word.strip()}` ✓")


@cmd(r"حذف رد(?:\s|$)([\s\S]*)")
async def _(event):
    word = event.pattern_match.group(1)
    if not word or not word.strip():
        return await edit_delete(event, "- اكتب: حذف رد <الكلمة>", 8)
    if db_del("replies", word.strip()):
        await edit_or_reply(event, f"تم حذف الرد: `{word.strip()}` ✓")
    else:
        await edit_delete(event, "- لا يوجد رد بهذا الاسم", 8)


@cmd(r"الردود$")
async def _(event):
    data = db_read("replies")
    if not data:
        return await edit_or_reply(event, "- لا يوجد ردود مضافة")
    txt = "**| الردود المضافة :**\n\n" + "\n".join(f"• `{k}`" for k in data)
    await edit_or_reply(event, txt)


@cmd(r"مسح الردود$")
async def _(event):
    db_write("replies", {})
    await edit_or_reply(event, "تم حذف جميع الردود ✓")


@client.on(events.NewMessage(incoming=True))
async def _replies_watcher(event):
    if not event.text:
        return
    data = db_read("replies")
    if not data:
        return
    reply = data.get(event.raw_text.strip())
    if reply:
        try:
            await event.reply(reply)
        except Exception:
            pass




@cmd(r"ضبط ترحيب(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    text = event.pattern_match.group(1)
    if not text or not text.strip():
        return await edit_delete(event, "- اكتب نص الترحيب بعد الأمر", 8)
    db_set("welcome", event.chat_id, text.strip())
    await edit_or_reply(event, "تم ضبط رسالة الترحيب ✓")


@cmd(r"الترحيب$", groups_only=True)
async def _(event):
    w = db_get("welcome", event.chat_id)
    if not w:
        return await edit_or_reply(event, "- لا يوجد ترحيب مضبوط")
    await edit_or_reply(event, f"**الترحيب الحالي:**\n\n{w}")


@cmd(r"حذف الترحيب$", groups_only=True)
async def _(event):
    if db_del("welcome", event.chat_id):
        await edit_or_reply(event, "تم حذف الترحيب ✓")
    else:
        await edit_or_reply(event, "- لا يوجد ترحيب أصلاً")


@client.on(events.ChatAction)
async def _welcome_watcher(event):
    if not (event.user_joined or event.user_added):
        return
    w = db_get("welcome", event.chat_id)
    if not w:
        return
    try:
        user = await event.get_user()
        chat = await event.get_chat()
        count = (await event.client.get_participants(event.chat_id, limit=0)).total
        msg = w.replace("{name}", get_display_name(user))
        msg = msg.replace("{title}", chat.title)
        msg = msg.replace("{count}", str(count))
        await event.client.send_message(event.chat_id, msg)
    except Exception:
        pass




@cmd(r"منع(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    word = event.pattern_match.group(1)
    if not word or not word.strip():
        return await edit_delete(event, "- اكتب: منع <الكلمة>", 8)
    data = db_read("locked")
    key = f"{event.chat_id}"
    words = data.get(key, [])
    if word.strip() not in words:
        words.append(word.strip())
    data[key] = words
    db_write("locked", data)
    await edit_or_reply(event, f"تم منع الكلمة: `{word.strip()}` ✓")


@cmd(r"الغاء منع(?:\s|$)([\s\S]*)", groups_only=True)
async def _(event):
    word = event.pattern_match.group(1)
    if not word or not word.strip():
        return await edit_delete(event, "- اكتب: الغاء منع <الكلمة>", 8)
    data = db_read("locked")
    key = f"{event.chat_id}"
    words = data.get(key, [])
    if word.strip() in words:
        words.remove(word.strip())
        data[key] = words
        db_write("locked", data)
        await edit_or_reply(event, f"تم إلغاء منع: `{word.strip()}` ✓")
    else:
        await edit_delete(event, "- الكلمة غير ممنوعة", 8)


@cmd(r"قائمة المنع$", groups_only=True)
async def _(event):
    words = db_read("locked").get(f"{event.chat_id}", [])
    if not words:
        return await edit_or_reply(event, "- لا يوجد كلمات ممنوعة")
    txt = "**| الكلمات الممنوعة :**\n\n" + "\n".join(f"• `{w}`" for w in words)
    await edit_or_reply(event, txt)


@client.on(events.NewMessage(incoming=True))
async def _locked_watcher(event):
    if not event.text or not event.is_group:
        return
    words = db_read("locked").get(f"{event.chat_id}", [])
    if not words:
        return
    low = event.raw_text.lower()
    if any(w.lower() in low for w in words):
        try:
            await event.delete()
        except Exception:
            pass



PM_WARN_TEXT = (
    f"**| حماية الخاص — سورس الجوكر**\n\n"
    "هذا حساب محمي، انتظر موافقة صاحب الحساب.\n"
    "تكرار الرسائل سيؤدي لحظرك."
)
PM_LIMIT = 5


@cmd(r"الحماية تشغيل$")
async def _(event):
    db_set("settings", "pmpermit", True)
    await edit_or_reply(event, "تم تشغيل حماية الخاص ✓")


@cmd(r"الحماية تعطيل$")
async def _(event):
    db_set("settings", "pmpermit", False)
    await edit_or_reply(event, "تم تعطيل حماية الخاص ✓")


@cmd(r"سماح(?:\s|$)([\s\S]*)", private_only=True)
async def _(event):
    uid = event.chat_id
    allowed = db_read("pm_allowed")
    allowed[str(uid)] = True
    db_write("pm_allowed", allowed)
    counts = db_read("pm_counts")
    counts.pop(str(uid), None)
    db_write("pm_counts", counts)
    await edit_or_reply(event, "تم السماح لهذا الشخص بالخاص ✓")


@cmd(r"رفض(?:\s|$)([\s\S]*)", private_only=True)
async def _(event):
    uid = event.chat_id
    allowed = db_read("pm_allowed")
    allowed.pop(str(uid), None)
    db_write("pm_allowed", allowed)
    await edit_or_reply(event, "تم رفض هذا الشخص من الخاص ✓")


@cmd(r"المسموحين$")
async def _(event):
    allowed = db_read("pm_allowed")
    if not allowed:
        return await edit_or_reply(event, "- لا يوجد مسموح لهم")
    txt = "**| المسموح لهم بالخاص :**\n\n" + "\n".join(
        f"• `{k}`" for k in allowed
    )
    await edit_or_reply(event, txt)


@client.on(events.NewMessage(incoming=True))
async def _pmpermit_watcher(event):
    if not event.is_private:
        return
    if not db_get("settings", "pmpermit", False):
        return
    sender = await event.get_sender()
    if sender is None or sender.bot or getattr(sender, "verified", False):
        return
    if event.chat_id == (await event.client.get_me()).id:
        return
    uid = str(event.chat_id)
    if db_read("pm_allowed").get(uid):
        return
    if getattr(sender, "is_self", False):
        return
    contact = getattr(sender, "contact", False)
    if contact:
        return
    counts = db_read("pm_counts")
    n = counts.get(uid, 0) + 1
    counts[uid] = n
    db_write("pm_counts", counts)
    if n >= PM_LIMIT:
        try:
            await event.client(BlockRequest(event.chat_id))
            await event.respond("تم حظرك لتكرار الرسائل.")
        except Exception:
            pass
        counts.pop(uid, None)
        db_write("pm_counts", counts)
        return
    try:
        await event.respond(f"{PM_WARN_TEXT}\n\nتحذير {n}/{PM_LIMIT}")
    except Exception:
        pass




@cmd(r"للكروبات(?:\s|$)([\s\S]*)")
async def _(event):
    reply = await event.get_reply_message()
    text = event.pattern_match.group(1)
    if not reply and not (text and text.strip()):
        return await edit_delete(event, "- اكتب نصاً أو رد على رسالة", 8)
    m = await event.edit("- جاري النشر بالمجموعات...")
    done, failed = 0, 0
    async for dialog in event.client.iter_dialogs():
        if dialog.is_group:
            try:
                if reply:
                    await event.client.send_message(dialog.id, reply)
                else:
                    await event.client.send_message(dialog.id, text.strip())
                done += 1
                await asyncio.sleep(0.5)
            except Exception:
                failed += 1
    await m.edit(f"تم النشر ✓\nنجح: {done} | فشل: {failed}")


@cmd(r"للخاص(?:\s|$)([\s\S]*)")
async def _(event):
    reply = await event.get_reply_message()
    text = event.pattern_match.group(1)
    if not reply and not (text and text.strip()):
        return await edit_delete(event, "- اكتب نصاً أو رد على رسالة", 8)
    m = await event.edit("- جاري النشر بالخاص...")
    done, failed = 0, 0
    async for dialog in event.client.iter_dialogs():
        if dialog.is_user and not dialog.entity.bot:
            try:
                if reply:
                    await event.client.send_message(dialog.id, reply)
                else:
                    await event.client.send_message(dialog.id, text.strip())
                done += 1
                await asyncio.sleep(0.5)
            except Exception:
                failed += 1
    await m.edit(f"تم النشر ✓\nنجح: {done} | فشل: {failed}")




@cmd(r"بنك$")
async def _(event):
    start = time.time()
    m = await event.edit("...")
    ms = (time.time() - start) * 1000
    await m.edit(f"**السرعة:** `{ms:.2f}` ms")


@cmd(r"الوقت$")
async def _(event):
    up = readable_time(time.time() - START_TIME)
    await edit_or_reply(event, f"**مدة التشغيل:** {up}")


@cmd(r"اعادة تشغيل$")
async def _(event):
    await event.edit("- جاري إعادة التشغيل...")
    db_set("settings", "restart_chat", event.chat_id)
    db_set("settings", "restart_msg", event.id)
    await event.client.disconnect()
    os.execl(sys.executable, sys.executable, os.path.abspath(__file__))




@cmd(r"تغيير اسم(?:\s|$)([\s\S]*)")
async def _(event):
    name = event.pattern_match.group(1)
    if not name or not name.strip():
        return await edit_delete(event, "- اكتب الاسم بعد الأمر", 8)
    parts = name.strip().split(maxsplit=1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    try:
        await event.client(
            functions.account.UpdateProfileRequest(
                first_name=first, last_name=last
            )
        )
    except Exception as e:
        return await edit_delete(event, f"`{e}`", 8)
    await edit_or_reply(event, "تم تغيير الاسم ✓")


@cmd(r"تغيير بايو(?:\s|$)([\s\S]*)")
async def _(event):
    bio = event.pattern_match.group(1)
    if not bio or not bio.strip():
        return await edit_delete(event, "- اكتب البايو بعد الأمر", 8)
    try:
        await event.client(
            functions.account.UpdateProfileRequest(about=bio.strip())
        )
    except Exception as e:
        return await edit_delete(event, f"`{e}`", 8)
    await edit_or_reply(event, "تم تغيير البايو ✓")


@cmd(r"تغيير صورة$")
async def _(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        return await edit_delete(event, "- رد على صورة", 8)
    m = await event.edit("- جاري التغيير...")
    try:
        photo = await event.client.download_media(reply.media)
        up = await event.client.upload_file(photo)
        await event.client(functions.photos.UploadProfilePhotoRequest(file=up))
        os.remove(photo)
        await m.edit("تم تغيير الصورة ✓")
    except Exception as e:
        await m.edit(f"`{e}`")


@cmd(r"حسابي$")
async def _(event):
    me = await event.client.get_me()
    txt = f"""**| معلومات حسابك :**
**الاسم:** {get_display_name(me)}
**الايدي:** `{me.id}`
**المعرف:** @{me.username if me.username else 'لا يوجد'}
**الرقم:** `+{me.phone if me.phone else 'مخفي'}`
**بريميوم:** {'نعم' if getattr(me, 'premium', False) else 'لا'}"""
    await edit_or_reply(event, txt)


@cmd(r"انتحال(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not user:
        return await edit_delete(event, "- رد على شخص أو ضع معرفه", 8)

    m = await event.edit("🎭 جاري سحب بيانات الهدف...")

    # 1. جلب الاسم
    first_name = (getattr(user, "first_name", "") or "").strip()
    last_name = (getattr(user, "last_name", "") or "").strip()
    if not first_name:
        return await edit_or_reply(m, "❌ الهدف ليس لديه اسم")

    # 2. جلب البايو
    bio = ""
    try:
        full = await client(functions.users.GetFullUserRequest(user))
        full_user = getattr(full, "full_user", None)
        if full_user:
            bio = getattr(full_user, "about", "") or ""
    except Exception as e:
        print(f"[impersonate] bio: {e}")

    # 3. سحب الصورة
    await m.edit("🖼️ جاري سحب الصورة...")
    photo_path = None
    try:
        photo_path = await client.download_profile_photo(
            user, file=os.path.join(tempfile.gettempdir(), f"imp_{int(time.time())}.jpg")
        )
    except Exception as e:
        print(f"[impersonate] download photo: {e}")

    # 4. تحديث الاسم والبايو
    await m.edit("✏️ جاري تحديث الاسم والبايو...")
    try:
        await client(functions.account.UpdateProfileRequest(
            first_name=first_name[:64],
            last_name=last_name[:64],
            about=bio[:70] if bio else "",
        ))
    except Exception as e:
        return await edit_or_reply(m, f"❌ فشل تحديث الاسم/البايو: `{e}`")

    # 5. تحديث الصورة
    photo_updated = False
    if photo_path and os.path.exists(photo_path):
        await m.edit("📸 جاري تحديث الصورة...")
        try:
            try:
                photos = await client(functions.photos.GetUserPhotosRequest(
                    user_id=types.InputUserSelf(),
                    offset=0,
                    max_id=0,
                    limit=100,
                ))
                if photos.photos:
                    await client(functions.photos.DeletePhotosRequest(id=photos.photos)
                    )
            except Exception as e:
                print(f"[impersonate] delete old photos: {e}")

            uploaded = await client.upload_file(photo_path)
            await client(functions.photos.UploadProfilePhotoRequest(file=uploaded))
            photo_updated = True
        except Exception as e:
            print(f"[impersonate] upload photo: {e}")
        finally:
            try:
                os.remove(photo_path)
            except Exception:
                pass

    # 6. النتيجة
    status = f"✅ تم انتحال شخصية {mention(user)} بنجاح\n\n"
    status += f"👤 **الاسم:** {first_name} {last_name}\n"
    status += f"📝 **البايو:** {bio[:60] + '...' if len(bio) > 60 else (bio or 'فارغ')}\n"
    status += f"🖼️ **الصورة:** {'محدثة ✓' if photo_updated else 'لم تُحدث ❌'}"

    await edit_or_reply(m, status)

@cmd(r"ترجمة(?:\s|$)([\s\S]*)")
async def _(event):
    reply = await event.get_reply_message()
    arg = event.pattern_match.group(1)
    lang = (arg.strip() or "ar") if arg else "ar"
    if reply and reply.text:
        text = reply.text
    elif arg and len(arg.strip().split(maxsplit=1)) > 1:
        lang, text = arg.strip().split(maxsplit=1)
    else:
        return await edit_delete(event, "- رد على نص | مثال: ترجمة en", 8)
    try:
        from googletrans import Translator
        tr = Translator()
        res = tr.translate(text, dest=lang)
        await edit_or_reply(
            event, f"**الترجمة ({res.src} | {lang}):**\n\n{res.text}"
        )
    except Exception as e:
        await edit_delete(event, f"- تعذر الترجمة (ثبّت googletrans): `{e}`", 10)



spam_targets = {}
spam_delay_min = 3.0
spam_delay_max = 5.0
spam_batch_min = 1
spam_batch_max = 1
spam_ai_enabled = False
spam_ai_target = ""
follow_running = False
forward_running = False
forward_task = None
forward_delay_min = 0.5
forward_delay_max = 0.5
selected_saved_msgs = []
flood_guard_enabled = False
flood_guard = None


_DEFAULT_INSULTS = {
    "sakhira": [
        "انت تمشي على موال الي يرفع رجلين اختك تكعد تمجد بيه لو شلون؟",
        "من كثر ما انت ذليل صرت تعتبر رفع رجلين عرضك انجاز تفتخر بيه",
        "كل ما ضاكت عليك الدنيا تروح تنيج اهلك وترجع فرحان",
        "نجت اختك الي اسمها أيات خليتها من عيري تسوي اصوات نجت امك من بعد السبات نجتها بكل ثبات عيري بكسمك زرع نبات انيج امك واسوي بكسها شتات من كسها اسوي نهر الفرات انيجها وأسويلي من نيجها حالات انيجها واني كلي صفات من النيج بأمك اني سويت اضفت جهات انيج امك وأخليها تنطق كلمات اركبها وأضل فوكاها بالساعات","ابن الخاضعه وابن الراضعه وعلى عيري متواضعه", "انيج امك بل دربونه اعصربكسهه ليمونه", "انيج اختك بشارع فلسطين واخلي كسهه ينلاخ طين", "انيج امك بملعب برشلونه خلي اشوف كسهه اشونه", 
"لك ابن بلاعت العيورررره ابن الطيزون اطبب امك شارع الانبار والعب بديوسه الكبار","انييجك نيجه البعير واضربك بعير ستيل","نيجه الحمار شرط بلليل مو بلنهار","ابن التحكه عل رصيف خلي يطلع نضيف كول ماشي عمو تعال انيجك نيجه كوردية اخلك تحك من الصيف للشتوية","ابن التحكه عل مجمده وتكول مامتعمده","ابن الدودكيه ابن السحقايه افتح كس امك بديه وبرجليه","ابن التحكه عل مجمده وتكول مامتعمده","العب على كس اختك اقمار واسوي عليه حرب ودمار عمو عدي عير من الحله للكوت اذا اضربك بي تجي امك تشيله بالتابوت يله ابن السيته فيته ابن التجر العير من لحيته اجر على اختك السيفونه وهيه بنيجها كلش حنونه وطلع من كسها بزونه","لاتضل تهوبز وطوبزتره اشدك على سير النعال ودك بل بسطال من وره النقال","اضرب اختك عيرمنا للزبير وبي معزوفه اذا تشوفه متعوفه","العب على كس اختك اقمار واسوي عليه حرب ودمار عمو عدي عير من الحله للكوت اذا اضربك بي تجي امك تشيله بالتابوت يله ابن السيته فيته ابن التجر العير من لحيته اجر على اختك السيفونه وهيه بنيجها كلش حنونه","انيج اختك وره الباب وتكلي عله كيفك يابو الشباب","انيج اختك وره الباب وتكلي عله كيفك يابو الشباب واشوي عله كسهه تكه وكباب","انيج امك نيجة الحمير واخليه ادنك مثل البعير","اضرب اختك عيركركره اكراد وعرب مجره وتجي امك تعاتبني وتكول ليش نايج بتي اكوخاله كسهه عجبني هاك اخذهاه من عمك المدير وتنح وستدير تف ابلاع لاترجع هاذه رزقك ربك ولد المضغوطه وعله عيري محطوطه","\"انيج امك بل دربونه اعصربكسهه ليمونه\", \"انيج اختك بشارع فلسطين واخلي كسهه ينلاخ طين\", \"انيج امك بملعب برشلونه خلي اشوف كسهه اشونه\",","احط بكس امك موس وسجاجين انيج امك نيجت القرد واخليه تموت من البرد","انيج اختك بشارع فلسطين واخلي كسهه ينلاخ طين","انيج امك بملعب برشلونه خلي اشوف كسهه اشونه","\"ابن الخاضعه وابن الراضعه وعلى عيري متواضعه\","
    ],
    
}

INSULTS = {}




def _load_insults():
    """يحمّل مكتبة السب من data/insults.json، وينشئها افتراضياً إن لم توجد"""
    global INSULTS
    if not os.path.exists(_path("insults")):
        db_write("insults", _DEFAULT_INSULTS)
    data = db_read("insults", _DEFAULT_INSULTS)
    for k, v in _DEFAULT_INSULTS.items():
        data.setdefault(k, v)
    INSULTS = data


def insult_combos():
    """عدد الجمل المتاحة = عدد جمل sakhira"""
    return len(INSULTS.get("sakhira", []))


def generate_insult():
    """يختار جملة عشوائية من sakhira فقط"""
    if not INSULTS:
        _load_insults()
    sakhira = INSULTS.get("sakhira") or []
    if not sakhira:
        return "شنو هل الوجه؟"
    return random.choice(sakhira).strip()


class TextFloodGuard:
    """حماية من الفلود عبر token bucket + ضبط المعدل اللحظي"""

    def __init__(self, is_premium=False):
        self.is_premium = is_premium
        self.capacity = 40 if is_premium else 20
        self.refill_rate = 3.0 if is_premium else 1.0
        self.tokens = self.capacity
        self.last_update = time.time()
        self.total_sent = 0
        self.daily_limit = 30000 if is_premium else 15000
        self.last_send_times = []

    async def wait_if_needed(self):
        self.total_sent += 1
        now = time.time()
        self.tokens = min(
            self.capacity, self.tokens + (now - self.last_update) * self.refill_rate
        )
        self.last_update = now
        self.last_send_times = [t for t in self.last_send_times if now - t < 8]
        instant_rate = (
            len(self.last_send_times) / max(now - self.last_send_times[0], 1)
            if self.last_send_times
            else 0
        )
        self.last_send_times.append(now)
        if instant_rate > 2.0:
            wait = min(instant_rate * 1.5, 8)
            await asyncio.sleep(wait)
            self.last_send_times = []
        if self.tokens < 1:
            wait = min((1 - self.tokens) / self.refill_rate, 10)
            await asyncio.sleep(max(wait, 0.05))
            self.tokens = 1
        self.tokens -= 1

    def get_stats(self):
        now = time.time()
        recent = len([t for t in self.last_send_times if now - t < 8])
        rate = (
            recent / max(now - self.last_send_times[0], 1)
            if self.last_send_times
            else 0
        )
        return {
            "type": " بريميوم" if self.is_premium else " عادي",
            "tokens": f"{self.tokens:.1f}/{self.capacity}",
            "refill": f"{self.refill_rate}/s",
            "rate": f"{rate:.2f} msg/s",
            "total": self.total_sent,
            "daily_max": self.daily_limit,
        }


async def _keep_typing(chat_id):
    while chat_id in spam_targets:
        try:
            async with client.action(chat_id, "typing"):
                await asyncio.sleep(4)
        except Exception:
            pass


async def _spam_loop(chat_id, reply_to=None):
    while chat_id in spam_targets:
        import random as _rnd
        batch = max(1, int(_rnd.uniform(spam_batch_min, spam_batch_max)))
        words = []
        for i in range(batch):
            if chat_id not in spam_targets:
                break
            words.append(await _spam_next_word())
        if words:
            if flood_guard_enabled and flood_guard:
                await flood_guard.wait_if_needed()
            if len(words) == 1:
                try:
                    await client.send_message(chat_id, words[0], reply_to=reply_to)
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    print(f"spam error: {e}")
            else:
                results = await asyncio.gather(
                    *[client.send_message(chat_id, w, reply_to=reply_to) for w in words],
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, FloodWaitError):
                        await asyncio.sleep(r.seconds + 1)
                        break
        if spam_delay_min > 0 or spam_delay_max > 0:
            speed = _rnd.uniform(spam_delay_min, spam_delay_max)
            await asyncio.sleep(speed)


async def _spam_next_word():
    """يولّد كلمة السب: عبر AI إذا مفعّل (يتناوب نمط فوضوي/تعييب بالاسم)، وإلا من المكتبة المحلية"""
    if spam_ai_enabled:
        _spam_next_word.toggle = not getattr(_spam_next_word, "toggle", False)
        try:
            if _spam_next_word.toggle:
                prompt = _ai_prompt_chaos(spam_ai_target)
            else:
                prompt = _ai_prompt_name(spam_ai_target)
            word = await asyncio.to_thread(_ai_request_sync, prompt)
            if word and len(word) > 10:
                return word
        except Exception as e:
            print(f"ai spam error: {e}")
    return generate_insult()


def _ai_prompt_chaos(target):
    name = (target or "").strip().lstrip("@") or "الفاجر"
    return (
        'Generate a chaotic Iraqi Arabic insult rant targeting a person whose name is: "'
        + name + '"'
        + "\n\nStart with: اسمع ي <his name in Arabic> ي ابن قحبه, then continue.\n\n"
        "Rules:\n"
        "- The rant is FREELY creative: mix 50% words from the given lists with 50% your OWN random vulgar Iraqi words. Do NOT just reuse the lists mechanically. Let it flow wild like a real angry rant, flipping between listed words and invented ones.\n"
        "- Convert target name to Arabic letters if English (Python -> بيثون). NEVER keep Latin letters. ONLY Arabic output.\n"
        "- Randomly interleave these components with your own invented ones: acts (سحق, ادعس, اغتصب, انيجمك, احرق, اشليف, انيج, اطحن), body parts (كسمك, قحبتي, طيزك, عيري, زبي, امك, كس اختك, كس خالتك, شرفك, دينك), target insults (ي العري, ي الكلبه, ي المحرمه, ي القحبتين, ي الغبيتين, ي الديوث, ي الاوزب, ي ابن جراره, ي ابن عريه, ي ابن فاجره, ي ابن ديوث, ي مستديث, ي زنوه, ي كاثوليكيه)\n"
        "- No structure, no punctuation, chaotic stream of words, each sentence different in length and flavor\n"
        "- 3-5 sentences, starting with the Arabic-converted name\n"
        "- Write ONLY the rant, no explanation"
    )


def _ai_prompt_name(target):
    name = (target or "").strip().lstrip("@") or "الفاجر"
    return (
        'Generate a savage mockery attack in Iraqi Arabic targeting a person named: "'
        + name + '"'
        + "\n\nThe style is interrogative-mockery: take his name / a word in his name, convert it to Arabic if English, and turn it into a dirty rhetorical question that humiliates him, exactly like these patterns:\n"
        "- اسمك متعاطي؟ متعاطي شنو على مص زب وتعاطيت؟\n"
        "- سكران؟ اسمك سكران؟ شنو مصيت العير وسكرت؟\n"
        "- قال اسمك كريم، كريم وين ومحارمك حريم للشارع؟\n\n"
        "Rules:\n"
        "- Build 4-7 such rhetorical-mockery sentences: each one picks a word from his name, repeats it as a question, then answers it with a dirty degrading punchline\n"
        "- Convert target name to Arabic letters if English. NEVER keep Latin letters. ONLY Arabic output.\n"
        "- Mix in Iraqi insults (ي بن قحبه, يا عري, يا ديوث) as punctuation between sentences\n"
        "- No punctuation structure, flowing rant\n"
        "- Always start by addressing the person: اسمع ي <اسمه> ي بن قحبه\n"
        "- Write ONLY the rant, no explanation"
    )


async def _forward_loop(chat_id):
    global forward_running
    while forward_running:
        if not selected_saved_msgs:
            forward_running = False
            break
        try:
            await client.forward_messages(chat_id, list(selected_saved_msgs))
        except Exception as e:
            print(f"forward error: {e}")
        import random as _rnd
        spd = _rnd.uniform(forward_delay_min, forward_delay_max) if forward_delay_min != forward_delay_max else forward_delay_min
        await asyncio.sleep(spd)


_INS_KEYS = {
    "شد": "sakhira",
}


@cmd(r"معاينة سب$")
async def _(event):
    if not INSULTS:
        _load_insults()
    samples = "\n".join(f"• {generate_insult()}" for _ in range(5))
    await edit_or_reply(
        event, f"**| عينات من المولّد :**\n\n{samples}"
    )


@cmd(r"عدد السب$")
async def _(event):
    if not INSULTS:
        _load_insults()
    await edit_or_reply(
        event, f"عدد التركيبات الممكنة: `{insult_combos():,}`"
    )


@cmd(r"اضف سب(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    parts = arg.split(maxsplit=1)
    if len(parts) < 2 or parts[0] not in _INS_KEYS:
        keys = " | ".join(_INS_KEYS)
        return await edit_delete(
            event, f"- اكتب: اضف سب <النوع> <النص>\nالأنواع: {keys}", 12
        )
    if not INSULTS:
        _load_insults()
    key = _INS_KEYS[parts[0]]
    INSULTS.setdefault(key, [])
    INSULTS[key].append(parts[1])
    db_write("insults", INSULTS)
    await edit_or_reply(
        event, f"تم إضافة إلى `{parts[0]}` ✓\nالتركيبات الآن: `{insult_combos():,}`"
    )


@cmd(r"نيكه(?:\s|$)([\s\S]*)")
async def _(event):
    global spam_ai_target
    arg = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    reply_to = reply.id if reply else None

    targets = []
    if arg:
        for tok in arg.split():
            ent = None
            try:
                if tok.isdigit() or (tok.startswith("-") and tok[1:].isdigit()):
                    ent = await event.client.get_entity(int(tok))
                else:
                    ent = await event.client.get_entity(tok)
            except Exception:
                ent = None
            if ent:
                targets.append(getattr(ent, "id", None))
        targets = [t for t in targets if t]
    if not targets:
        targets = [event.chat_id]

    if spam_ai_enabled:
        if reply:
            tgt = await _resolve_spam_target(reply)
            spam_ai_target = (tgt.get("name") or "").strip()
        else:
            spam_ai_target = arg.split()[0] if arg else ""
        db_set("settings", "spam_ai_target", spam_ai_target)
    else:
        spam_ai_target = ""

    started = []
    for cid in targets:
        if cid in spam_targets:
            continue
        r_to = reply_to if cid == event.chat_id else None
        ent = None
        try:
            ent = await event.client.get_entity(cid)
        except Exception:
            ent = None
        spam_targets[cid] = {"reply": r_to, "ent": ent}
        asyncio.ensure_future(_spam_loop(cid, r_to))
        asyncio.ensure_future(_keep_typing(cid))
        started.append(cid)

    if not started:
        return await edit_delete(event, "- كل الأهداف تعمل بالفعل", 6)

    db_set("settings", "spam_targets", [str(c) for c in started])
    db_set("settings", "spam_delay_min", spam_delay_min)
    db_set("settings", "spam_delay_max", spam_delay_max)
    db_set("settings", "spam_batch_min", spam_batch_min)
    db_set("settings", "spam_batch_max", spam_batch_max)

    import random as _rnd
    speed = _rnd.uniform(spam_delay_min, spam_delay_max) if spam_delay_min != spam_delay_max else spam_delay_min
    state = "🛡" if flood_guard_enabled else ""
    batch_txt = f"{spam_batch_min} ~ {spam_batch_max}" if spam_batch_min != spam_batch_max else str(spam_batch_min)
    msg = f" بدء الإرسال... ⏱ {spam_delay_min} ~ {spam_delay_max}ث | دفعة: {batch_txt} {state}"
    msg += f"\n الأهداف ({len(started)}): " + ", ".join(f"`{c}`" for c in started)
    if spam_ai_enabled:
        msg += "\n 🧠 وضع الذكاء: مفعل" + (f" | الهدف: {spam_ai_target}" if spam_ai_target else " | بدون هدف")
    if reply_to and event.chat_id in started:
        msg += "\n مستهدف: على الرسالة المُشار إليها"
    await event.edit(msg)


@cmd(r"سب ذكاء$")
async def _(event):
    global spam_ai_enabled
    spam_ai_enabled = not spam_ai_enabled
    db_set("settings", "spam_ai_enabled", spam_ai_enabled)
    state = "مفعل 🧠" if spam_ai_enabled else "معطّل"
    await edit_or_reply(event, f"وضع سب الذكاء: {state}\n(عند التفعيل يولّد السب بـ AI ويستخرج الهدف من الرد)")


async def _resolve_spam_target(reply):
    """يستخرج اسم المستهدف من الرد: الاسم الكامل (first + last)"""
    name = ""
    raw = ""
    uid = None
    if reply:
        uid = reply.sender_id
        raw = (reply.text or "").strip()
        try:
            if reply.sender:
                first = getattr(reply.sender, "first_name", "") or ""
                last = getattr(reply.sender, "last_name", "") or ""
                name = (first + " " + last).strip()
                if not name:
                    name = get_display_name(reply.sender)
        except Exception:
            pass
    if not name and uid:
        name = str(uid)
    return {"name": name, "raw": raw, "uid": uid}


@cmd(r"خلاص$")
async def _(event):
    if not spam_targets:
        return await edit_delete(event, "- الإرسال متوقف بالفعل", 6)
    count = len(spam_targets)
    spam_targets.clear()
    db_set("settings", "spam_targets", [])
    await event.edit(f" تم إيقاف الإرسال من كل الأهداف ({count})")


@cmd(r"الأهداف$")
async def _(event):
    if not spam_targets:
        return await edit_delete(event, "- لا توجد أهداف جارية", 6)
    lines = []
    for cid, info in spam_targets.items():
        r = "رد" if info.get("reply") else "-"
        lines.append(f"• `{cid}` | {r}")
    await edit_or_reply(
        event, f"**| أهداف الإرسال الجارية ({len(lines)}):**\n\n" + "\n".join(lines)
    )


@cmd(r"دفعة(?:\s|$)([\s\S]*)")
async def _(event):
    global spam_batch_min, spam_batch_max
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        await edit_or_reply(event, f"- مثال: `{PREFIX}دفعة 3` أو `{PREFIX}دفعة 1 ~ 10`")
        return
    if "~" in arg:
        parts = arg.split("~", 1)
        try:
            lo = float(parts[0].strip())
            hi = float(parts[1].strip())
            if lo < 1 or hi < 1:
                return await edit_delete(event, "- القيمة يجب أن تكون 1 أو أكثر", 6)
            if lo > hi:
                lo, hi = hi, lo
            spam_batch_min = int(lo)
            spam_batch_max = int(hi)
            await edit_or_reply(event, f"تم ضبط الدفعة: عشوائي بين {int(lo)} و {int(hi)} رسالة ✓")
        except (ValueError, AttributeError):
            await edit_delete(event, "- صيغة خاطئة | مثال: دفعة 1 ~ 10", 6)
    else:
        try:
            count = float(arg)
            if count < 1:
                return await edit_delete(event, "- القيمة يجب أن تكون 1 أو أكثر", 6)
            spam_batch_min = int(count)
            spam_batch_max = int(count)
            await edit_or_reply(event, f"تم ضبط الدفعة إلى {int(count)} رسالة ✓")
        except (ValueError, AttributeError):
            await edit_delete(event, "- قيمة غير صالحة | مثال: دفعة 3 أو دفعة 1 ~ 10", 6)


@cmd(r"(?:وقت الارسال|سرعه)(?:\s|$)([\s\S]*)")
async def _(event):
    global spam_delay_min, spam_delay_max
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        await edit_or_reply(event, f"- مثال: `{PREFIX}سرعه 3` أو `{PREFIX}سرعه 3 ~ 5` أو `{PREFIX}سرعه 1.3 ~ 2.7`")
        return
    if "~" in arg:
        parts = arg.split("~", 1)
        try:
            lo = float(parts[0].strip())
            hi = float(parts[1].strip())
            if lo < 0 or hi < 0:
                return await edit_delete(event, "- القيمة يجب أن تكون 0 أو أكثر", 6)
            if lo > hi:
                lo, hi = hi, lo
            spam_delay_min = lo
            spam_delay_max = hi
            await edit_or_reply(event, f"تم ضبط السرعة: عشوائي بين {lo} و {hi}ث ✓")
        except (ValueError, AttributeError):
            await edit_delete(event, "- صيغة خاطئة | مثال: سرعه 3 ~ 5", 6)
    else:
        try:
            delay = float(arg)
            if delay < 0:
                return await edit_delete(event, "- الوقت يجب أن يكون 0 أو أكثر", 6)
            spam_delay_min = delay
            spam_delay_max = delay
            await edit_or_reply(event, f"تم ضبط وقت الإرسال إلى {delay}ث ✓")
        except (ValueError, AttributeError):
            await edit_delete(event, "- قيمة غير صالحة | مثال: سرعه 0.5 أو سرعه 3 ~ 5", 6)


@cmd(r"تتبع(?:\s|$)([\s\S]*)")
async def _(event):
    global follow_running
    target_id = None
    reply = await event.get_reply_message()
    if reply and reply.sender_id:
        target_id = reply.sender_id
    else:
        arg = (event.pattern_match.group(1) or "").strip()
        if arg:
            ent = await _ai_resolve_ent(arg)
            if ent and hasattr(ent, "id"):
                target_id = ent.id
            else:
                return await edit_delete(event, "- لم أجد المستخدم", 8)
        else:
            return await edit_delete(event, f"- رد على رسالة الشخص أو اكتب: {PREFIX}تتبع <يوزر>", 8)
    db_set("settings", "follow_target", target_id)
    db_set("settings", "follow_chat", event.chat_id)
    db_set("settings", "follow_running", True)
    db_set("settings", "follow_last_msg", 0)
    follow_running = True
    asyncio.ensure_future(_follow_loop())
    try:
        user = await event.client.get_entity(target_id)
        name = get_display_name(user)
    except Exception:
        name = str(target_id)
    import random as _rnd
    spd = _rnd.uniform(spam_delay_min, spam_delay_max) if spam_delay_min != spam_delay_max else spam_delay_min
    await edit_or_reply(event, f"تم تفعيل التتبع على: {name} — `{target_id}` ✓\nسرعة الإرسال: {spd:.1f}ث\nسترد تلقائياً على رسائله في الخاص والمجموعات")


@cmd(r"كافي$")
async def _(event):
    global follow_running
    db_set("settings", "follow_running", False)
    follow_running = False
    await edit_or_reply(event, "تم إيقاف التتبع ✓")


@client.on(events.NewMessage(incoming=True))
async def _auto_follow(event):
    if not follow_running or event.out:
        return
    target_id = db_get("settings", "follow_target")
    if not target_id:
        return
    target_id = int(target_id)
    sender_id = getattr(event, "sender_id", None)
    if not sender_id or int(sender_id) != target_id:
        return
    db_set("settings", "follow_last_msg", event.id)
    db_set("settings", "follow_chat", event.chat_id)
    word = generate_insult()
    try:
        async with client.action(event.chat_id, "typing"):
            await asyncio.sleep(0.3)
        if flood_guard_enabled and flood_guard:
            await flood_guard.wait_if_needed()
        await event.reply(word)
    except Exception:
        pass


async def _follow_loop():
    """حلقة تتبع مستمرة — ترسل ردود بشكل دوري على المستهدف حسب السرعة المحددة"""
    import random as _rnd
    me_id = None
    try:
        me = await client.get_me()
        me_id = me.id
    except Exception:
        pass
    while follow_running:
        try:
            target_id = db_get("settings", "follow_target")
            chat_id = db_get("settings", "follow_chat")
            last_msg_id = db_get("settings", "follow_last_msg", 0)
            if not target_id or not chat_id:
                await asyncio.sleep(30)
                continue
            target_id = int(target_id)
            if last_msg_id:
                try:
                    msg = await client.get_messages(entity=chat_id, ids=last_msg_id)
                    if msg and not msg.deleted:
                        pass
                    else:
                        async for msg in client.iter_messages(target_id, limit=1):
                            if msg and not msg.deleted:
                                sender = getattr(msg, "sender_id", None)
                                if sender and int(sender) != me_id:
                                    last_msg_id = msg.id
                                    chat_id = msg.chat_id
                                    db_set("settings", "follow_last_msg", msg.id)
                                    db_set("settings", "follow_chat", msg.chat_id)
                                break
                except Exception:
                    pass
            words = []
            batch = max(1, int(_rnd.uniform(spam_batch_min, spam_batch_max)))
            for _i in range(batch):
                words.append(generate_insult())
            try:
                if flood_guard_enabled and flood_guard:
                    await flood_guard.wait_if_needed()
                if len(words) == 1:
                    await client.send_message(chat_id, words[0], reply_to=last_msg_id)
                else:
                    await asyncio.gather(
                        *[client.send_message(chat_id, w, reply_to=last_msg_id) for w in words],
                        return_exceptions=True,
                    )
            except Exception:
                pass
        except Exception:
            pass
        spd = _rnd.uniform(spam_delay_min, spam_delay_max) if spam_delay_min != spam_delay_max else spam_delay_min
        await asyncio.sleep(spd)


@cmd(r"حماية الفلود$")
async def _(event):
    global flood_guard_enabled
    flood_guard_enabled = not flood_guard_enabled
    state = "🛡 مفعلة" if flood_guard_enabled else " معطلة"
    await edit_or_reply(event, f"حماية الفلود: {state}")


@cmd(r"الفلود$")
async def _(event):
    if not flood_guard:
        return await edit_delete(event, "- الحماية غير مهيأة", 6)
    s = flood_guard.get_stats()
    txt = (
        f"**🛡 حماية الفلود**\n\n"
        f"الحساب: {s['type']}\n"
        f"Tokens: {s['tokens']}\n"
        f"Refill: {s['refill']}\n"
        f"المعدل: {s['rate']}\n"
        f"المرسل: {s['total']}/{s['daily_max']}"
    )
    await edit_or_reply(event, txt)


@cmd(r"تحديد$")
async def _(event):
    global selected_saved_msgs
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(event, "- رد على الرسالة في المحفوظات", 8)
    me = await client.get_me()
    if event.chat_id != me.id:
        return await edit_delete(event, "- استخدم هذا الأمر في المحفوظات فقط", 8)
    if any(getattr(m, "id", None) == reply.id for m in selected_saved_msgs):
        return await edit_delete(event, "- هذه الرسالة محددة مسبقاً", 6)
    selected_saved_msgs.append(reply)
    preview = (reply.text or "[وسائط]")[:50]
    await edit_or_reply(
        event, f"تم تحديد الرسالة ({len(selected_saved_msgs)}) ✓\n📝 {preview}..."
    )


@cmd(r"الغاء تحديد$")
async def _(event):
    global selected_saved_msgs
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(event, "- رد على الرسالة في المحفوظات", 8)
    before = len(selected_saved_msgs)
    selected_saved_msgs = [m for m in selected_saved_msgs if getattr(m, "id", None) != reply.id]
    if len(selected_saved_msgs) == before:
        return await edit_delete(event, "- هذه الرسالة غير محددة", 6)
    await edit_or_reply(
        event, f"تم إلغاء تحديد الرسالة ✓\nالمتبقي: {len(selected_saved_msgs)}"
    )


@cmd(r"مسح كل محدد$")
async def _(event):
    global selected_saved_msgs
    if not selected_saved_msgs:
        return await edit_delete(event, "- لا توجد رسائل محددة", 6)
    count = len(selected_saved_msgs)
    selected_saved_msgs = []
    await edit_or_reply(event, f"تم مسح كل الرسائل المحددة ({count}) ✓")


@cmd(r"المحددات$")
async def _(event):
    if not selected_saved_msgs:
        return await edit_delete(event, "- لا توجد رسائل محددة", 6)
    lines = []
    for i, m in enumerate(selected_saved_msgs, 1):
        preview = (m.text or "[وسائط]").replace("\n", " ")[:40]
        lines.append(f"{i}. `{getattr(m, 'id', '?')}` {preview}")
    await edit_or_reply(
        event, f"**| الرسائل المحددة ({len(lines)}):**\n\n" + "\n".join(lines)
    )


@cmd(r"تشغيل التحويل$")
async def _(event):
    global forward_running, forward_task
    if not selected_saved_msgs:
        return await edit_delete(event, "- لم يتم تحديد رسائل! استخدم .تحديد أولاً", 8)
    if forward_running:
        return await edit_delete(event, "- التحويل يعمل بالفعل", 6)
    forward_running = True
    forward_task = asyncio.ensure_future(_forward_loop(event.chat_id))
    await event.edit(
        f" تشغيل التحويل من المحفوظات... رسائل: {len(selected_saved_msgs)} | delay: {forward_delay_min} ~ {forward_delay_max}ث"
    )


@cmd(r"ايقاف التحويل$")
async def _(event):
    global forward_running
    if not forward_running:
        return await edit_delete(event, "- التحويل متوقف بالفعل", 6)
    forward_running = False
    await event.edit(" تم إيقاف التحويل")


@cmd(r"ديلاي(?:\s|$)([\s\S]*)")
async def _(event):
    global forward_delay_min, forward_delay_max
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        await edit_or_reply(event, f"- مثال: `{PREFIX}ديلاي 0.5` أو `{PREFIX}ديلاي 0.3 ~ 1.5`")
        return
    if "~" in arg:
        parts = arg.split("~", 1)
        try:
            lo = float(parts[0].strip())
            hi = float(parts[1].strip())
            if lo < 0 or hi < 0:
                return await edit_delete(event, "- القيمة يجب أن تكون 0 أو أكثر", 6)
            if lo > hi:
                lo, hi = hi, lo
            forward_delay_min = lo
            forward_delay_max = hi
            await edit_or_reply(event, f"تم ضبط ديلاي التحويل: عشوائي بين {lo} و {hi}ث ✓")
        except (ValueError, AttributeError):
            await edit_delete(event, "- صيغة خاطئة | مثال: ديلاي 0.3 ~ 1.5", 6)
    else:
        try:
            delay = float(arg)
            if delay < 0:
                return await edit_delete(event, "- القيمة يجب أن تكون 0 أو أكثر", 6)
            forward_delay_min = delay
            forward_delay_max = delay
            await edit_or_reply(event, f"تم ضبط ديلاي التحويل إلى {delay}ث ✓")
        except (ValueError, AttributeError):
            await edit_delete(event, "- قيمة غير صالحة | مثال: ديلاي 0 أو ديلاي 0.3 ~ 1.5", 6)




@cmd(r"ملصق$")
async def _(event):
    reply = await event.get_reply_message()
    if not reply or not reply.photo:
        return await edit_delete(event, "- رد على صورة", 8)
    m = await event.edit("- جاري التحويل...")
    try:
        img = await event.client.download_media(reply.media)
        await event.client.send_file(
            event.chat_id, img, force_document=False,
            attributes=[types.DocumentAttributeFilename("sticker.webp")],
        )
        os.remove(img)
        await m.delete()
    except Exception as e:
        await m.edit(f"`{e}`")


@cmd(r"تحويل صورة$")
async def _(event):
    reply = await event.get_reply_message()
    if not reply or not reply.sticker:
        return await edit_delete(event, "- رد على ملصق", 8)
    m = await event.edit("- جاري التحويل...")
    try:
        st = await event.client.download_media(reply.media)
        await event.client.send_file(event.chat_id, st, force_document=False)
        os.remove(st)
        await m.delete()
    except Exception as e:
        await m.edit(f"`{e}`")


@cmd(r"صوت$")
async def _(event):
    reply = await event.get_reply_message()
    if not reply or not (reply.audio or reply.voice or reply.video or reply.document or reply.video_note):
        return await edit_delete(event, "- رد على مقطع/أغنية/صوت/فيديو لتحويله إلى بصمة صوت", 8)
    m = await event.edit("- جاري التحويل إلى بصمة صوت...")
    tmp_in = None
    tmp_out = None
    try:
        tmp_in = await event.client.download_media(reply.media)
        tmp_out = tmp_in + "_voice.ogg"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", tmp_in,
            "-vn", "-c:a", "libopus",
            "-b:a", "32k", "-ar", "48000", "-ac", "1",
            "-y", tmp_out,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=120)
        if proc.returncode != 0:
            return await m.edit(" فشل التحويل — تأكد من أن الملف صالح")
        import mimetypes
        await event.client.send_file(
            event.chat_id, tmp_out,
            voice_note=True,
            attributes=[types.DocumentAttributeAudio(
                voice=True,
                duration=0,
                title="",
                performer="",
            )],
            reply_to=reply.id,
        )
        await m.delete()
    except asyncio.TimeoutError:
        await m.edit(" انتهت مهلة التحويل (الملف كبير جداً)")
    except Exception as e:
        await m.edit(f" خطأ: {e}")
    finally:
        for f in (tmp_in, tmp_out):
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass




@cmd(r"نسبة الحب(?:\s|$)([\s\S]*)")
async def _(event):
    await edit_or_reply(event, f"نسبة الحب: {random.randint(0, 100)}% ♥")


@cmd(r"نسبة الغباء(?:\s|$)([\s\S]*)")
async def _(event):
    await edit_or_reply(event, f"نسبة الغباء: {random.randint(0, 100)}% 🤡")


@cmd(r"نرد$")
async def _(event):
    await event.delete()
    await event.client.send_message(
        event.chat_id, file=types.InputMediaDice(emoticon="\U0001F3B2")
    )


@cmd(r"قلوب$")
async def _(event):
    hearts = ["\u2764", "\U0001F9E1", "\U0001F49B", "\U0001F49A", "\U0001F499", "\U0001F49C", "\U0001F5A4", "\U0001F90D", "\U0001F90E", "\U0001F497"]
    for h in hearts:
        try:
            await event.edit(h * 5)
            await asyncio.sleep(0.4)
        except Exception:
            break


@cmd(r"عد(?:\s|$)([\s\S]*)")
async def _(event):
    arg = event.pattern_match.group(1)
    if not arg or not arg.strip().isdigit():
        return await edit_delete(event, "- اكتب: عد <رقم>", 8)
    n = min(int(arg.strip()), 100)
    for i in range(n, -1, -1):
        try:
            await event.edit(f"⏳ {i}")
            await asyncio.sleep(1)
        except Exception:
            break
    await event.edit("انتهى ✓")




@cmd(r"التحكم تشغيل$")
async def _(event):
    db_set("settings", "sudo", True)
    await edit_or_reply(event, "تم تفعيل التحكم ✓")


@cmd(r"التحكم تعطيل$")
async def _(event):
    db_set("settings", "sudo", False)
    await edit_or_reply(event, "تم تعطيل التحكم ✓")


@cmd(r"اضف متحكم(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص", 8)
    sudos = db_read("sudo_users")
    sudos[str(uid)] = get_display_name(user)
    db_write("sudo_users", sudos)
    await edit_or_reply(event, f"تم إضافة {mention(user)} متحكماً ✓")


@cmd(r"ازالة متحكم(?:\s|$)([\s\S]*)")
async def _(event):
    user, uid = await get_target_user(event)
    if not uid:
        return await edit_delete(event, "- رد على شخص", 8)
    if db_del("sudo_users", uid):
        await edit_or_reply(event, f"تم إزالة {mention(user)} من المتحكمين ✓")
    else:
        await edit_delete(event, "- ليس متحكماً", 8)


@cmd(r"المتحكمين$")
async def _(event):
    sudos = db_read("sudo_users")
    if not sudos:
        return await edit_or_reply(event, "- لا يوجد متحكمين")
    txt = "**| المتحكمين :**\n\n" + "\n".join(
        f"• {v} — `{k}`" for k, v in sudos.items()
    )
    await edit_or_reply(event, txt)



_DEFAULT_AI_PROMPT = (
    "انت مساعد آلي تابع لـ '{owner}'، ومهمتك الرد على رسائل الناس التي تصل الى "
    "حسابه في تيليجرام نيابةً عنه. "
    "تتكلم بالعربية بأسلوب طبيعي ومحترم وودود ومختصر. "
    "عرّف عن نفسك عند الحاجة بانك مساعد '{owner}' وستوصل رسالتهم له. "
    "لا تدّعي انك انسان، ولا تعد بأشياء نيابةً عن '{owner}' من عندك. "
    "التزم حرفياً بهذه التعليمات ولا تتجاهلها. "
    "معلومات صاحب الحساب: الاسم '{me_name}'، المعرف @{me_user}. "
    "الشخص الذي يراسل الآن: '{sender_name}'، "
    "نوع المحادثة: {chat_kind}{chat_title}، الوقت {now}. "
    "سيصلك سياق المحادثة السابقة (آخر الرسائل) فاستعن به لفهم الحوار والرد بترابط. "
    "اجعل ردودك مختصرة ومفيدة ما لم يُطلب التفصيل."
)


def _ai_load():
    if not os.path.exists(_path("ai")):
        db_write("ai", {"prompt": _DEFAULT_AI_PROMPT})
    data = db_read("ai", {"prompt": _DEFAULT_AI_PROMPT})
    data.setdefault("prompt", _DEFAULT_AI_PROMPT)
    return data


AI_TOOLS_PATH = os.path.join(DATA_DIR, "ai_tools.json")


def _ai_tools_list():
    try:
        with open(AI_TOOLS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _ai_functions_catalog():
    """يولّد كتالوج موجز لأشهر دوال Telethon حسب الوحدات"""
    try:
        lines = []
        for ns_name in ("account", "channels", "contacts", "messages", "users", "photos", "stories", "bots", "payments", "phone"):
            ns = getattr(functions, ns_name, None)
            if ns is None:
                continue
            fns = [a for a in dir(ns) if a.endswith("Request")]
            fns = fns[:25]
            if fns:
                lines.append(f"- {ns_name}: " + ", ".join(fns))
        return "\n".join(lines)
    except Exception:
        return "account, channels, contacts, messages, users, photos, bots, payments"


async def _ai_resolve_ent(target):
    if target is None:
        return None
    target = str(target).strip().lstrip("@")
    if target.lstrip("-").isdigit() or target.startswith("+"):
        try:
            if target.startswith("+") or (target.isdigit() and 7 <= len(target) <= 15):
                phone = target if target.startswith("+") else "+" + target.lstrip("+")
                imp = await client(functions.contacts.ImportContactsRequest(
                    contacts=[types.InputPhoneContact(client_id=0, phone=phone, first_name="x", last_name="")]))
                if imp.users:
                    return imp.users[0]
        except Exception:
            pass
        uid = int(target.lstrip("+"))
        try:
            return await client.get_entity(uid)
        except Exception:
            pass
        ent = await _ai_find_by_id(uid)
        if ent:
            return ent
        return None
    try:
        return await client.get_entity(target)
    except Exception:
        pass
    try:
        res = await client(functions.contacts.ResolveUsernameRequest(target.replace("@", "")))
        return res.users[0] if getattr(res, "users", None) else (res.chats[0] if getattr(res, "chats", None) else None)
    except Exception:
        return None


async def _ai_find_by_id(uid):
    """يبحث عن مستخدم في الرسائل الحديثة والجهات لمن لم يُخزّن access_hash"""
    try:
        async for d in client.iter_dialogs(limit=80):
            try:
                if d.entity and getattr(d.entity, "id", None) == uid:
                    return d.entity
            except Exception:
                pass
        async for d in client.iter_dialogs(limit=30):
            try:
                async for msg in client.iter_messages(d.id, limit=50):
                    if msg.sender_id == uid:
                        sender = await msg.get_sender()
                        if sender:
                            return sender
            except Exception:
                pass
    except Exception:
        pass
    return None


async def _ai_run_any_tool(name, p):
    """يحاول تنفيذ أي اسم أداة كدالة Telethon حقيقية تلقائياً"""
    p = p or {}
    ns_name = None
    method = None
    params = {}
    if "." in str(name):
        ns_name, method = str(name).split(".", 1)
    elif isinstance(p.get("request"), dict) and p["request"].get("_"):
        full = p["request"]["_"]
        if "." in full:
            ns_name, method = full.split(".", 1)
        else:
            method = full
        params = {k: v for k, v in p["request"].items() if k != "_"}
    elif p.get("_") and "." in str(p["_"]):
        ns_name, method = str(p["_"]).split(".", 1)
        params = {k: v for k, v in p.items() if k != "_"}
    else:
        method = str(name)
        params = p
    if not method:
        return f" أداة غير معروفة: {name}"
    ns = None
    if ns_name:
        ns = getattr(functions, ns_name, None) or getattr(types, ns_name, None)
    if ns is None:
        for candidate in (functions, types):
            try:
                ns = getattr(candidate, ns_name, None) if ns_name else None
            except Exception:
                ns = None
            if ns:
                break
    if ns is None and ns_name:
        return f" لا توجد وحدة للدالة {method}"
    if ns is None:
        fn = _find_function_global(method)
        if fn:
            return await _ai_run_direct(fn, params)
        return f" لا توجد دالة {method} في أي وحدة"
    fn = getattr(ns, method, None)
    if fn is None:
        fn = _find_any_method(ns, method)
    if fn is None:
        return f" لا توجد دالة {method}"
    return await _ai_run_direct(fn, params)


def _find_function_global(method):
    """يبحث عن دالة في كل وحدات functions ثم types"""
    for candidate in (functions, types):
        for sub in dir(candidate):
            if sub.startswith("_") or sub.startswith("TL"):
                continue
            try:
                ns = getattr(candidate, sub, None)
            except Exception:
                continue
            if ns is None or not hasattr(ns, method):
                continue
            fn = getattr(ns, method, None)
            if callable(fn):
                return fn
            fn2 = _find_any_method(ns, method)
            if fn2:
                return fn2
    return None


def _find_any_method(ns, method):
    """يبحث عن دالة بعدة محاولات: المطابقة التامة، إضافة Request، اختلافات الحالة، تشابه الأسماء"""
    if not method:
        return None
    candidates = [
        method,
        method + "Request",
        method.replace("Request", ""),
        method[0].lower() + method[1:],
        method[0].upper() + method[1:],
        method[0].upper() + method[1:] + "Request",
        "Get" + method, "Get" + method + "Request",
        "Send" + method, "Send" + method + "Request",
        "Edit" + method, "Edit" + method + "Request",
        "Create" + method, "Create" + method + "Request",
        "Delete" + method, "Delete" + method + "Request",
        "Update" + method, "Update" + method + "Request",
    ]
    all_attrs = [a for a in dir(ns)]
    for c in candidates:
        obj = getattr(ns, c, None)
        if callable(obj):
            return obj
    method_l = method.lower()
    for attr in all_attrs:
        al = attr.lower()
        if al == method_l or al.endswith(method_l) or al.replace("request", "") == method_l:
            obj = getattr(ns, attr, None)
            if callable(obj):
                return obj
    try:
        from difflib import get_close_matches
        names = [a for a in all_attrs if a.endswith("Request")]
        best = get_close_matches(method, [a.replace("Request", "") for a in names], n=1, cutoff=0.5)
        if best:
            idx = [a.replace("Request", "") for a in names].index(best[0])
            return getattr(ns, names[idx], None)
    except Exception:
        pass
    return None


async def _ai_run_direct(fn, params):
    """ينفّذ دالة Telethon مباشرة مع تحويل المعطيات النصية لكيانات"""
    try:
        params = await _ai_coerce_params(fn, params)
        res = await client(fn(**params))
        return f" نتيجة {fn.__name__}:\n{str(res)[:3000]}"
    except Exception as e:
        return f" خطأ تنفيذ {fn.__name__}: {e}"


async def _ai_run_raw_tl(p):
    """ينفّذ استدعاء Telethon خام بلا قيود — يدعم عدة أشكال من الذكاء:
    الشكل 1 (الموثّق): {"namespace","method","params"}
    الشكل 2: {"request": {"_": "channels.GetFullChannel", "channel": "acjava"}}
    الشكل 3: {"tl": "channels.GetFullChannel", "params": {...}}"""
    try:
        ns_name = None
        method = None
        params = {}

        if p.get("namespace") and p.get("method"):
            ns_name, method, params = p["namespace"], p["method"], (p.get("params") or {})

        elif p.get("tl"):
            tl = p["tl"]
            if "." in tl:
                ns_name, method = tl.split(".", 1)
            else:
                method = tl
            params = p.get("params") or {}

        elif isinstance(p.get("request"), dict) and p["request"].get("_"):
            full = p["request"]["_"]
            if "." in full:
                ns_name, method = full.split(".", 1)
            else:
                method = full
            params = {k: v for k, v in p["request"].items() if k != "_"}

        if not method:
            return " تعذّر فهم شكل الاستدعاء raw_tl"

        ns = None
        if ns_name:
            ns = getattr(functions, ns_name, None) or getattr(types, ns_name, None)
        if ns is None:
            guess = method.split("Get")[0].split("Edit")[0].split("Send")[0].split("Create")[0].split("Delete")[0].split("Resolve")[0].rstrip("s").lower() or "channels"
            ns = getattr(functions, guess, None) or getattr(types, guess, None)
        if ns is None:
            return f" لا توجد وحدة للدالة {method}"
        fn = getattr(ns, method, None)
        if fn is None:
            fn = _find_any_method(ns, method)
        if fn is None:
            return f" لا توجد دالة {method} في {ns_name or guess}"

        params = await _ai_coerce_params(fn, params)
        res = await client(fn(**params))
        return f" نتيجة {getattr(fn, '__name__', method)}:\n{str(res)[:3000]}"
    except Exception as e:
        return f" خطأ تنفيذ raw_tl: {e}"


async def _ai_coerce_params(fn, params):
    """يحوّل بعض المعطيات النصية (يوزر/رابط) إلى كيانات Telethon قبل الاستدعاء"""
    import inspect
    try:
        sig = inspect.signature(fn)
        fields = set(sig.parameters.keys())
    except Exception:
        fields = set(params.keys())
    out = {}
    for k, v in params.items():
        if k in ("channel", "peer", "from_id", "to_id") and isinstance(v, str):
            if v.startswith("@") or "t.me" in v or (v.lstrip("-").isdigit() and not v.isdigit()):
                try:
                    ent = await _ai_resolve_ent(v)
                    if ent is not None:
                        out[k] = ent
                        continue
                except Exception:
                    pass
        if k in ("user", "users") and isinstance(v, str):
            if v.startswith("@") or "t.me" in v:
                try:
                    ent = await _ai_resolve_ent(v)
                    if ent is not None:
                        out[k] = ent if k == "user" else [ent]
                        continue
                except Exception:
                    pass
        if k in ("chats",) and isinstance(v, list):
            try:
                ents = []
                for x in v:
                    if isinstance(x, str) and (x.startswith("@") or "t.me" in x):
                        e = await _ai_resolve_ent(x)
                        if e: ents.append(e)
                    else:
                        ents.append(x)
                out[k] = ents
                continue
            except Exception:
                pass
        out[k] = v
    return out


_AI_TOOL_ALIASES = {
    "كشف": "get_user", "معلومات": "get_user", "من_هذا": "get_user", "ابحث": "resolve_username",
    "ارسل": "send_message", "ابعت": "send_message", "رسالة": "send_message",
    "حظر": "block_user", "بان": "block_user", "امنع": "block_user",
    "الغاء_حظر": "unblock_user", "فك_حظر": "unblock_user",
    "طرد": "kick_user", "اطرد": "kick_user",
    "محادثاتي": "list_dialogs", "دردشات": "list_dialogs", "قوائمي": "list_dialogs",
    "اقرا": "read_messages", "قراءة": "read_messages", "اقرأ": "read_messages",
    "امسح": "delete_messages", "مسح": "delete_messages",
    "انشئ": "create_group", "انشاء_مجموعة": "create_group",
    "انضم": "invite_to_chat", "دعوة": "invite_to_chat",
    "غير_اسمي": "update_profile", "تغيير_اسم": "update_profile",
    "مغادرة": "leave_chat", "غادر": "leave_chat",
    "توجيه": "forward_message", "انقل": "forward_message",
    "تثبيت": "pin_message", "ثبت": "pin_message",
}


async def _ai_run_tool(call):
    """ينفّذ استدعاء أداة JSON صريح ويرجع النتيجة كنص"""
    name = call.get("name") or call.get("tool")
    name = _AI_TOOL_ALIASES.get(str(name), name)
    p = call.get("parameters") or call.get("params") or {}
    try:
        if name == "send_message":
            ent = await _ai_resolve_ent(p["target"])
            if ent is None:
                return " تعذّر إيجاد الهدف"
            await client.send_message(ent, p["text"])
            return f" تم الإرسال إلى {p['target']}"
        if name == "block_user":
            ent = await _ai_resolve_ent(p["target"])
            if ent is None:
                return " تعذّر إيجاد المستخدم"
            await client(functions.contacts.BlockRequest(ent))
            return f" تم حظر {p['target']}"
        if name == "unblock_user":
            ent = await _ai_resolve_ent(p["target"])
            if ent is None:
                return " تعذّر إيجاد المستخدم"
            await client(functions.contacts.UnblockRequest(ent))
            return f" تم إلغاء حظر {p['target']}"
        if name == "kick_user":
            ent = await _ai_resolve_ent(p["user"])
            chat = await _ai_resolve_ent(p["chat"])
            if ent is None or chat is None:
                return " تعذّر إيجاد المستخدم أو المجموعة"
            await client.kick_participant(chat, ent)
            return f" تم طرد {p['user']} من {p['chat']}"
        if name == "ban_chat_member":
            ent = await _ai_resolve_ent(p["user"])
            chat = await _ai_resolve_ent(p["chat"])
            if ent is None or chat is None:
                return " تعذّر إيجاد"
            await client(functions.channels.EditBannedRequest(chat, ent,
                  types.ChatBannedRights(until_date=None, view_messages=True)))
            return f" تم حظر {p['user']} من {p['chat']}"
        if name == "pin_message":
            await client.pin_message(p["chat_id"], p["message_id"])
            return f" تم تثبيت الرسالة {p['message_id']}"
        if name == "read_messages":
            ent = await _ai_resolve_ent(p["target"])
            if ent is None:
                return " تعذّر إيجاد المحادثة"
            limit = int(p.get("limit", 5))
            out = []
            async for msg in client.iter_messages(ent, limit=limit):
                who = "أنت" if msg.out else (get_display_name(await msg.get_sender()) if msg.sender_id else "؟")
                out.append(f"{who}: {msg.raw_text or '[وسائط]'}")
            return ":\n" + "\n".join(reversed(out)) if out else "لا رسائل"
        if name == "delete_messages":
            ent = await _ai_resolve_ent(p["target"])
            if ent is None:
                return " تعذّر إيجاد"
            if p.get("message_ids"):
                await client.delete_messages(ent, p["message_ids"], revoke=p.get("revoke", True))
                return f" تم حذف الرسائل من {p['target']}"
            await client.delete_messages(ent, None)
            return f" تم مسح المحادثة مع {p['target']}"
        if name == "get_me":
            me = await client.get_me()
            return f" {get_display_name(me)} | @{me.username or 'لايوجد'} | id {me.id} | هاتف {getattr(me,'phone','غير متاح')} | بريميوم {'نعم' if getattr(me,'premium',False) else 'لا'}"
        if name == "get_user":
            who = p.get("target") or p.get("user") or p.get("username") or p.get("id")
            ent = await _ai_resolve_ent(who)
            if ent is None:
                return " تعذّر إيجاد"
            return f" {get_display_name(ent)} | @{getattr(ent,'username',None) or 'لايوجد'} | id {ent.id} | بريميوم {'نعم' if getattr(ent,'premium',False) else 'لا'} | موثّق {'نعم' if getattr(ent,'verified',False) else 'لا'} | بايو: {getattr(ent,'about','') or 'لايوجد'}"
        if name == "list_dialogs":
            out = []
            async for d in client.iter_dialogs(limit=int(p.get("limit", 25))):
                out.append(f"- {d.name} ({d.id})")
            return ":\n" + "\n".join(out)
        if name == "resolve_username":
            res = await client(functions.contacts.ResolveUsernameRequest(str(p["username"]).replace("@", "")))
            u = res.users[0] if getattr(res, "users", None) else None
            if u:
                return f" {get_display_name(u)} | @{u.username or 'لايوجد'} | id {u.id}"
            return " لم يوجد"
        if name == "create_group":
            chat = await client(functions.channels.CreateChannelRequest(
                title=p["title"], about=p.get("about", ""), broadcast=bool(p.get("broadcast", False))))
            return f" تم الإنشاء: {p['title']} (id {chat.chats[0].id})"
        if name == "invite_to_chat":
            ent = await _ai_resolve_ent(p["user"])
            chat = await _ai_resolve_ent(p["chat"])
            if ent is None or chat is None:
                return " تعذّر إيجاد"
            await client(functions.channels.InviteToChannelRequest(chat, [ent]))
            return f" تمت دعوة {p['user']} إلى {p['chat']}"
        if name == "update_profile":
            kw = {}
            if p.get("first_name"):
                kw["first_name"] = p["first_name"]
            if "last_name" in p:
                kw["last_name"] = p["last_name"]
            if "about" in p:
                kw["about"] = p["about"]
            await client(functions.account.UpdateProfileRequest(**kw))
            return " تم تحديث البروفايل"
        if name == "leave_chat":
            chat = await _ai_resolve_ent(p["chat"])
            if chat is None:
                return " تعذّر إيجاد"
            await client(functions.channels.LeaveChannelRequest(chat))
            return f" تمت المغادرة: {p['chat']}"
        if name == "forward_message":
            fch = await _ai_resolve_ent(p["from_chat"])
            tch = await _ai_resolve_ent(p["to_chat"])
            await client.forward_messages(tch, p["message_id"], fch)
            return " تم التوجيه"
        if name == "raw_tl":
            return await _ai_run_raw_tl(p)
        if name == "my_channels":
            return await _ai_execute_action("قنواتي", event=None)
        if name == "count_dialogs":
            n = 0
            async for _ in client.iter_dialogs():
                n += 1
            return f" عدد محادثاتك: {n}"
        return await _ai_run_any_tool(name, p)
    except Exception as e:
        return f" خطأ تنفيذ {name}: {e}"


def _ai_parse_tool_calls(text):
    """يستخرج استدعاءات الأدوات بصيغة JSON من رد الذكاء (كتل code أو JSON عاري)"""
    calls = []
    for m in _re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.DOTALL):
        try:
            calls.append(json.loads(m.group(1)))
        except Exception:
            pass
    if calls:
        return calls
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "{":
            depth = 0
            j = i
            while j < n:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < n:
                blob = text[i:j + 1]
                try:
                    obj = json.loads(blob)
                    if isinstance(obj, dict) and ("name" in obj or "tool" in obj):
                        calls.append(obj)
                except Exception:
                    pass
                i = j + 1
                continue
        i += 1
    return calls


SOURCE_INFO_PATH = os.path.join(DATA_DIR, "source_info.txt")


def build_source_info():
    """يولّد ملف دليل السورس من قائمة الأوامر MENU + شرح عام"""
    lines = [
        "=== دليل سورس الجوكر (rkkyk Userbot) ===",
        "",
        "نظرة عامة:",
        f"- سورس يوزربوت يعمل على حساب شخصي (Telethon) باسم '{OWNER_NAME}'.",
        f"- البادئة (Prefix) لكل الأوامر هي: {PREFIX}",
        "- كل ميزة لها ملف json خاص في مجلد data/ للتخزين الدائم.",
        "- لا يوجد بوت مساعد، كل شيء يعمل عبر حساب الجوكر مباشرة.",
        "- يدعم الذكاء الاصطناعي (QuillBot) للرد نيابة عن الجوكر، ومولّد سب، وقسم سبام، وإدارة مجموعات، وردود، وتحكم كامل بالحساب.",
        "",
        "=== الأقسام والأوامر ===",
        "",
    ]
    for sec, txt in MENU.items():
        try:
            formatted = txt.format(p=PREFIX)
        except Exception:
            formatted = txt
        clean = formatted.replace("**", "").replace("`", "")
        lines.append(f"--- القسم {sec} ---")
        lines.append(clean)
        lines.append("")
    lines.append("=== قدرات إضافية ===")
    lines.append("- الذكاء الاصطناعي: يقرأ سياق المحادثة، يتذكر المحادثات السابقة، ويعرف كامل معلومات المرسل.")
    lines.append("- مولّد السب: يولّد ملايين الشتائم العربية الذكية من مكتبة data/insults.json.")
    lines.append("- يمكن للذكاء استخدام أوامر Telethon (MCP) للوصول إلى أي شيء في الحساب: قراءة الرسائل، إرسالها، إدارة المجموعات، البحث، إلخ.")
    lines.append("- كل ما يسأل عنه المستخدم حول السورس يجب الإجابة عليه من هذا الدليل.")
    content = "\n".join(lines)
    try:
        with open(SOURCE_INFO_PATH, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass
    return content


def load_source_info():
    if not os.path.exists(SOURCE_INFO_PATH):
        return build_source_info()
    try:
        with open(SOURCE_INFO_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _ai_rand_id():
    a = string.ascii_lowercase + string.digits
    return "".join(random.choices(a, k=11))


def _ai_request_sync(full_message):
    """طلب متزامن لـ QuillBot — يُشغّل داخل thread حتى لا يحجب البوت"""
    conn = http.client.HTTPSConnection("quillbot.com", timeout=60)
    payload = json.dumps(
        {
            "stream": True,
            "message": {
                "role": "user",
                "content": full_message,
                "messageId": _ai_rand_id(),
                "files": [],
            },
            "product": "ai-chat",
            "originUrl": "/ai-chat",
        }
    )
    accept_enc = "gzip, deflate, br" if brotli else "gzip, deflate"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11; K) AppleWebKit/537.36 (KHTML, like "
            "Gecko) Chrome/138.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/event-stream",
        "Accept-Encoding": accept_enc,
        "Content-Type": "application/json",
        "platform-type": "webapp",
        "useridtoken": "empty-token",
        "webapp-version": "27.13.2",
        "origin": "https://quillbot.com",
        "referer": "https://quillbot.com/ai-chat/c/new",
        "accept-language": "ar,en-US;q=0.8,en;q=0.7",
    }
    conn.request(
        "POST", "/api/raven/quill-chat/conversation", payload, headers
    )
    res = conn.getresponse()
    raw = res.read()
    enc = res.getheader("Content-Encoding")
    try:
        if enc == "br" and brotli:
            raw = brotli.decompress(raw)
        elif enc == "gzip":
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            raw = zlib.decompress(raw)
    except Exception:
        pass
    out = []
    for line in raw.decode("utf-8", "ignore").splitlines():
        if line.startswith("data:"):
            try:
                d = json.loads(line.split("data: ", 1)[1])
                if "chunk" in d:
                    out.append(d["chunk"])
            except Exception:
                continue
    conn.close()
    return "".join(out).strip()


AI_CONTEXT_LIMIT = 50
AI_CONTEXT_MAXCHARS = 6000
AI_MSG_MAXCHARS = 400
AI_CONTEXT_LIMIT = db_get("settings", "ai_context", AI_CONTEXT_LIMIT)
AI_MEM_LIMIT = 40
AI_MEM_MAXCHARS = 8000


def _ai_mem_key(sender_id):
    return f"mem_{sender_id}"


def ai_mem_get(sender_id):
    return db_get("ai_mem", _ai_mem_key(sender_id), [])


def ai_mem_add(sender_id, role, text):
    key = _ai_mem_key(sender_id)
    mem = db_get("ai_mem", key, [])
    mem.append({"role": role, "text": text, "t": datetime.now().strftime("%Y-%m-%d %H:%M")})
    if len(mem) > AI_MEM_LIMIT:
        mem = mem[-AI_MEM_LIMIT:]
    db_set("ai_mem", key, mem)
    return mem


def ai_mem_clear(sender_id):
    db_del("ai_mem", _ai_mem_key(sender_id))


def ai_mem_format(sender_id):
    mem = ai_mem_get(sender_id)
    if not mem:
        return ""
    out = []
    for m in mem:
        who = "المساعد" if m["role"] == "assistant" else "المرسل"
        out.append(f"[{m['t']}] {who}: {m['text']}")
    text = "\n".join(out)
    if len(text) > AI_MEM_MAXCHARS:
        text = "…\n" + text[-AI_MEM_MAXCHARS:]
    return text


async def _build_context(event):
    """يجلب آخر AI_CONTEXT_LIMIT رسالة ويبني نص المحادثة مع حدود الطول"""
    if event is None:
        return ""
    try:
        me = await client.get_me()
        lines = []
        async for msg in client.iter_messages(
            event.chat_id, limit=AI_CONTEXT_LIMIT, max_id=event.id
        ):
            body = msg.raw_text or ("[وسائط]" if msg.media else "")
            if not body:
                continue
            if len(body) > AI_MSG_MAXCHARS:
                body = body[:AI_MSG_MAXCHARS] + "…"
            if msg.sender_id == me.id:
                who = OWNER_NAME
            else:
                try:
                    s = await msg.get_sender()
                    who = get_display_name(s)
                except Exception:
                    who = "مستخدم"
            lines.append(f"{who}: {body}")
        lines.reverse()
        text = "\n".join(lines)
        if len(text) > AI_CONTEXT_MAXCHARS:
            text = "…\n" + text[-AI_CONTEXT_MAXCHARS:]
        return text
    except Exception:
        return ""


import re as _re


_RESOLVE_CACHE = {}


async def _resolve(target):
    """يحوّل معرّف/يوزر/رقم إلى كيان قابل للاستخدام في Telethon"""
    target = (target or "").strip().lstrip("@")
    if not target:
        return None
    if target in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[target]
    try:
        if target.lstrip("-").isdigit() or target.startswith("+"):
            phone = target if target.startswith("+") else "+" + target.lstrip("+")
            imp = await client(functions.contacts.ImportContactsRequest(
                contacts=[types.InputPhoneContact(client_id=0, phone=phone, first_name="x", last_name="")]))
            if imp.users:
                ent = imp.users[0]
                _RESOLVE_CACHE[target] = ent
                return ent
            if target.lstrip("+").isdigit() and not target.startswith("+"):
                try:
                    ent = await client.get_entity(int(target))
                    _RESOLVE_CACHE[target] = ent
                    return ent
                except Exception:
                    pass
            return f"__ERR__لا يوجد حساب مرتبط بهذا الرقم"
        else:
            ent = await client.get_entity(target)
        _RESOLVE_CACHE[target] = ent
        return ent
    except Exception:
        try:
            res = await client(functions.contacts.ResolveUsernameRequest(target.replace("@", "")))
            ent = res.users[0] if getattr(res, "users", None) else (res.chats[0] if getattr(res, "chats", None) else None)
            if ent:
                _RESOLVE_CACHE[target] = ent
            return ent
        except Exception as e:
            return f"__ERR__{e}"


async def _ai_execute_action(instruction, event):
    """ينفّذ أي إجراء عبر Telethon بناءً على طلب المالك ويرجع نص النتيجة"""
    ins = instruction.strip()
    try:
        m = _re.search(r"ابعت\s+(?:رسالة\s+)?(?:لـ|إلى|ل)\s+([^\:]+?)\s*[:：]\s*(.+)", ins)
        if m:
            targets = [t.strip() for t in m.group(1).strip().split(",")]
            text = m.group(2).strip()
            res = []
            for t in targets:
                ent = await _resolve(t)
                if isinstance(ent, str) and ent.startswith("__ERR__"):
                    res.append(f" {t}: {ent[7:]}")
                    continue
                try:
                    await client.send_message(ent, text)
                    res.append(f" تم الإرسال إلى {t}")
                except Exception as e:
                    res.append(f" {t}: {e}")
            return "\n".join(res)

        for kw in (r"حظر", r"بان", r"امنع"):
            m = _re.search(kw + r"\s+(?:الرقم\s+|المستخدم\s+|اليوزر\s+)?(.+)", ins)
            if m:
                ent = await _resolve(m.group(1).strip())
                if isinstance(ent, str) and ent.startswith("__ERR__"):
                    return f" تعذّر الحظر: {ent[7:]}"
                try:
                    await client(functions.contacts.BlockRequest(ent))
                    name = get_display_name(ent) if hasattr(ent, "id") else m.group(1)
                    return f" تم حظر {name} بنجاح من حسابك."
                except Exception as e:
                    return f" فشل الحظر: {e}"

        m = _re.search(r"الغاء\s+حظر\s+(?:الرقم\s+|المستخدم\s+|اليوزر\s+)?(.+)", ins)
        if m:
            ent = await _resolve(m.group(1).strip())
            if isinstance(ent, str) and ent.startswith("__ERR__"):
                return f" تعذّر: {ent[7:]}"
            try:
                await client(functions.contacts.UnblockRequest(ent))
                return f" تم إلغاء حظر {get_display_name(ent) if hasattr(ent,'id') else m.group(1)}."
            except Exception as e:
                return f" فشل: {e}"

        m = _re.search(r"اطرد\s+(?:المستخدم\s+)?(.+?)\s+(?:من\s+|في\s+)?(.+)", ins)
        if m and (_re.search(r"من\s+|في\s+", ins)):
            ent = await _resolve(m.group(1).strip())
            chat = await _resolve(m.group(2).strip())
            if isinstance(ent, str) and ent.startswith("__ERR__"):
                return f" العضو: {ent[7:]}"
            if isinstance(chat, str) and chat.startswith("__ERR__"):
                return f" المجموعة: {chat[7:]}"
            try:
                await client.kick_participant(chat, ent)
                return f" تم طرد {get_display_name(ent) if hasattr(ent,'id') else ''} من {get_display_name(chat) if hasattr(chat,'id') else ''}."
            except Exception as e:
                return f" فشل الطرد: {e}"

        if _re.search(r"ثبت|پین", ins):
            if event and event.reply_to_msg_id:
                try:
                    await client.pin_message(event.chat_id, event.reply_to_msg_id)
                    return " تم تثبيت الرسالة."
                except Exception as e:
                    return f" فشل التثبيت: {e}"

        m = _re.search(r"اقر[اأ]?\s*(?:آخر\s+)?(\d+)?\s*رسال[ةه]?\s+(?:من\s+|في\s+)?(.+)", ins)
        if m:
            limit = int(m.group(1)) if m.group(1) else 5
            target = m.group(2).strip() if m.group(2) else (event.chat_id if event else None)
            ent = await _resolve(target) if isinstance(target, str) else target
            if isinstance(ent, str) and ent.startswith("__ERR__"):
                return f" تعذّر القراءة: {ent[7:]}"
            out = []
            async for msg in client.iter_messages(ent, limit=limit):
                who = "أنت" if msg.out else (get_display_name(await msg.get_sender()) if msg.sender_id else "؟")
                out.append(f"{who}: {msg.raw_text or '[وسائط]'}")
            return " آخر الرسائل:\n" + "\n".join(reversed(out)) if out else "لا توجد رسائل"

        m = _re.search(r"امسح\s+(?:رسائل\s+)?(.+?)(?:\s+مع\s+|\s+من\s+)?(.+)?$", ins)
        if m and _re.search(r"مسح|امسح", ins):
            target = m.group(2).strip() if m.group(2) else (m.group(1).strip() if m.group(1) else None)
            if target:
                ent = await _resolve(target)
                if isinstance(ent, str) and ent.startswith("__ERR__"):
                    return f" تعذّر: {ent[7:]}"
                try:
                    await client.delete_messages(ent, None)
                    return f" تم مسح المحادثة مع {get_display_name(ent) if hasattr(ent,'id') else target}."
                except Exception as e:
                    return f" فشل المسح: {e}"

        if _re.search(r"من\s+انت|معلوماتي|حسابي|من\s+أنا", ins):
            me = await client.get_me()
            return (
                f" حسابك:\nالاسم: {get_display_name(me)}\nالمعرّف: @{me.username or 'لايوجد'}\n"
                f"الآيدي: {me.id}\nالهاتف: {getattr(me, 'phone', 'غير متاح')}\n"
                f"بريميوم: {'نعم' if getattr(me, 'premium', False) else 'لا'}"
            )

        if _re.search(r"محادثاتي|قوائمي|الدردشات|الشاتات|قائمتي", ins):
            dialogs = []
            async for d in client.iter_dialogs(limit=25):
                dialogs.append(f"- {d.name} ({d.id})")
            return " المحادثات:\n" + "\n".join(dialogs)

        m = _re.search(r"انش[ئي]?\s+(?:مجموعة\s+|قروب\s+)?(.+)", ins)
        if m:
            try:
                chat = await client(functions.channels.CreateChannelRequest(
                    title=m.group(1).strip(), about="", broadcast=False))
                cid = chat.chats[0].id
                return f" تم إنشاء مجموعة: {m.group(1).strip()} (id {cid})"
            except Exception as e:
                return f" فشل الإنشاء: {e}"

        m = _re.search(r"اضف\s+(?:المستخدم\s+)?(.+?)\s+(?:إلى\s+|لـ|ل)\s+(.+)", ins)
        if m:
            ent = await _resolve(m.group(1).strip())
            chat = await _resolve(m.group(2).strip())
            if isinstance(ent, str) and ent.startswith("__ERR__"):
                return f" العضو: {ent[7:]}"
            if isinstance(chat, str) and chat.startswith("__ERR__"):
                return f" المجموعة: {chat[7:]}"
            try:
                await client(functions.channels.InviteToChannelRequest(chat, [ent]))
                return f" تمت دعوة {get_display_name(ent) if hasattr(ent,'id') else ''} إلى {get_display_name(chat) if hasattr(chat,'id') else ''}."
            except Exception as e:
                return f" فشل الدعوة: {e}"

        m = _re.search(r"ابحث\s+(?:عن\s+)?(.+)", ins)
        if m:
            ent = await _resolve(m.group(1).strip())
            if isinstance(ent, str) and ent.startswith("__ERR__"):
                return f" لم أجد: {ent[7:]}"
            if hasattr(ent, "id"):
                return f" وُجد: {get_display_name(ent)} | @{getattr(ent,'username',None) or 'لايوجد'} | id {ent.id}"
            return f" وُجد كيان: {ent}"

        m = _re.search(r"(?:من\s+هذا|من\s+هو|من\s+هي|معلومات\s+(?:المستخدم\s+|الرقم\s+)?|من\s+يكون)\s*(.+)?", ins)
        if m and (m.group(1) or _re.search(r"من\s+هذا|من\s+هو", ins)):
            ent = await _resolve((m.group(1) or "").strip())
            if isinstance(ent, str) and ent.startswith("__ERR__"):
                return f" تعذّر: {ent[7:]}"
            if hasattr(ent, "id"):
                return (f" {get_display_name(ent)}\nالمعرّف: @{getattr(ent,'username',None) or 'لايوجد'}\n"
                        f"الآيدي: {ent.id}\nبريميوم: {'نعم' if getattr(ent,'premium',False) else 'لا'}\n"
                        f"موثّق: {'نعم' if getattr(ent,'verified',False) else 'لا'}\nالبايو: {getattr(ent,'about','لايوجد') or 'لايوجد'}")
            return f"ℹ {ent}"

        if _re.search(r"قنواتي|المشرف\s+بها|اديرها|مالك\s+او\s+مشرف|املكها|قنوات\s+التي|مجموعاتي", ins):
            me = await client.get_me()
            owned = []
            admin = []
            try:
                async for d in client.iter_dialogs(limit=200):
                    ent = d.entity
                    if not (getattr(ent, "megagroup", False) or getattr(ent, "broadcast", False)):
                        continue
                    title = getattr(ent, "title", "بدون اسم")
                    try:
                        full = await client(functions.channels.GetFullChannelRequest(ent))
                        participant = full.full_chat.participants
                        if getattr(participant, "admin", False):
                            admin.append(title)
                        elif getattr(participant, "admin_rights", None):
                            admin.append(title)
                        else:
                            admins = [p.user_id for p in getattr(full.full_chat, "admins", None) or []]
                            if me.id in admins:
                                admin.append(title)
                    except Exception:
                        pass
            except Exception:
                pass
            if not owned and not admin:
                return " لا توجد قنوات/مجموعات تملكها أو تديرها (أو تعذّر الفحص)."
            parts = []
            if owned:
                parts.append("المالك:\n" + "\n".join(f"- {t}" for t in owned[:50]))
            if admin:
                parts.append("مشرف:\n" + "\n".join(f"- {t}" for t in admin[:50]))
            return "\n\n".join(parts)

        if _re.search(r"عدد\s+المحادثات|كم\s+محادثة|عدد\s+الدردشات", ins):
            n = 0
            async for _ in client.iter_dialogs():
                n += 1
            return f" عدد محادثاتك: {n}"

        if _re.search(r"بحث\s+في\s+المحادثات|دور\s+على\s+(.+)|ابحث\s+لي\s+على\s+(.+)", ins):
            q = None
            mq = _re.search(r"بحث\s+في\s+المحادثات\s+(.+)", ins) or _re.search(r"دور\s+على\s+(.+)", ins) or _re.search(r"ابحث\s+لي\s+على\s+(.+)", ins)
            if mq:
                q = mq.group(1).strip()
            if q:
                found = []
                async for d in client.iter_dialogs(limit=200):
                    if q in (d.name or ""):
                        found.append(f"- {d.name} ({d.id})")
                return " المحادثات المطابقة:\n" + "\n".join(found[:50]) if found else " لا توجد نتائج."

        return None
    except Exception as e:
        return f" خطأ بالتنفيذ: {e}"


async def ai_ask(question, event=None, owner_chat=False, with_tools=False):
    """يبني التعليمات + السياق ويرسل السؤال ويرجع الرد"""
    prompt = _ai_load()["prompt"]
    ctx = {
        "owner": OWNER_NAME,
        "me_name": "",
        "me_id": "",
        "me_user": "",
        "sender_name": "مستخدم",
        "sender_id": "",
        "sender_user": "لايوجد",
        "sender_first": "",
        "sender_last": "",
        "sender_phone": "غير متاح",
        "sender_bio": "لايوجد",
        "sender_premium": "لا",
        "sender_bot": "لا",
        "sender_lang": "غير معروف",
        "sender_verified": "لا",
        "sender_status": "غير معروف",
        "sender_common": 0,
        "sender_blocked": "لا",
        "chat_kind": "محادثة",
        "chat_title": "",
        "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        me = await client.get_me()
        ctx["me_name"] = get_display_name(me)
        ctx["me_id"] = me.id
        ctx["me_user"] = me.username or "لايوجد"
    except Exception:
        pass
    if event is not None:
        try:
            sender = await event.get_sender()
            ctx["sender_name"] = get_display_name(sender)
            ctx["sender_id"] = getattr(sender, "id", "")
            ctx["sender_user"] = getattr(sender, "username", "") or "لايوجد"
            ctx["sender_first"] = getattr(sender, "first_name", "") or ""
            ctx["sender_last"] = getattr(sender, "last_name", "") or ""
            ctx["sender_phone"] = getattr(sender, "phone", "") or "غير متاح"
            ctx["sender_bio"] = getattr(sender, "about", "") or "لايوجد"
            ctx["sender_premium"] = "نعم" if getattr(sender, "premium", False) else "لا"
            ctx["sender_bot"] = "نعم" if getattr(sender, "bot", False) else "لا"
            ctx["sender_lang"] = getattr(sender, "lang_code", "") or "غير معروف"
            ctx["sender_verified"] = "نعم" if getattr(sender, "verified", False) else "لا"
            ctx["sender_status"] = str(getattr(sender, "status", "") or "غير معروف")
            try:
                pfull = await client(functions.users.GetFullUserRequest(sender))
                full = getattr(pfull, "full_user", None)
                if full is not None:
                    bio = getattr(full, "about", "")
                    if bio:
                        ctx["sender_bio"] = bio
                    ctx["sender_common"] = getattr(full, "common_chats_count", 0)
                    ctx["sender_blocked"] = "نعم" if getattr(full, "blocked", False) else "لا"
            except Exception:
                pass
            if event.is_private:
                ctx["chat_kind"] = "الخاص"
            elif event.is_group:
                ctx["chat_kind"] = "مجموعة"
                chat = await event.get_chat()
                t = getattr(chat, "title", "")
                ctx["chat_title"] = f" ({t})" if t else ""
        except Exception:
            pass
    try:
        system = prompt.format(**ctx)
    except Exception:
        system = prompt
    context = await _build_context(event)
    sender_id = ctx.get("sender_id") or "unknown"
    memory = ai_mem_format(sender_id)
    source_info = load_source_info()
    parts = [f"[تعليمات النظام]\n{system}"]
    if source_info:
        parts.append(f"[دليل سورس الجوكر — كل ما يجب أن تعرفه عن السورس]\n{source_info}")
    if context:
        parts.append(f"[سياق المحادثة السابقة — آخر {AI_CONTEXT_LIMIT} رسالة]\n{context}")
    if memory:
        parts.append(f"[ذاكرة المحادثة مع هذا الشخص — ما تذكرته سابقاً]\n{memory}")
    if owner_chat:
        ochat = ai_mem_format("chat_owner")
        if ochat:
            parts.append(f"[محادثتك السابقة مع المالك — لكي تكمل/تصحّح بناءً عليها]\n{ochat}")
    if with_tools:
        tools = _ai_tools_list()
        tools_txt = json.dumps(tools, ensure_ascii=False, indent=1)
        catalog = _ai_functions_catalog()
        parts.append(
            "[قدرة تنفيذ Telethon — لديك صلاحية تنفيذ أي دالة على حساب المالك بلا قيود]\n"
            "لتشغيل أي إجراء اكتب كتلة JSON بصيغة:\n"
            "```json\n{\"name\": \"<اسم_الوحدة>.اسم_الدالة\", \"parameters\": { ... }}\n```\n"
            "مثال: {\"name\": \"channels.GetFullChannelRequest\", \"parameters\": {\"channel\": \"@username\"}}\n"
            "أو استخدم الأسماء العربية: {\"name\": \"كشف\", \"parameters\": {\"user\": 123}}\n"
            "يمكنك إرجاع عدة استدعاءات دفعة واحدة، وتجربة أكثر من دالة حتى تنجز المطلوب.\n"
            "لا تشرح ما ستفعله فقط — نفّذ فعلياً ثم اشرح النتيجة بلا أكواد.\n"
            "أشهر الوحدات المتاحة:\n"
            f"{catalog}\n"
            f"قائمة أدوات سريعة إضافية:\n{tools_txt}"
        )
    parts.append(f"[رسالة المستخدم الحالية]\n{question}")
    full = "\n\n".join(parts)
    answer = await asyncio.to_thread(_ai_request_sync, full)
    if answer:
        ai_mem_add(sender_id, "user", question)
        ai_mem_add(sender_id, "assistant", answer)
    return answer


@cmd(r"ذكاء تشغيل$")
async def _(event):
    db_set("settings", "ai_auto", True)
    await edit_or_reply(event, "تم تشغيل وضع محادثة الذكاء بالخاص ✓")
    raise events.StopPropagation()


@cmd(r"ذكاء تعطيل$")
async def _(event):
    db_set("settings", "ai_auto", False)
    await edit_or_reply(event, "تم تعطيل وضع محادثة الذكاء ✓")
    raise events.StopPropagation()


@cmd(r"ذكاء سياق(?:\s|$)([\s\S]*)")
async def _(event):
    global AI_CONTEXT_LIMIT
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg.isdigit():
        await edit_delete(
            event, f"- اكتب: {PREFIX}ذكاء سياق <عدد الرسائل>\nالحالي: {AI_CONTEXT_LIMIT}", 8
        )
        raise events.StopPropagation()
    AI_CONTEXT_LIMIT = min(int(arg), 200)
    db_set("settings", "ai_context", AI_CONTEXT_LIMIT)
    await edit_or_reply(event, f"تم ضبط عدد رسائل السياق إلى {AI_CONTEXT_LIMIT} ✓")
    raise events.StopPropagation()


@cmd(r"ذكاء مفعل$")
async def _(event):
    db_set("settings", "ai_full", True)
    db_set("settings", "ai_auto", False)
    build_source_info()
    await edit_or_reply(
        event,
        "تم تفعيل وضع الذكاء الشامل (لأمر .ذكاء فقط، للمالك) ✓\n"
        "• يعرف دليل السورس كاملاً ويجيب عن أي سؤال\n"
        "• يتذكر محادثاتك السابقة\n"
        "• يملك كامل معلومات المرسل\n"
        "• ينفّذ أوامر Telethon فعلياً ويرد بنتيجة كل إجراء\n"
        "• الرد التلقائي بالخاص معطّل (هذا الوضع للأمر المباشر)",
    )
    raise events.StopPropagation()


@cmd(r"ذكاء ذاكرة(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    sender = await event.get_sender()
    sid = getattr(sender, "id", "unknown")
    if arg in ("مسح", "حذف", "clear"):
        ai_mem_clear(sid)
        await edit_or_reply(event, "تم مسح ذاكرة المحادثة ✓")
        raise events.StopPropagation()
    mem = ai_mem_format(sid)
    if not mem:
        await edit_or_reply(event, "لا توجد ذاكرة محادثة بعد لهذا الشخص")
        raise events.StopPropagation()
    await edit_or_reply(event, f"**ذاكرة المحادثة:**\n\n{mem}")
    raise events.StopPropagation()


@cmd(r"ذكاء جلسة(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if arg in ("مسح", "حذف", "clear"):
        ai_mem_clear("chat_owner")
        await edit_or_reply(event, "تم مسح جلسة المحادثة التفاعلية ✓")
        raise events.StopPropagation()
    mem = ai_mem_format("chat_owner")
    if not mem:
        await edit_or_reply(event, "لا توجد جلسة محادثة بعد")
        raise events.StopPropagation()
    await edit_or_reply(event, f"**جلسة المحادثة التفاعلية:**\n\n{mem}")
    raise events.StopPropagation()


@cmd(r"دليل الذكاء$")
async def _(event):
    txt = build_source_info()
    n = len(txt)
    await edit_or_reply(event, f"تم توليد دليل السورس ✓\nالملف: data/source_info.txt\nعدد الأحرف: {n}")
    raise events.StopPropagation()


@cmd(r"ادوات الذكاء$")
async def _(event):
    tools = _ai_tools_list()
    await edit_or_reply(event, f"عدد أدوات Telethon المعرّفة: {len(tools)}\nالملف: data/ai_tools.json\nأمر .ذكاء مفعل لتفعيل التنفيذ الحر")
    raise events.StopPropagation()


@cmd(r"تعليمات الذكاء(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        cur = _ai_load()["prompt"]
        await edit_or_reply(
            event,
            f"**| تعليمات الذكاء الحالية:**\n\n`{cur}`\n\n"
            f"للتعديل: `{PREFIX}تعليمات الذكاء <النص>`\n"
            f"للإرجاع: `{PREFIX}تعليمات الذكاء افتراضي`",
        )
        raise events.StopPropagation()
    if arg == "افتراضي":
        db_set("ai", "prompt", _DEFAULT_AI_PROMPT)
        await edit_or_reply(event, "تم إرجاع التعليمات الافتراضية ✓")
        raise events.StopPropagation()
    data = _ai_load()
    data["prompt"] = arg
    db_write("ai", data)
    await edit_or_reply(event, "تم تحديث تعليمات الذكاء ✓")
    raise events.StopPropagation()


@cmd(r"ذكاء(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    if not arg and reply and reply.text:
        arg = reply.text
    if not arg:
        return await edit_delete(event, f"- اكتب: {PREFIX}ذكاء <سؤالك>", 8)
    m = await event.edit(" جاري التفكير...")
    try:
        with_tools = True
        answer = await ai_ask(arg, event, owner_chat=True, with_tools=with_tools)
        if not answer:
            return await m.edit("- لم أحصل على رد، حاول مرة أخرى")
        ai_mem_add("chat_owner", "user", arg)
        ai_mem_add("chat_owner", "assistant", answer)
        final_reply = None
        current = answer
        for round_no in range(4):
            calls = _ai_parse_tool_calls(current)
            if calls:
                results = []
                for call in calls:
                    res = await _ai_run_tool(call)
                    results.append(f"[{call.get('name')}] {res}")
                follow = await ai_ask(
                    "[نتائج تنفيذ أدواتك — راجعها وحدد إن كنت تحتاج محاولة أخرى أو تنفيذ المزيد]:\n"
                    + "\n".join(results) +
                    "\nإن اكتمل المطلوب اشرح للمالك النتيجة بوضوح بلا أكواد. وإن فشل شيء جرّب اسماً آخر أو دالة أقرب.",
                    event, owner_chat=True, with_tools=with_tools)
                if not follow:
                    final_reply = current
                    break
                ai_mem_add("chat_owner", "assistant", follow)
                if not _ai_parse_tool_calls(follow):
                    final_reply = follow
                    break
                current = follow
                continue
            direct = await _ai_execute_action(arg, event)
            if not direct:
                direct = await _ai_execute_action(current, event)
            if direct:
                final_reply = f"{current}\n\n{direct}"
            else:
                final_reply = current
            break
        if not final_reply:
            final_reply = current
        final_reply = re.sub(r"```json.*?```", "", final_reply, flags=re.DOTALL).strip()
        final_reply += "\n\n__محادثة مستمرة — اكتب .ذكاء للمتابعة/التصحيح__"
        await edit_or_reply(m, final_reply)
    except Exception as e:
        await edit_or_reply(m, f"- خطأ بالذكاء: `{e}`")




def _bc_extract(text):
    text = (text or "").strip().replace("https://", "").replace("http://", "")
    if "+" in text or "/joinchat/" in text:
        return ("invite", text.split("+")[-1].split("/")[-1])
    m = _re.match(r"t\.me/(.+?)(?:/|$)", text)
    if m:
        return ("username", m.group(1))
    if text.startswith("@"):
        return ("username", text[1:])
    if _re.match(r"^-?\d+$", text):
        return ("chat_id", int(text))
    if text:
        return ("username", text)
    return None


def _bc_name(entity):
    if isinstance(entity, User):
        n = (getattr(entity, "first_name", "") + " " + getattr(entity, "last_name", "")).strip()
        return n or str(getattr(entity, "id", "؟"))
    return str(getattr(entity, "title", "") or getattr(entity, "id", "؟"))


def _bc_type(entity):
    if isinstance(entity, User):
        return "user"
    if getattr(entity, "broadcast", False):
        return "channel"
    if getattr(entity, "megagroup", False):
        return "group"
    return "chat"


def _bc_tos(entity, name=None):
    if name is None:
        name = _bc_name(entity) or "؟"
    name = str(name)
    for r in (getattr(entity, "restriction_reason", []) or []):
        if getattr(r, "reason", "") == "terms":
            return (
                "Warning هذه المجموعة محظورة لانتهاكها شروط خدمة تيليجرام (TOOLTIP).\n"
                f"  → {name}"
            )
    return None


def _bc_translate(res):
    """يحوّل نتيجة الفحص لعربية واضحة"""
    if res is None:
        return " سليم | لا يوجد حظر"
    if res.startswith("OK|"):
        _, t, name = (res.split("|", 2) + ["", ""])[:3]
        return f" سليم | النوع: {t} | الاسم: {name}"
    if res == "BANNED_OR_NOT_FOUND":
        return " محظور أو غير موجود"
    if res == "BANNED_OR_PRIVATE":
        return " محظور أو خاص"
    if res == "BANNED":
        return " محظور (BANNED)"
    if res == "BANNED_YOU":
        return " محظور أنت فيه"
    if res == "BANNED_OR_EXPIRED":
        return "⏰ الرابط منتهٍ أو محظور"
    if res == "BANNED_OR_INVALID":
        return " الرابط غير صالح أو محظور"
    if res == "INVALID_USER_ID":
        return " معرّف مستخدم غير صالح"
    if res == "NOT_FOUND":
        return "🔍 غير موجود"
    if res == "FULL":
        return " المجموعة ممتلئة"
    if res == "EXPIRED":
        return "⏰ الرابط منتهٍ الصلاحية"
    if res.startswith("SCAM_FAKE|"):
        parts = res.split("|", 1)
        return f" رابط وهمي/نصب (SCAM): {parts[1] if len(parts) > 1 else '؟'}"
    if res.startswith("TOOLTIP:"):
        return " " + res.replace("TOOLTIP:", "").strip().replace("None", "؟")
    if res.startswith("ERROR"):
        return "Warning " + res
    if res.startswith("FLOOD_WAIT"):
        return "⏳ " + res
    return res.replace("None", "؟")


async def _bc_check_entity(identifier):
    try:
        entity = await client.get_entity(identifier)
    except UsernameNotOccupiedError:
        return "BANNED_OR_NOT_FOUND"
    except ChannelPrivateError:
        return "BANNED_OR_PRIVATE"
    except ChannelBannedError:
        return "BANNED"
    except UserIdInvalidError:
        return "INVALID_USER_ID"
    except ValueError:
        return "NOT_FOUND"
    except Exception:
        return "NOT_FOUND"
    msg = _bc_tos(entity)
    if msg:
        return msg
    return f"OK|{_bc_type(entity)}|{_bc_name(entity)}"


async def _bc_check_invite(hashv):
    try:
        result = await client(CheckChatInviteRequest(hash=hashv))
    except InviteHashExpiredError:
        return "BANNED_OR_EXPIRED"
    except InviteHashInvalidError:
        return "BANNED_OR_INVALID"
    except ChannelPrivateError:
        return "BANNED_OR_PRIVATE"
    except ChannelBannedError:
        return "BANNED"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
    if isinstance(result, ChatInviteAlready):
        entity = getattr(result, "chat", None)
        if entity:
            msg = _bc_tos(entity)
            if msg:
                return msg
            return f"OK|{_bc_type(entity)}|{_bc_name(entity)}"
        return "OK|chat|MEMBER"
    if isinstance(result, ChatInvite):
        title = str(getattr(result, "title", "?") or "?")
        if getattr(result, "scam", False) or getattr(result, "fake", False):
            return f"SCAM_FAKE|{title}"
        try:
            await client(ImportChatInviteRequest(hash=hashv))
            return f"OK|{('channel' if getattr(result, 'channel', False) else 'group')}|{title}"
        except ChannelPrivateError:
            return f"TOOLTIP: This group can't be displayed because it violated Telegram's Terms of Service.\n  -> {title}"
        except ChannelBannedError:
            return f"BANNED|{title}"
        except UserBannedInChannelError:
            return f"BANNED_YOU|{title}"
        except UsersTooMuchError:
            return f"FULL|{title}"
        except InviteHashExpiredError:
            return f"EXPIRED|{title}"
        except Exception as e:
            return f"ERROR: {e}"
    return "ERROR: Unknown response"


async def _bc_check(target):
    parsed = _bc_extract(target)
    if not parsed:
        return " مدخل غير صالح"
    kind, value = parsed
    try:
        if kind == "invite":
            return await _bc_check_invite(value)
        return await _bc_check_entity(value)
    except FloodWaitError as e:
        return f"FLOOD_WAIT: wait {e.seconds}s"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


@cmd(r"فحص(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        up = readable_time(time.time() - START_TIME)
        me = await event.client.get_me()
        txt = f"""**[ سورس الجوكر ]**
=========================

**الحالة:** يعمل ✓
**المالك:** {OWNER_NAME}
**الحساب:** {get_display_name(me)}
**البادئة:** `{PREFIX}`
**مدة التشغيل:** {up}
 **المكتبة:** Telethon
 **التخزين:** JSON

 لعرض الأوامر أرسل `{PREFIX}الاوامر`
 للتحديثات والتحسينات اشترك: https://t.me/rkkyk"""
        return await edit_or_reply(event, txt)
    m = await event.edit("🔍 جاري الفحص...")
    res = await _bc_check(arg)
    await edit_or_reply(m, _bc_translate(res))


@cmd(r"فحص_دفعه(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        return await edit_delete(event, f"- اكتب: {PREFIX}فحص_دفعه <رابط دعوة>", 8)
    m = await event.edit("🔍 جاري فحص الدعوة...")
    parsed = _bc_extract(arg)
    if not parsed or parsed[0] != "invite":
        return await edit_or_reply(m, " هذا ليس رابط دعوة صالحاً")
    res = await _bc_check_invite(parsed[1])
    await edit_or_reply(m, _bc_translate(res))


@cmd(r"فحص_مجموعه$")
async def _(event):
    m = await event.edit("🔍 جاري فحص المجموعة الحالية...")
    try:
        entity = await event.get_chat()
        res = _bc_tos(entity)
        if res:
            out = res
        else:
            out = f"OK|{_bc_type(entity)}|{_bc_name(entity)}"
    except Exception as e:
        out = f"ERROR: {e}"
    await edit_or_reply(m, _bc_translate(out))



REPORT_REASONS = {
    "سبام": "spam",
    "اباحي": "porn",
    "عنف": "violence",
    "تحرش": "child_abuse",
    "حقوق": "copyright",
    "وهمي": "fake",
    "غير_قانوني": "illegal",
    "اخر": "other",
    "spam": "spam",
    "porn": "porn",
    "violence": "violence",
    "child_abuse": "child_abuse",
    "copyright": "copyright",
    "fake": "fake",
    "illegal": "illegal",
    "other": "other",
}

REPORT_REASON_OBJS = {
    "spam": types.InputReportReasonSpam,
    "porn": types.InputReportReasonPornography,
    "pornography": types.InputReportReasonPornography,
    "violence": types.InputReportReasonViolence,
    "child_abuse": types.InputReportReasonChildAbuse,
    "copyright": types.InputReportReasonCopyright,
    "fake": types.InputReportReasonFake,
    "illegal": types.InputReportReasonIllegalDrugs,
    "illegal_drugs": types.InputReportReasonIllegalDrugs,
    "other": types.InputReportReasonOther,
}


def _report_reason_obj(name):
    key = REPORT_REASONS.get((name or "spam").lower(), "spam")
    return REPORT_REASON_OBJS.get(key, types.InputReportReasonSpam)()


def _report_settings():
    """إعدادات البلاغ المحفوظة"""
    s = db_read("report_cfg", {})
    s.setdefault("reason", "spam")
    s.setdefault("message", "محتوى مخالف لشروط تيليجرام")
    s.setdefault("speed", 3)
    s.setdefault("target", "")
    s.setdefault("running", False)
    return s


_REPORT_OPTIONS = {
    "spam": b"0",
    "abuse": b"1",
    "porn": b"2",
    "pornography": b"2",
    "violence": b"4",
    "drugs": b"5",
    "copyright": b"10",
    "other": b"8",
    "child_abuse": b"9",
    "fake": b"7",
    "illegal": b"6",
    "illegal_drugs": b"6",
}


async def _do_report(peer_entity, reason_name, message, msg_id=None):
    """ينفّذ بلاغاً واحداً ويرجع True أو نص الخطأ"""
    reason = _report_reason_obj(reason_name)
    option = _REPORT_OPTIONS.get((reason_name or "spam").lower(), b"1")
    try:
        if msg_id is not None:
            await client(functions.messages.ReportRequest(
                peer=peer_entity,
                id=[int(msg_id)],
                option=option,
                message=message,
            ))
        else:
            await client(functions.account.ReportPeerRequest(
                peer=peer_entity,
                reason=reason,
                message=message,
            ))
        return True
    except Exception as e:
        return f"ERR:{e}"


def _extract_entity_from_url(url):
    """يستخرج اسم المستخدم/القناة من رابط تيليجرام (ي处理 روابط الرسائل أيضاً)"""
    import re
    m = re.search(r't\.me/(?:s/)?([^/?]+)', url or "")
    if m:
        return m.group(1)
    return url


def _extract_msg_id_from_url(url):
    """يستخرج رقم الرسالة من رابط تيليجرام إن وُجد"""
    import re
    m = re.search(r't\.me/(?:s/)?[^/?]+/(\d+)', url or "")
    if m:
        return int(m.group(1))
    return None


def _peer_report_link(chat_id, msg_id):
    """يبني رابط رسالة للبلاغ لأي نوع: خاص/مجموعة/قناة، عامة أو خاصة"""
    try:
        pid = int(chat_id)
    except Exception:
        return ""
    if pid > 0:
        return f"https://t.me/c/{pid}/{msg_id}"
    s = str(pid)
    if s.startswith("-100"):
        s = s[4:]
    elif s.startswith("-"):
        s = s[1:]
    return f"https://t.me/c/{s}/{msg_id}"


async def _target_still_alive(target):
    """يتحقق هل الهدف لم يُحظر بعد من تيليجرام (مثل .فحص).
    يرجع (True, entity) إن لم يُحظر، أو (False, رسالة_السبب) إن حُظر/انتهى/مفقود."""
    try:
        resolved = _extract_entity_from_url(target)
        ent = await _ai_resolve_ent(resolved)
        if ent is None:
            return False, " تعذّر إيجاد الهدف (ممكن محظور أو محذوف)"
        try:
            await client.get_permissions(ent) if getattr(ent, "megagroup", False) or getattr(ent, "broadcast", False) else None
        except Exception:
            pass
        return True, ent
    except Exception as e:
        err = str(e)
        if any(k in err for k in ("banned", "deactivated", "not exist", "notExist", "You can't", "CHANNEL_PRIVATE", "USER_BANNED_IN_CHANNEL", "timeout")):
            return False, f"X الهدف محظور/غير متاح الآن: {err}"
        return False, f"X خطأ في فحص الهدف: {err}"


@cmd(r"شد_هدف(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    cfg = _report_settings()
    cfg["target"] = arg
    db_write("report_cfg", cfg)
    await edit_or_reply(event, f" تم ضبط الهدف: {arg or 'لايوجد'}")


@cmd(r"شد_نوع(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        return await edit_delete(event, f"- اكتب: {PREFIX}شد_نوع <نوع>", 8)
    if arg.lower() not in REPORT_REASONS:
        return await edit_or_reply(event, " نوع غير معروف. الأنواع: " + ", ".join(REPORT_REASONS.keys()))
    cfg = _report_settings()
    cfg["reason"] = arg.lower()
    db_write("report_cfg", cfg)
    await edit_or_reply(event, f" تم ضبط نوع البلاغ: {arg}")


@cmd(r"شد_رساله(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        return await edit_delete(event, f"- اكتب: {PREFIX}شد_رساله <نص البلاغ>", 8)
    cfg = _report_settings()
    cfg["message"] = arg
    db_write("report_cfg", cfg)
    await edit_or_reply(event, f" تم ضبط رسالة البلاغ:\n{arg}")


@cmd(r"شد_سرعه(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg.isdigit():
        return await edit_delete(event, f"- اكتب: {PREFIX}شد_سرعه <ثواني التأخير>", 8)
    cfg = _report_settings()
    cfg["speed"] = max(1, min(int(arg), 60))
    db_write("report_cfg", cfg)
    await edit_or_reply(event, f" سرعة البلاغ (تأخير): {cfg['speed']} ثانية")


@cmd(r"شد_ايقاف$")
async def _(event):
    cfg = _report_settings()
    cfg["running"] = False
    db_write("report_cfg", cfg)
    await edit_or_reply(event, " تم طلب إيقاف البلاغ المستمر")


@cmd(r"شد_اعداد$")
async def _(event):
    cfg = _report_settings()
    await edit_or_reply(
        event,
        f"**| إعدادات الشد الداخلي:**\n"
        f"الهدف: {cfg['target'] or 'لايوجد'}\n"
        f"النوع: {cfg['reason']}\n"
        f"الرسالة: {cfg['message']}\n"
        f"السرعة: {cfg['speed']} ثانية\n"
        f"يعمل الآن: {'نعم' if cfg['running'] else 'لا'}\n\n"
        f"الأوامر:\n"
        f"`{PREFIX}شد_هدف` <رابط/يوزر>\n"
        f"`{PREFIX}شد_نوع` <نوع>\n"
        f"`{PREFIX}شد_رساله` <نص>\n"
        f"`{PREFIX}شد_سرعه` <ثواني>\n"
        f"`{PREFIX}شد` <رابط/يوزر> أو رد على رسالة | يبدأ البلاغ\n"
        f"`{PREFIX}شد_ايقاف` | يوقفه",
    )


@cmd(r"شد(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    cfg = _report_settings()

    target = None
    reply_peer = None
    reply_msg_id = None

    if reply is not None:
        try:
            reply_peer = await event.get_input_chat()
        except Exception:
            reply_peer = None
        reply_msg_id = reply.id
        if reply_peer is not None:
            target = _peer_report_link(event.chat_id, reply_msg_id)
            cfg["target"] = target

    if reply_peer is None:
        target = arg or cfg["target"]
        if not target:
            return await edit_delete(event, f"- اكتب: {PREFIX}شد <رابط/يوزر/آيدي> أو رد على رسالة", 8)
        cfg["target"] = target

    cfg["running"] = True
    db_write("report_cfg", cfg)
    m = await event.edit(
        f" بدء البلاغ المستمر على:\n{target}\nالنوع: {cfg['reason']}\nالسرعة: {cfg['speed']}ث\n"
        f"(سيُوقف تلقائياً إذا حُظر الهدف — أو بـ {PREFIX}شد_ايقاف)"
    )
    sent = 0
    err_count = 0
    while True:
        cfg = _report_settings()
        if not cfg.get("running", False):
            await edit_or_reply(m, f" تم الإيقاف بطلبك.\n بلاغات مُرسلة: {sent}")
            return
        try:
            if reply_peer is not None and reply_msg_id is not None:
                r = await _do_report(reply_peer, cfg["reason"], cfg["message"], msg_id=reply_msg_id)
            else:
                alive, res = await _target_still_alive(target)
                if not alive:
                    await edit_or_reply(m, f"X توقّف البلاغ تلقائياً:\n{res}\n بلاغات مُرسلة: {sent}")
                    cfg = _report_settings()
                    cfg["running"] = False
                    db_write("report_cfg", cfg)
                    return
                ent = res
                msg_id = _extract_msg_id_from_url(target)
                r = await _do_report(ent, cfg["reason"], cfg["message"], msg_id=msg_id)
        except Exception as e:
            r = f"ERR:{e}"
        if r is True:
            sent += 1
            err_count = 0
            try:
                await m.edit(f" بلاغ مستمر...\n مُرسل: {sent}\nالنوع: {cfg['reason']}\nالسرعة: {cfg['speed']}ث")
            except Exception:
                pass
        else:
            err_count += 1
            await edit_or_reply(m, f"Warning خطأ في البلاغ ({err_count}): {r}\n مُرسل: {sent}")
            if err_count >= 5:
                cfg = _report_settings()
                cfg["running"] = False
                db_write("report_cfg", cfg)
                return await edit_or_reply(m, f"X توقّف بعد أخطاء متتالية.\n بلاغات مُرسلة: {sent}")
        await asyncio.sleep(cfg["speed"])


flushing = {"working": False, "mode": "api", "users": [], "usernames": {}}


@cmd(r"تفليش$", groups_only=True)
async def _(event):
    if flushing["working"]:
        return await edit_delete(event, "- العملية جارية بالفعل...", 6)
    flushing["mode"] = "api"
    await edit_or_reply(event, f" بدأت سحب الضحايا (وضع API المباشر).. اصبر\n(`{PREFIX}وقف` للإيقاف)")
    await _flush_run(event)


@cmd(r"تفلش2$", groups_only=True)
async def _(event):
    if flushing["working"]:
        return await edit_delete(event, "- العملية جارية بالفعل...", 6)
    flushing["mode"] = "bot_user"
    await edit_or_reply(event, f" بدأت سحب الضحايا (للبوت باليوزر).. اصبر\n(`{PREFIX}وقف` للإيقاف)")
    await _flush_run(event)


@cmd(r"تفلش$", groups_only=True)
async def _(event):
    if flushing["working"]:
        return await edit_delete(event, "- العملية جارية بالفعل...", 6)
    flushing["mode"] = "bot"
    await edit_or_reply(event, f" بدأت سحب الضحايا (للبوت بالآيدي).. اصبر\n(`{PREFIX}وقف` للإيقاف)")
    await _flush_run(event)


@cmd(r"وقف$")
async def _(event):
    if not flushing["working"]:
        return await edit_delete(event, "- لا توجد عملية جارية", 6)
    flushing["working"] = False
    await edit_or_reply(event, " تم طلب الإيقاف ✓")


async def _flush_run(event):
    flushing["working"] = True
    flushing["users"] = []
    flushing["usernames"] = {}
    collected = 0
    total = 0
    try:
        me = await client.get_me()
        my_id = me.id
    except Exception:
        my_id = None
    try:
        async for u in client.iter_participants(event.chat_id):
            if not flushing["working"]:
                break
            if my_id and u.id == my_id:
                continue
            flushing["users"].append(u.id)
            if getattr(u, "username", None):
                flushing["usernames"][u.id] = u.username
            collected += 1
            if collected % 200 == 0:
                try:
                    await event.edit(f" جمع الأعضاء... `{collected}`")
                except Exception:
                    pass
        try:
            await event.edit(f" تم جمع `{len(flushing['users'])}` عضو. جاري التفليش...")
        except Exception:
            pass
        if flushing["mode"] == "api":
            total = await _flush_api(event)
        else:
            total = await _flush_bot(event)
        state = " اكتمل التفليش" if flushing["working"] else " أُوقفت العملية"
        await edit_or_reply(event, f"{state} ✓\nأُرسلت أو طُردت: {total}")
    except Exception as e:
        await edit_or_reply(event, f"X خطأ في التفليش:\n`{e}`")
    finally:
        flushing["working"] = False


async def _flush_api(event):
    count = 0
    for uid in flushing["users"]:
        if not flushing["working"]:
            break
        try:
            if getattr(event.chat, "megagroup", False) or getattr(event.chat, "broadcast", False):
                rights = ChatBannedRights(until_date=0, view_messages=True)
                await client(functions.channels.EditBannedRequest(
                    channel=event.chat, participant=uid, banned_rights=rights
                ))
            else:
                await client(functions.messages.DeleteChatUserRequest(
                    chat_id=event.chat_id, user_id=uid
                ))
            count += 1
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception:
            pass
        await asyncio.sleep(0.9)
    return count


async def _flush_bot(event):
    count = 0
    for uid in flushing["users"]:
        if not flushing["working"]:
            break
        username = flushing["usernames"].get(uid)
        if flushing["mode"] == "bot_user" and username:
            text = f"حظر @{username}"
        else:
            text = f"حظر {uid}"
        try:
            await client.send_message(event.chat_id, text)
            count += 1
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception:
            pass
        await asyncio.sleep(0.3)
        if count % 20 == 0:
            await asyncio.sleep(2.0)
    return count


DIGIT_SETS = {
    0:  {"name": "عادي",         "map": "0123456789"},
    1:  {"name": "محاط بدائرة",    "map": "⓪①②③④⑤⑥⑦⑧⑨"},
    2:  {"name": "محاط مليان",     "map": "⓿❶❷❸❹❺❻❼❽❾"},
    3:  {"name": "فوق الخط",       "map": "⁰¹²³⁴⁵⁶⁷⁸⁹"},
    4:  {"name": "تحت الخط",       "map": "₀₁₂₃₄₅₆₇₈₉"},
    5:  {"name": "بين قوسين",      "map": "⁽⁰¹²³⁴⁵⁶⁷⁸⁹"},
    6:  {"name": "عريض",          "map": "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"},
    7:  {"name": "عريض مائل",       "map": "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"},
    8:  {"name": "مزدوج",          "map": "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"},
    9:  {"name": "آلة كاتبة",       "map": "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"},
    10: {"name": "عرض كامل",        "map": "０１２３４５６７８９"},
    11: {"name": "عربي شرقي",       "map": "٠١٢٣٤٥٦٧٨٩"},
    12: {"name": "فارسي",          "map": "۰۱۲۳۴۵۶۷۸۹"},
    33: {"name": "حروف يونانية",     "map": "αβγδεζηθικ"},
    36: {"name": "مونو (Monospace)", "map": "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"},
}

TIME_ZONES = {
    "بغداد": "Asia/Baghdad",
    "العراق": "Asia/Baghdad",
    "السعودية": "Asia/Riyadh",
    "مكة": "Asia/Riyadh",
    "الكويت": "Asia/Kuwait",
    "مصر": "Africa/Cairo",
    "القاهرة": "Africa/Cairo",
    "الاردن": "Asia/Amman",
    "سوريا": "Asia/Damascus",
    "لبنان": "Asia/Beirut",
    "اليمن": "Asia/Aden",
    "المغرب": "Africa/Casablanca",
    "الجزائر": "Africa/Algiers",
    "تونس": "Africa/Tunis",
    "ليبيا": "Africa/Tripoli",
    "تركيا": "Europe/Istanbul",
    "دبي": "Asia/Dubai",
    "قطر": "Asia/Qatar",
    "فلسطين": "Asia/Hebron",
    "السودان": "Africa/Khartoum",
    "الصومال": "Africa/Mogadishu",
    "لندن": "Europe/London",
    "باريس": "Europe/Paris",
    "نيويورك": "America/New_York",
    "لوس_انجلوس": "America/Los_Angeles",
    "موسكو": "Europe/Moscow",
    "طهران": "Asia/Tehran",
    "اسلام_اباد": "Asia/Karachi",
    "جاكرتا": "Asia/Jakarta",
    "طوكيو": "Asia/Tokyo",
    "سيدني": "Australia/Sydney",
    "الهند": "Asia/Kolkata",
    "جنوب_افريقيا": "Africa/Johannesburg",
}

_time_task = None


def _time_digit_style():
    return db_get("settings", "time_digit_style", 0)


def _time_zone_key():
    return db_get("settings", "time_zone", "Asia/Baghdad")


def _resolve_zone(arg):
    """يحوّل اسم بلد/مدينة أو مفتاح zoneinfo إلى مفتاح صالح"""
    a = (arg or "").strip()
    if not a:
        return None
    if a in TIME_ZONES:
        return TIME_ZONES[a]
    if a in TIME_ZONES.values():
        return a
    for name, key in TIME_ZONES.items():
        if name in a or a in name:
            return key
    try:
        ZoneInfo(a)
        return a
    except Exception:
        return None


def _format_time_decorated():
    zk = _time_zone_key()
    try:
        tz = ZoneInfo(zk)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()
    h12 = now.hour % 12
    if h12 == 0:
        h12 = 12
    raw = f"{h12}:{now.minute:02d}"
    ds = _time_digit_style()
    dmap = DIGIT_SETS.get(ds, DIGIT_SETS[0])["map"]
    out = []
    for ch in raw:
        if "0" <= ch <= "9":
            idx = ord(ch) - 48
            out.append(dmap[idx] if idx < len(dmap) else ch)
        else:
            out.append(ch)
    return "".join(out)


async def _time_loop():
    """حلقة تحدّث الاسم الأخير بوقت حي كل دقيقة"""
    while db_get("settings", "time_active", False):
        t = _format_time_decorated()
        try:
            await client(functions.account.UpdateProfileRequest(last_name=t))
        except Exception:
            pass
        now = datetime.now()
        sleep_s = 60 - now.second - now.microsecond / 1_000_000
        if sleep_s <= 0:
            sleep_s = 60.0
        await asyncio.sleep(sleep_s)


@cmd(r"وقتي تشغيل$")
async def _(event):
    db_set("settings", "time_active", True)
    global _time_task
    if _time_task is None or _time_task.done():
        _time_task = asyncio.ensure_future(_time_loop())
    await edit_or_reply(event, " تم تفعيل الاسم الوقتي — سيظهر الوقت بجانب اسمك كل دقيقة")


@cmd(r"وقتي ايقاف$")
async def _(event):
    db_set("settings", "time_active", False)
    await edit_or_reply(event, " تم إيقاف الاسم الوقتي")


@cmd(r"وقتي توقيت(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        cur = _time_zone_key()
        names = [n for n, k in TIME_ZONES.items() if k == cur]
        label = (" / ".join(names)) if names else cur
        sample = "\n".join(f"• `{n}` ⟶ `{k}`" for n, k in list(TIME_ZONES.items())[:12])
        return await edit_or_reply(
            event,
            f"**| اختيار التوقيت (المنطقة الزمنية):**\nالحالي: {label} ({cur})\n\n"
            f"**أمثلة البلدان:**\n{sample}\n… وغيرها الكثير (أو اكتب مفتاح zoneinfo مباشرة مثل `Europe/London`)\n\n"
            f"للتغيير: `{PREFIX}وقتي توقيت <اسم البلد/المدينة>`\nمثال: `{PREFIX}وقتي توقيت بغداد`",
        )
    zk = _resolve_zone(arg)
    if not zk:
        return await edit_or_reply(
            event,
            " لم أتعرّف على هذه المنطقة.\nاكتب `.وقتي توقيت` لعرض قائمة البلدان المتاحة، "
            "أو استخدم مفتاح zoneinfo صحيح مثل `Asia/Baghdad`.",
        )
    db_set("settings", "time_zone", zk)
    preview = _format_time_decorated()
    names = [n for n, k in TIME_ZONES.items() if k == zk]
    label = (" / ".join(names)) if names else zk
    await edit_or_reply(event, f" تم ضبط التوقيت: {label} ({zk})\nالمعاينة الآن: {preview}")


@cmd(r"وقتي شكل(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg.isdigit():
        lines = []
        for k, v in DIGIT_SETS.items():
            ds_backup = _time_digit_style()
            db_set("settings", "time_digit_style", k)
            ex = _format_time_decorated()
            db_set("settings", "time_digit_style", ds_backup)
            lines.append(f"`{k}` | {v['name']}  ⟶  `{ex}`")
        return await edit_or_reply(
            event,
            f"**| أشكال أرقام الاسم الوقتي (مع أمثلة حية):**\n" + "\n".join(lines) +
            f"\n\nللاختيار: `{PREFIX}وقتي شكل <رقم>`\nالحالي: {_time_digit_style()}",
        )
    k = int(arg)
    if k not in DIGIT_SETS:
        return await edit_or_reply(event, " رقم شكل غير موجود — اكتب `.وقتي شكل` لعرض القائمة")
    db_set("settings", "time_digit_style", k)
    preview = _format_time_decorated()
    await edit_or_reply(event, f" تم ضبط الشكل: {DIGIT_SETS[k]['name']}\nالمعاينة: {preview}")


@cmd(r"وقتي$")
async def _(event):
    preview = _format_time_decorated()
    active = db_get("settings", "time_active", False)
    zk = _time_zone_key()
    names = [n for n, k in TIME_ZONES.items() if k == zk]
    label = (" / ".join(names)) if names else zk
    await edit_or_reply(
        event,
        f"**| الاسم الوقتي:**\nالحالة: {' شغال' if active else 'X متوقف'}\n"
        f"الشكل: {DIGIT_SETS.get(_time_digit_style(), DIGIT_SETS[0])['name']}\n"
        f"التوقيت: {label} ({zk})\n"
        f"المعاينة: {preview}\n\n"
        f"الأوامر:\n`{PREFIX}وقتي تشغيل`\n`{PREFIX}وقتي ايقاف`\n"
        f"`{PREFIX}وقتي شكل <رقم>`\n`{PREFIX}وقتي توقيت <بلد/مدينة>`",
    )



# تم حذف أوامر التحديث وقطع الصلاحية عن المطور السابق

@client.on(events.NewMessage(incoming=True))
async def _ai_auto_watcher(event):
    if not event.is_private or not event.text:
        return
    if not db_get("settings", "ai_auto", False):
        return
    if db_get("settings", "ai_full", False):
        return
    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False):
        return
    me = await client.get_me()
    if event.sender_id == me.id:
        return
    try:
        async with client.action(event.chat_id, "typing"):
            answer = await ai_ask(event.raw_text, event)
        if answer:
            await event.reply(answer)
    except Exception:
        pass


_VC_API = "https://audio.ettacent.dev/api/v1"

VC_EFFECTS = [
    ("1", "سنجاب", "🐿", "صوت مرتفع كالسناجب"),
    ("2", "عميق", "", "صوت رجال عميق"),
    ("3", "روبوت", "", "صوت روبوتي"),
    ("4", "صدى", "", "صدى واسع"),
    ("5", "عكسي", "", "قلب الصوت"),
    ("6", "همس", "", "صوت همس خفيف"),
    ("7", "مكبر", "", "مكبر صوت"),
    ("8", "هاتف", "", "صوت هاتف قديم"),
    ("9", "كهف", "", "صدى كهف عميق"),
    ("10", "فضائي", "", "صوت كائن فضائي"),
    ("11", "هيليوم", "", "صوت مرتفع جداً"),
    ("12", "شيطان", "", "صوت شيطاني"),
    ("13", "راديو", "", "صوت راديو"),
    ("14", "تحت الماء", "", "صوت تحت الماء"),
    ("15", "وحش", "", "صوت وحش مخيف"),
    ("16", "8-بت", "🕹", "صوت ألعاب قديمة"),
    ("17", "فنطاز", "", "صوت فنطاز قديم"),
    ("18", "بطيء", "", "صوت مبطئ"),
    ("19", "سريع", "", "صوت مسرع"),
    ("20", "تأتأة", "", "صوت متقطع"),
    ("21", "مكتوم", "", "صوت مكتوم"),
    ("22", "جوقة", "", "صوت جوقة متعددة"),
    ("23", "سكران", "", "صوت سكران"),
    ("24", "تريمولو", "", "صوت مرتجف"),
    ("25", "معطل", "", "بدون تأثير"),
]
VC_KEYS = ["chipmunk","deep","robot","echo","reverse","whisper","megaphone","telephone",
           "cave","alien","helium","demon","radio","underwater","monster","eight_bit",
           "vintage","slow","fast","stutter","muffled","chorus","drunk","tremolo","none"]


async def _vc_ensure_token():
    """يضمن وجود توكن API — يسجل إذا لزم الأمر"""
    tok = db_get("settings", "vc_token")
    if tok:
        return tok
    try:
        me = await client.get_me()
        uid = me.id
    except Exception:
        return None
    try:
        import requests as req
        r = req.post(f"{_VC_API}/auth/register", params={"user_id": uid}, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        code = data.get("code")
        bot_username = data.get("bot_username")
        if not code or not bot_username:
            return None
        try:
            await client.inline_query(bot_username, code)
        except Exception:
            pass
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                p = req.post(f"{_VC_API}/auth/poll", params={"user_id": uid, "code": code}, timeout=10)
                if p.status_code == 200:
                    tok = p.json().get("token")
                    if tok:
                        db_set("settings", "vc_token", tok)
                        return tok
                    return None
                if p.status_code == 404:
                    return None
            except Exception:
                pass
            await asyncio.sleep(2)
    except Exception:
        pass
    return None


@cmd(r"صوتي سجل$")
async def _(event):
    m = await event.edit("🔄 جاري التسجيل في خادم الصوت...")
    tok = await _vc_ensure_token()
    if tok:
        await edit_or_reply(m, " تم التسجيل في خادم الصوت بنجاح ✓")
    else:
        await edit_or_reply(m, " فشل التسجيل — تأكد من اتصال الإنترنت")


@cmd(r"صوتي(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        lines = "\n".join(f"`{num}` | {emo} {name}  — {desc}" for num, name, emo, desc in VC_EFFECTS)
        return await edit_or_reply(
            event,
            f"**| قائمة تأثيرات الصوت (Voice Changer):**\n\n{lines}\n\n"
            f"للتطبيق: رد على ملف صوتي وأرسل `{PREFIX}صوتي <رقم>`\n"
            f"مثال: `{PREFIX}صوتي 3` (روبوت)\n"
            f"للتسجيل أول مرة: `{PREFIX}صوتي سجل`",
        )
    if arg == "سجل":
        return
    idx = -1
    try:
        idx = int(arg) - 1
    except ValueError:
        pass
    if idx < 0 or idx >= len(VC_EFFECTS):
        return await edit_or_reply(event, f" رقم غير صالح (1-{len(VC_EFFECTS)}). اكتب `{PREFIX}صوتي` لعرض القائمة")
    reply = await event.get_reply_message()
    if not reply or not (reply.audio or reply.voice or reply.video or reply.document or reply.video_note):
        return await edit_delete(event, "- رد على ملف صوتي/فيديو/أغنية أولاً", 8)
    num, name, emo, desc = VC_EFFECTS[idx]
    effect_key = VC_KEYS[idx]
    if effect_key == "none":
        return await edit_or_reply(event, " التأثير معطل — اختر تأثيراً آخر")
    m = await event.edit(f"{emo} جاري تطبيق تأثير: {name}...")
    tmp_in = None
    tmp_out = None
    try:
        tok = await _vc_ensure_token()
        if not tok:
            return await m.edit(" لم يتم التسجيل في خادم الصوت. أرسل `.صوتي سجل` أولاً")
        tmp_in = await event.client.download_media(reply.media)
        tmp_out = os.path.join(DATA_DIR, f"vc_{int(time.time()*1000)}.ogg")
        import requests as req
        with open(tmp_in, "rb") as f:
            files = {"audio": (os.path.basename(tmp_in), f, "audio/ogg")}
            data = {"effect": effect_key, "media_type": "voice"}
            headers = {"X-Auth-Token": tok}
            resp = req.post(f"{_VC_API}/process", files=files, data=data, headers=headers, timeout=120)
        if resp.status_code == 401:
            db_set("settings", "vc_token", "")
            return await m.edit(" التوكن منتهي — أرسل `.صوتي سجل` لإعادة التسجيل")
        if resp.status_code != 200 or len(resp.content) < 100:
            return await m.edit(f" فشل المعالجة (رمز {resp.status_code})")
        with open(tmp_out, "wb") as f:
            f.write(resp.content)
        try:
            rp = await asyncio.create_subprocess_exec(
                "ffprobe", "-i", tmp_out, "-show_entries", "format=duration",
                "-v", "quiet", "-of", "csv=p=0",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            out, _ = await asyncio.wait_for(rp.communicate(), timeout=15)
            dur = int(float(out.decode().strip())) if out else 0
        except Exception:
            dur = 0
        await event.client.send_file(
            event.chat_id, tmp_out,
            voice_note=True,
            attributes=[types.DocumentAttributeAudio(voice=True, duration=dur)],
            reply_to=reply.id,
        )
        try:
            await m.delete()
        except Exception:
            pass
    except Exception as e:
        await m.edit(f" خطأ: {e}")
    finally:
        for f in (tmp_in, tmp_out):
            if f and os.path.exists(f):
                try: os.remove(f)
                except Exception: pass


_TIK_API = "https://tiktok-downbloder.vercel.app/"


def _tik_fetch_sync(url):
    """يستدعي API التيك توك ويعيد JSON"""
    import urllib.parse
    conn = http.client.HTTPSConnection("tiktok-downbloder.vercel.app", timeout=60)
    conn.request("GET", "/?url=" + urllib.parse.quote(url, safe=""), headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/138.0.0.0",
    })
    res = conn.getresponse()
    raw = res.read()
    conn.close()
    return json.loads(raw.decode("utf-8", "ignore"))


def _tik_download_sync(dl_url, dest):
    """ينزّل ملفاً من رابط مباشر"""
    conn = http.client.HTTPSConnection("tikcdn.io", timeout=120)
    conn.request("GET", dl_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/138.0.0.0",
        "Referer": "https://www.tiktok.com/",
    })
    res = conn.getresponse()
    with open(dest, "wb") as f:
        while True:
            chunk = res.read(65536)
            if not chunk:
                break
            f.write(chunk)
    conn.close()
    return dest


def _tik_cleanup(files):
    for f in files:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


@cmd(r"تيك(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        return await edit_delete(event, f"- اكتب: {PREFIX}تيك <رابط تيك توك>", 8)
    m = await event.edit("- جاري جلب البيانات...")
    tmp_files = []
    try:
        data = await asyncio.to_thread(_tik_fetch_sync, arg)
        raw = data.get("result", {}).get("raw", {}).get("result", {})
        mtype = raw.get("type") or ""
        if not data.get("success") or not mtype:
            return await edit_or_reply(m, "X تعذّر الجلب — الرابط غير صالح أو محذوف")
        await m.edit(f" وجدت: {mtype} ✓\nجارٍ التحميل...")
        sent = 0
        if mtype == "video":
            vurl = raw.get("video")
            if vurl:
                dest = os.path.join(BASE_DIR, f"tik_video_{_ai_rand_id()}.mp4")
                tmp_files.append(dest)
                await asyncio.to_thread(_tik_download_sync, vurl, dest)
                cap = (raw.get("desc") or "").strip()
                await event.client.send_file(event.chat_id, dest, caption=cap[:1024] or None)
                sent += 1
        elif mtype == "image":
            imgs = raw.get("images") or []
            for i, iurl in enumerate(imgs):
                dest = os.path.join(BASE_DIR, f"tik_img_{_ai_rand_id()}.webp")
                tmp_files.append(dest)
                await asyncio.to_thread(_tik_download_sync, iurl, dest)
                await event.client.send_file(event.chat_id, dest)
                sent += 1
                if i >= 9:
                    break
            murl = raw.get("music")
            if murl:
                await m.edit(" جاري جلب المزيكا...")
                dest = os.path.join(BASE_DIR, f"tik_music_{_ai_rand_id()}.m4a")
                tmp_files.append(dest)
                await asyncio.to_thread(_tik_download_sync, murl, dest)
                await event.client.send_file(
                    event.chat_id, dest,
                    attributes=[types.DocumentAttributeFilename("tiktok_music.m4a")],
                )
        else:
            return await edit_or_reply(m, "X نوع غير مدعوم")
        await edit_or_reply(m, f" تم التحميل ✓\nوسائط أُرسلت: {sent}" if sent else " تم الجلب ✓")
    except Exception as e:
        await edit_or_reply(m, f"X خطأ: `{e}`")
    finally:
        _tik_cleanup(tmp_files)


# ═══════════════════════════════════════════════════════════
#  أمر يوتيوب — تحميل MP3 عبر Samplecut (بدون حظر IP)
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
#  أمر يوتيوب - النسخة الفخمة (مطابقة لبوتات الميوزك الكبيرة)
# ═══════════════════════════════════════════════════════════
from PIL import Image  # تأكد من تثبيت مكتبة Pillow
# ═══════════════════════════════════════════════════════════
#  أمر يوتيوب - النسخة الفخمة (مطابقة لبوتات الميوزك الكبيرة)
# ═══════════════════════════════════════════════════════════

THUMBNAIL_URL = "https://i.ibb.co/0ygLm1zm/3c96cc6464fc59eb3289e5b54afcb5f7.jpg"
THUMBNAIL_PATH = os.path.join(DATA_DIR, "yt_thumb_original.jpg")
THUMB_PROCESSED = os.path.join(DATA_DIR, "yt_thumb_ready.jpg")

_YT_CACHE = {}
_YT_SEARCH = {}

def _fmt_dur(s):
    s = int(s or 0)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def _safe_name(title, vid):
    t = re.sub(r'[\\/:*?"<>|\n\r\t]', '_', title or "").strip()
    return (re.sub(r'\s+', ' ', t)[:80] or f"audio_{vid}") + ".mp3"

# ───────────── البحث ─────────────
def _yt_search(q):
    if q in _YT_SEARCH: return _YT_SEARCH[q]
    print(f"[search] query={q!r}")
    for fn in (_yt_search_direct, _yt_search_ytdlp):
        vid = fn(q)
        if vid:
            _YT_SEARCH[q] = vid
            return vid
    return None

def _yt_search_direct(q):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept-Language": "ar,en;q=0.9",
    })
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            def find(o):
                if isinstance(o, dict):
                    if "videoRenderer" in o: return o["videoRenderer"].get("videoId")
                    for v in o.values():
                        r = find(v)
                        if r: return r
                elif isinstance(o, list):
                    for x in o:
                        r = find(x)
                        if r: return r
                return None
            vid = find(data)
            if vid: return vid
        m = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        if m: return m.group(1)
    except Exception as e:
        print(f"[direct] err: {e}")
    return None

def _yt_search_ytdlp(q):
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(f"ytsearch1:{q}", download=False)
            if info and info.get("entries"):
                return info["entries"][0].get("id")
    except Exception:
        pass
    return None

# ───────────── جلب الصوت من Samplecut ─────────────
def _samp_fetch(vid):
    if vid in _YT_CACHE and time.time() - _YT_CACHE[vid]["_ts"] < 3600:
        return _YT_CACHE[vid]

    def _post(payload):
        req = urllib.request.Request("https://api.samplecut.app/v1/downloads",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Client-Name": "Joker", "User-Agent": "Mozilla/5.0"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode()), None
        except urllib.error.HTTPError as e:
            try: return None, json.loads(e.read().decode()).get("error", {}).get("code")
            except: return None, None
        except: return None, None

    data, code = _post({"url": f"https://youtu.be/{vid}"})
    if code == "too_long":
        data, _ = _post({"url": f"https://youtu.be/{vid}", "start_sec": 0, "end_sec": 1800})
    
    if not data or not data.get("download_url"):
        return None

    res = {"url": data["download_url"], "title": data.get("title") or "", 
           "duration": data.get("track_duration_sec") or 0, "_ts": time.time()}
    _YT_CACHE[vid] = res
    return res

# ───────────── معالجة الصورة ─────────────
def _prepare_thumb():
    try:
        if not os.path.exists(THUMBNAIL_PATH):
            req = urllib.request.Request(THUMBNAIL_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                with open(THUMBNAIL_PATH, "wb") as f: f.write(r.read())

        # قص وضغط الصورة لتقبلها تيليجرام (أقل من 200KB و 320x320)
        img = Image.open(THUMBNAIL_PATH)
        img.thumbnail((320, 320), Image.LANCZOS)
        
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        img.save(THUMB_PROCESSED, format="JPEG", quality=85, optimize=True)
        
        with open(THUMB_PROCESSED, "rb") as f:
            return f.read() # إرجاع الصورة كـ Bytes
    except Exception as e:
        print(f"[thumb] Error: {e}")
        return None

# ───────────── التنزيل ─────────────
def _download_file(url, out_path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(out_path, "wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk: break
            f.write(chunk)

# ───────────── الأمر الفخم ─────────────
@cmd(r"يوت(?:\s|$)([\s\S]*)")
async def _(event):
    query = (event.pattern_match.group(1) or "").strip()
    if not query:
        return await edit_delete(event, f"- اكتب: `{PREFIX}يوت <اسم الأغنية أو رابط>`", 8)

    m = await event.edit("🔍 بحث...")
    
    # 1. البحث
    mm = re.search(r"(?:v=|youtu\.be/|shorts/|/embed/)([a-zA-Z0-9_-]{11})", query)
    vid = mm.group(1) if mm else await asyncio.to_thread(_yt_search, query)
    if not vid:
        return await edit_or_reply(m, "❌ لم أجد الأغنية.")

    # 2. جلب رابط الصوت
    await m.edit("⬇️ جاري جلب الصوت...")
    res = await asyncio.to_thread(_samp_fetch, vid)
    if not res:
        return await edit_or_reply(m, "❌ فشل جلب الصوت من السيرفر.")

    # 3. تجهيز البيانات
    title = res["title"] or f"يوتيوب - {vid}"
    duration = int(res["duration"] or 0)
    fname = _safe_name(title, vid)
    audio_url = res["url"]

    # 4. تجهيز الصورة المصغرة
    thumb_bytes = await asyncio.to_thread(_prepare_thumb)

    # 5. التنزيل المحلي (لضمان ظهور الاسم والصورة)
    await m.edit("📥 جاري التنزيل والمعالجة...")
    tmp_path = os.path.join(tempfile.gettempdir(), fname)
    try:
        await asyncio.to_thread(_download_file, audio_url, tmp_path)
    except Exception as e:
        return await edit_or_reply(m, f"❌ فشل التنزيل: `{e}`")

    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 1024:
        return await edit_or_reply(m, "❌ الملف تالف أو فارغ.")

    # 6. الإرسال الفخم
    await m.edit("📤 جاري الإرسال...")
    
    # النص المطلوب مع الرابط و الإيموجي البريميوم
    caption_fancy = (
        f'⌯︙ تم التحميل بنجاح '
        f'<a href="https://t.me/rkkyk">𝟼𝟼𝟼</a> '
        f'<tg-emoji emoji-id="5357304199417735018">🎧</tg-emoji>'
    )
    
    attributes = [
        DocumentAttributeAudio(
            duration=duration,
            title=title[:64], 
            performer="@rkkyk",  # تم التعديل هنا
            voice=False
        ),
        DocumentAttributeFilename(fname)
    ]

    try:
        kw = dict(
            file=tmp_path,
            mime_type="audio/mpeg",
            attributes=attributes,
            force_document=False,
            reply_to=event.reply_to_msg_id
        )
        if thumb_bytes:
            kw["thumb"] = thumb_bytes 

        try:
            # محاولة الإرسال بالتنسيق الفخم والايموجي البريميوم
            await client.send_file(event.chat_id, caption=caption_fancy, parse_mode="html", **kw)
        except Exception as html_err:
            print(f"HTML Error: {html_err}")
            # إذا فشل ايموجي البريميوم (بسبب اصدار قديم)، يرسل النص بدون ايموجي بريميوم
            simple_caption = '⌯︙ تم التحميل بنجاح <a href="https://t.me/rkkyk">𝟼𝟼𝟼</a> 🎵'
            await client.send_file(event.chat_id, caption=simple_caption, parse_mode="html", **kw)

        await m.delete()
    except Exception as e:
        await edit_or_reply(m, f"❌ خطأ أثناء الإرسال: `{e}`")
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass


# ═══════════════════════════════════════════════════════════
#  م23 — النشر التلقائي (Auto Broadcast)
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
#  م23 — النشر التلقائي (Auto Broadcast) — نسخة محصنة
# ═══════════════════════════════════════════════════════════
_autobc_task = None
_autobc_running = False


def _autobc_cfg():
    cfg = db_read("autobc", {})
    cfg.setdefault("groups", [])
    cfg.setdefault("message", None)
    cfg.setdefault("interval", 30)
    cfg.setdefault("running", False)
    cfg.setdefault("total_sent", 0)
    cfg.setdefault("last_sent", 0)
    cfg.setdefault("_cached_groups", [])
    return cfg


def _autobc_save(cfg):
    db_write("autobc", cfg)


def _rebuild_entities(entities_data):
    """إعادة بناء كيانات Telegram كما هي بالضبط"""
    if not entities_data:
        return None
    result = []
    for e in entities_data:
        try:
            cls_name = e.get("_")
            cls = getattr(types, cls_name, None)
            if cls:
                # نمرر البيانات كما هي
                kwargs = {k: v for k, v in e.items() if k != "_"}
                result.append(cls(**kwargs))
        except Exception:
            continue
    return result if result else None

def _dump_entities(msg):
    """يحول entities الرسالة إلى dict للحفظ في JSON"""
    if not msg or not getattr(msg, "entities", None):
        return None
    try:
        # نحفظ كل شي بالضبط بدون حذف
        return [e.to_dict() for e in msg.entities]
    except Exception:
        return None

async def _autobc_loop():
    """حلقة النشر التلقائي — تُرسل الرسالة لكل المجموعات دورياً"""
    global _autobc_running
    _autobc_running = True
    try:
        while _autobc_running:
            cfg = _autobc_cfg()
            if not cfg.get("running"):
                break
            groups = cfg.get("groups", [])
            msg = cfg.get("message")
            interval_min = int(cfg.get("interval", 30))

            if not groups or not msg:
                await asyncio.sleep(30)
                continue

            text = msg.get("text", "")
            entities = _rebuild_entities(msg.get("entities"))

            sent_now = 0
            for gid in groups:
                if not _autobc_running:
                    break
                try:
                    send_kwargs = {
                        "entity": int(gid),
                        "message": text,
                    }
                    
                    # إذا كانت الرسالة تحتوي على تنسيقات (Bold, Italic) مأخوذة من أزرار تيليجرام
                    if entities:
                        send_kwargs["formatting_entities"] = entities
                        send_kwargs["parse_mode"] = None
                    else:
                        # إذا كانت الرسالة نص عادي، نعالج الماركداون ونحوله لـ HTML عشان ما يخرب البريميوم
                        # تحويل **نص** إلى <b>نص</b>
                        text = text.replace("**", "__BOLD__")
                        text = text.replace("__BOLD__", "<b>", 1)
                        text = text.replace("__BOLD__", "</b>", 1)
                        # تحويل `نص` إلى <code>نص</code>
                        text = text.replace("`", "__CODE__")
                        text = text.replace("__CODE__", "<code>", 1)
                        text = text.replace("__CODE__", "</code>", 1)
                        
                        # إذا كانت الرسالة فيها إيموجي بريميوم، نحوله لـ HTML
                        # (افتراضياً الإيموجي البريميوم في تيليجرام يرسل بـ <tg-emoji>)
                        send_kwargs["parse_mode"] = "html"
                        send_kwargs["message"] = text

                    await client.send_message(**send_kwargs)
                    sent_now += 1
                    await asyncio.sleep(3)
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 1)
                except Exception:
                    pass

            cfg = _autobc_cfg()
            cfg["total_sent"] = cfg.get("total_sent", 0) + sent_now
            cfg["last_sent"] = time.time()
            _autobc_save(cfg)

            total_wait = interval_min * 60
            while total_wait > 0 and _autobc_running:
                w = min(30, total_wait)
                await asyncio.sleep(w)
                total_wait -= w
    finally:
        _autobc_running = False
def _autobc_start_task():
    global _autobc_task
    if _autobc_task is None or _autobc_task.done():
        _autobc_task = asyncio.ensure_future(_autobc_loop())


@cmd(r"المجموعات$")
async def _(event):
    m = await event.edit("🔍 جاري جمع المجموعات...")
    groups = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            groups.append(dialog)
    if not groups:
        return await edit_or_reply(m, "❌ لا توجد مجموعات في حسابك")

    cfg = _autobc_cfg()
    cfg["_cached_groups"] = [
        {"id": d.id, "title": d.name or "بدون اسم"} for d in groups[:100]
    ]
    _autobc_save(cfg)

    lines = [f"**📋 مجموعاتك ({len(groups)}):**\n"]
    for i, d in enumerate(groups[:100], 1):
        lines.append(f"`{i}.` {d.name} — `{d.id}`")
    if len(groups) > 100:
        lines.append(f"\n… و {len(groups) - 100} مجموعة أخرى")
    lines.append(f"\n**لإضافة:** `{PREFIX}اضف مجموعه <الرقم>`")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n..."
    await edit_or_reply(m, text)


@cmd(r"اضف مجموعه(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    
    cfg = _autobc_cfg()
    groups = cfg.get("groups", [])
    cached = cfg.get("_cached_groups", [])

    if not cached and not reply:
        return await edit_or_reply(event, f"⚠️ أرسل `{PREFIX}المجموعات` أولاً لعرض القائمة.")

    added_count = 0
    already_added = 0
    
    # 1. الإضافة بالكل
    if arg in ("الكل", "كل", "all"):
        if not cached:
            return await edit_or_reply(event, "⚠️ قائمة المجموعات فارغة.")
        for g in cached:
            if g["id"] not in groups:
                groups.append(g["id"])
                added_count += 1
            else:
                already_added += 1
                
    # 2. الإضافة بالأرقام (مثل 1 2 8 7)
    elif arg and all(x.isdigit() for x in arg.split()):
        nums = [int(x) for x in arg.split()]
        for num in nums:
            idx = num - 1
            if 0 <= idx < len(cached):
                gid = cached[idx]["id"]
                if gid not in groups:
                    groups.append(gid)
                    added_count += 1
                else:
                    already_added += 1
        if added_count == 0 and already_added == 0:
            return await edit_or_reply(event, "⚠️ أرقام غير صحيحة أو خارج القائمة.")

    # 3. الإضافة بالرد
    elif reply:
        target_id = None
        fwd = getattr(reply, "fwd_from", None)
        if fwd and getattr(fwd, "from_id", None):
            from_id = fwd.from_id
            if hasattr(from_id, "channel_id"):
                target_id = int(f"-100{from_id.channel_id}")
            elif hasattr(from_id, "chat_id"):
                target_id = int(f"-100{from_id.chat_id}")
        elif getattr(reply, "peer_id", None):
            peer = reply.peer_id
            if hasattr(peer, "channel_id"):
                target_id = int(f"-100{peer.channel_id}")
            elif hasattr(peer, "chat_id"):
                target_id = int(f"-100{peer.chat_id}")
                
        if target_id:
            if target_id not in groups:
                groups.append(target_id)
                added_count += 1
            else:
                already_added += 1
        else:
            return await edit_or_reply(event, "⚠️ لا يمكن استخراج المجموعة من هذه الرسالة.")

    else:
        return await edit_or_reply(event, f"⚠️ **طريقة الإضافة:**\n"
            f"1️⃣ **بالأرقام:** `{PREFIX}اضف مجموعه 1 2 3`\n"
            f"2️⃣ **بالكل:** `{PREFIX}اضف مجموعه الكل`\n"
            f"3️⃣ **بالرد:** حول رسالة من المجموعة ورد بـ `{PREFIX}اضف مجموعه`")

    cfg["groups"] = groups
    _autobc_save(cfg)
    
    msg = f"✅ تمت إضافة `{added_count}` مجموعة."
    if already_added > 0:
        msg += f"\n⚠️ `{already_added}` كانت مضافة مسبقاً."
    msg += f"\n📊 الإجمالي الآن: `{len(groups)}`"
    
    await edit_or_reply(event, msg)

@cmd(r"ازالة مجموعه(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    
    cfg = _autobc_cfg()
    groups = cfg.get("groups", [])
    
    if not groups:
        return await edit_or_reply(event, "⚠️ لا توجد مجموعات مضافة لحذفها.")

    removed_count = 0

    # 1. حذف الكل
    if arg in ("الكل", "كل", "all"):
        removed_count = len(groups)
        groups.clear()

    # 2. الحذف بالأرقام التسلسلية (1 2 3)
    elif arg and all(x.isdigit() for x in arg.split()):
        nums = [int(x) for x in arg.split()]
        nums.sort(reverse=True)
        for num in nums:
            idx = num - 1
            if 0 <= idx < len(groups):
                groups.pop(idx)
                removed_count += 1
        if removed_count == 0:
            return await edit_or_reply(event, f"⚠️ أرقام غير صحيحة (راجع `{PREFIX}مجموعاتي`).")

    # 3. الحذف بالرد
    elif reply:
        target_id = None
        fwd = getattr(reply, "fwd_from", None)
        if fwd and getattr(fwd, "from_id", None):
            from_id = fwd.from_id
            if hasattr(from_id, "channel_id"):
                target_id = int(f"-100{from_id.channel_id}")
            elif hasattr(from_id, "chat_id"):
                target_id = int(f"-100{from_id.chat_id}")
        elif getattr(reply, "peer_id", None):
            peer = reply.peer_id
            if hasattr(peer, "channel_id"):
                target_id = int(f"-100{peer.channel_id}")
            elif hasattr(peer, "chat_id"):
                target_id = int(f"-100{peer.chat_id}")
                
        if target_id:
            if target_id in groups:
                groups.remove(target_id)
                removed_count += 1
            else:
                return await edit_or_reply(event, "⚠️ هذه المجموعة ليست في القائمة.")
        else:
            return await edit_or_reply(event, "⚠️ لا يمكن استخراج المجموعة من هذه الرسالة.")
            
    else:
        return await edit_or_reply(event, f"⚠️ **طريقة الحذف:**\n"
            f"1️⃣ **بالأرقام:** `{PREFIX}ازالة مجموعه 1 2 3`\n"
            f"2️⃣ **بالكل:** `{PREFIX}ازالة مجموعه الكل`\n"
            f"3️⃣ **بالرد:** حول رسالة من المجموعة ورد بـ `{PREFIX}ازالة مجموعه`")

    cfg["groups"] = groups
    _autobc_save(cfg)
    
    await edit_or_reply(event, f"✅ تم حذف `{removed_count}` مجموعة.\n📊 المتبقي: `{len(groups)}`")

@cmd(r"مجموعاتي$")
async def _(event):
    cfg = _autobc_cfg()
    groups = cfg.get("groups", [])
    
    if not groups:
        return await edit_or_reply(event, f"❌ لا توجد مجموعات مضافة")

    m = await event.edit("🔍 جاري جلب الأسماء...")
    lines = [f"**📢 مجموعات النشر المضافة ({len(groups)}):**\n"]
    
    for i, gid in enumerate(groups, 1):
        try:
            ent = await client.get_entity(int(gid))
            title = getattr(ent, "title", str(gid))
        except Exception:
            title = f"(غير متاح: {gid})"
        lines.append(f"`{i}.` {title}")
        
    lines.append(f"\n**للحذف:** `{PREFIX}ازالة مجموعه <الرقم>` (مثلاً `{PREFIX}ازالة مجموعه 1 2`)")
    await edit_or_reply(m, "\n".join(lines))
    
@cmd(r"تعيين رساله(?:\s|$)([\s\S]*)")
async def _(event):
    reply = await event.get_reply_message()
    text = (event.pattern_match.group(1) or "").strip()

    if reply and reply.text:
        entities_data = _dump_entities(reply)
        cfg = _autobc_cfg()
        cfg["message"] = {"text": reply.text, "entities": entities_data}
        _autobc_save(cfg)
        entities_count = len(entities_data) if entities_data else 0
        return await edit_or_reply(
            event,
            f"✅ تم التعيين (من الرد)\n📝 النص: `{len(reply.text)}` حرف\n✨ Entities: `{entities_count}`"
        )

    if text:
        cfg = _autobc_cfg()
        cfg["message"] = {"text": text, "entities": None}
        _autobc_save(cfg)
        return await edit_or_reply(event, f"✅ تم التعيين\n📝 النص: `{len(text)}` حرف")

    return await edit_delete(event, f"- رد على رسالة، أو اكتب: `{PREFIX}تعيين رساله <النص>`", 8)


@cmd(r"الرساله$")
async def _(event):
    cfg = _autobc_cfg()
    msg = cfg.get("message")
    if not msg:
        return await edit_or_reply(event, f"❌ لا توجد رسالة معينة")

    text = msg.get("text", "")
    entities = msg.get("entities") or []
    await edit_or_reply(
        event,
        f"**📝 الرسالة الحالية:**\n\n{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
        f"📊 الأحرف: `{len(text)}`\n✨ Entities: `{len(entities)}`"
    )


@cmd(r"مسح الرساله$")
async def _(event):
    cfg = _autobc_cfg()
    cfg["message"] = None
    _autobc_save(cfg)
    await edit_or_reply(event, "✅ مُسحت")


@cmd(r"وقت النشر(?:\s|$)([\s\S]*)")
async def _(event):
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg.isdigit():
        cfg = _autobc_cfg()
        return await edit_or_reply(event, f"- اكتب: `{PREFIX}وقت النشر <دقائق>`\nالحالي: `{cfg.get('interval', 30)}`")

    minutes = max(1, int(arg))
    cfg = _autobc_cfg()
    cfg["interval"] = minutes
    _autobc_save(cfg)
    await edit_or_reply(event, f"✅ الوقت: `{minutes}` دقيقة")


@cmd(r"بدء النشر$")
async def _(event):
    cfg = _autobc_cfg()
    groups = cfg.get("groups", [])
    msg = cfg.get("message")

    if not groups:
        return await edit_or_reply(event, f"❌ لا توجد مجموعات")
    if not msg:
        return await edit_or_reply(event, f"❌ لا توجد رسالة")

    cfg["running"] = True
    _autobc_save(cfg)
    _autobc_start_task()

    interval = cfg.get("interval", 30)
    await edit_or_reply(
        event,
        f"🚀 **بدأ النشر**\n📢 `{len(groups)}` مجموعة\n⏱️ كل `{interval}` دقيقة\n🛑 `{PREFIX}ايقاف النشر`"
    )


@cmd(r"ايقاف النشر$")
async def _(event):
    global _autobc_running
    cfg = _autobc_cfg()
    if not cfg.get("running"):
        return await edit_or_reply(event, "⚠️ متوقف أصلاً")

    cfg["running"] = False
    _autobc_save(cfg)
    _autobc_running = False
    await edit_or_reply(event, "🛑 تم الإيقاف")


@cmd(r"حالة النشر$")
async def _(event):
    cfg = _autobc_cfg()
    groups = cfg.get("groups", [])
    msg = cfg.get("message")
    interval = cfg.get("interval", 30)
    running = cfg.get("running", False)
    total = cfg.get("total_sent", 0)
    last = cfg.get("last_sent", 0)

    state = "🟢 يعمل" if running else "🔴 متوقف"
    last_str = "—"
    if last:
        ago = int(time.time() - last)
        last_str = f"قبل {readable_time(ago)}"

    text = (
        f"**📊 حالة النشر**\n\n"
        f"⚡ الحالة: {state}\n"
        f"📢 المجموعات: `{len(groups)}`\n"
        f"📝 الرسالة: {'✅' if msg else '❌'}\n"
        f"⏱️ الفاصل: `{interval}` دقيقة\n"
        f"📤 إجمالي المرسل: `{total}`\n"
        f"🕐 آخر: {last_str}"
    )
    

    await edit_or_reply(event, text)

async def _follow_checker_loop():
    """يتحقق دورياً من وجود رسائل من الهدف، ويبحث عن أخرى إذا حُذفت"""
    me_id = None
    try:
        me = await client.get_me()
        me_id = me.id
    except Exception:
        pass
    while follow_running:
        try:
            target_id = db_get("settings", "follow_target")
            last_msg_id = db_get("settings", "follow_last_msg", 0)
            chat_id = db_get("settings", "follow_chat")
            if not target_id:
                await asyncio.sleep(30)
                continue
            target_id = int(target_id)
            if last_msg_id and chat_id:
                try:
                    msg = await client.get_messages(entity=chat_id, ids=last_msg_id)
                    if msg and not msg.deleted:
                        await asyncio.sleep(20)
                        continue
                except Exception:
                    pass
            async for msg in client.iter_messages(target_id, limit=1):
                if not msg or msg.deleted:
                    continue
                last_sender = getattr(msg, "sender_id", None)
                if not last_sender or int(last_sender) == me_id:
                    continue
                db_set("settings", "follow_last_msg", msg.id)
                db_set("settings", "follow_chat", msg.chat_id)
                word = generate_insult()
                try:
                    await msg.reply(word)
                except Exception:
                    pass
                break
        except Exception:
            pass
        await asyncio.sleep(20)


async def _resume_persistent_tasks():
    """يستأنف المهام المستمرة بعد إعادة التشغيل من إعدادات settings.json"""
    global spam_targets, spam_delay_min, spam_delay_max, spam_batch_min, spam_batch_max, spam_ai_enabled, spam_ai_target, _time_task

    spam_ai_enabled = db_get("settings", "spam_ai_enabled", False)
    spam_ai_target = db_get("settings", "spam_ai_target", "")

    targets = db_get("settings", "spam_targets", [])
    dmin = db_get("settings", "spam_delay_min", 3.0)
    dmax = db_get("settings", "spam_delay_max", 5.0)
    bmin = db_get("settings", "spam_batch_min", 1)
    bmax = db_get("settings", "spam_batch_max", 1)
    if isinstance(targets, str):
        targets = [targets]
    if targets:
        spam_delay_min = float(dmin) if dmin else 3.0
        spam_delay_max = float(dmax) if dmax else 5.0
        spam_batch_min = max(1, int(bmin or 1))
        spam_batch_max = max(1, int(bmax or 1))
        for c in targets:
            try:
                cid = int(c)
                if cid in spam_targets:
                    continue
                spam_targets[cid] = {"reply": None}
                asyncio.ensure_future(_spam_loop(cid, None))
                asyncio.ensure_future(_keep_typing(cid))
            except Exception:
                continue
        print("  ↻ تم استئناف الإرسال التلقائي (السبام) — يهدف " + str(len(spam_targets)))

    if db_get("settings", "time_active", False):
        if _time_task is None or _time_task.done():
            _time_task = asyncio.ensure_future(_time_loop())
        print("  ↻ تم استئناف الاسم الوقتي")

    if db_get("settings", "follow_running", False):
        follow_running = True
        asyncio.ensure_future(_follow_loop())
        print("  ↻ تم استئناف التتبع")

    try:
        rcfg = db_read("report_cfg", {})
        if rcfg.get("running") and rcfg.get("target"):
            asyncio.ensure_future(_resume_report_loop(rcfg["target"]))
            print("  ↻ تم استئناف البلاغ المستمر (الشد)")
    except Exception:
        pass


async def _resume_report_loop(target):
    """نسخة من حلقة الشد لتشغيلها بعد إعادة التشغيل دون أمر"""
    from asyncio import sleep as _sleep
    sent = 0
    err_count = 0
    while True:
        cfg = _report_settings()
        if not cfg.get("running", False) or not cfg.get("target"):
            return
        tgt = cfg.get("target")
        alive, res = await _target_still_alive(tgt)
        if not alive:
            cfg = _report_settings()
            cfg["running"] = False
            db_write("report_cfg", cfg)
            try:
                await client.send_message("me", f"X توقّف البلاغ المستمر تلقائياً:\n{res}\n بلاغات مُرسلة: {sent}")
            except Exception:
                pass
            return
        ent = res
        msg_id = _extract_msg_id_from_url(tgt)
        r = await _do_report(ent, cfg["reason"], cfg["message"], msg_id=msg_id)
        if r is True:
            sent += 1
            err_count = 0
        else:
            err_count += 1
            if err_count >= 5:
                cfg = _report_settings()
                cfg["running"] = False
                db_write("report_cfg", cfg)
                return
        await _sleep(cfg["speed"])


async def _startup():
    global flood_guard
    import shutil
    if shutil.which("git"):
        try:
            subprocess.run(
                ["git", "config", "--global", "--add", "safe.directory", BASE_DIR],
                cwd=BASE_DIR, capture_output=True, timeout=20,
            )
        except Exception:
            pass
    me = await client.get_me()
    _load_insults()
    build_source_info()
    is_premium = getattr(me, "premium", False)
    flood_guard = TextFloodGuard(is_premium=is_premium)
    print("=" * 45)
    print(f"  سورس الجوكر يعمل الآن ✓")
    print(f"  الحساب: {get_display_name(me)} | {me.id}")
    print(f"  البادئة: {PREFIX} | أرسل {PREFIX}الاوامر")
    print(f"  تركيبات السب: {insult_combos():,}")
    print(f"  حماية الفلود: {'🛡 مفعلة' if flood_guard_enabled else ' معطلة'}")
    print(f"  نوع الحساب: {'بريميوم' if is_premium else 'عادي'}")
    print("=" * 45)
    await _resume_persistent_tasks()
    rc = db_get("settings", "restart_chat")
    rm = db_get("settings", "restart_msg")
    if rc and rm:
        try:
            await client.edit_message(rc, rm, "تم إعادة التشغيل بنجاح ✓")
        except Exception:
            pass
        s = db_read("settings")
        s.pop("restart_chat", None)
        s.pop("restart_msg", None)
        db_write("settings", s)


def _acquire_single_lock():
    """يمنع تشغيل نسختين بنفس السيشن في نفس الوقت (سبب wrong session ID)"""
    import socket as _socket
    lock_path = os.path.join(DATA_DIR, "joker.lock")
    alive = False
    if os.path.exists(lock_path):
        try:
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            s.connect(lock_path)
            s.close()
            alive = True
        except Exception:
            alive = False
            try:
                os.remove(lock_path)
            except Exception:
                pass
    if alive:
        print("=" * 45)
        print("  السورس يعمل بالفعل في جلسة أخرى!")
        print("  أغلق النسخة القديمة قبل تشغيل هذه.")
        print("  (سبب خطأ wrong session ID هو تشغيل نسختين بنفس السيشن)")
        print("=" * 45)
        sys.exit(1)
    try:
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.bind(lock_path)
        sock.listen(1)
        return sock
    except OSError:
        print("تعذّر إنشاء قفل التشغيل")
        sys.exit(1)


def main():
    global client
    lock_sock = _acquire_single_lock()
    new_login = not CONFIG["STRING_SESSION"]
    phone = ""
    if new_login:
        print("=" * 45)
        print("  لا يوجد كود سيشن — سيتم تسجيل الدخول الآن")
        print("  أدخل رقم هاتفك مع رمز الدولة (مثال: +96478...)")
        print("=" * 45)
        try:
            phone = input("Phone رقم الهاتف: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("تم الإلغاء")
            sys.exit(1)
        if not phone.startswith("+"):
            phone = "+" + phone.lstrip("+")
    try:
        if new_login and phone:
            client.start(phone=lambda: phone)
        else:
            client.start()
    except Exception as e:
        err = str(e)
        if "api_id/api_hash" in err or "API_ID_PUBLISHED" in err or "API_ID_INVALID" in err:
            print("✗ البيانات (API_ID/API_HASH) غير صحيحة.")
            print("  أدخل بياناتك الصحيحة من https://my.telegram.org/apps")
            try:
                aid = input("* API_ID: ").strip()
                ahash = input("* API_HASH: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("تم الإلغاء")
                sys.exit(1)
            if aid.isdigit() and ahash:
                CONFIG["API_ID"] = int(aid)
                CONFIG["API_HASH"] = ahash
                _save_cfg_basic(CONFIG)
                client = TelegramClient(
                    StringSession(CONFIG["STRING_SESSION"]),
                    CONFIG["API_ID"],
                    CONFIG["API_HASH"],
                    app_version="الجوكر 1.0",
                    auto_reconnect=True,
                    connection_retries=None,
                )
                if new_login and phone:
                    client.start(phone=lambda: phone)
                else:
                    client.start()
            else:
                print("بيانات غير صحيحة — أغلق وأعد التشغيل")
                sys.exit(1)
        else:
            print(f"خطأ بتسجيل الدخول: {e}")
            if new_login:
                client.start()
    if new_login:
        try:
            session_str = client.session.save()
            save_session(session_str)
            print("=" * 45)
            print("  تم تسجيل الدخول وحفظ كود السيشن تلقائياً ✓")
            print("  لن يُطلب منك تسجيل الدخول مرة أخرى")
            print("=" * 45)
        except Exception:
            pass
    try:
        client.loop.run_until_complete(_startup())
        while True:
            try:
                client.run_until_disconnected()
                break
            except Exception as e:
                print(f"انقطع الاتصال: {e}")
                print("إعادة الاتصال خلال 5 ثوان...")
                time.sleep(5)
                try:
                    client.loop.run_until_complete(client.connect())
                except Exception as e2:
                    print(f"فشل إعادة الاتصال: {e2}")
    finally:
        try:
            os.remove(os.path.join(DATA_DIR, "joker.lock"))
        except Exception:
            pass


if __name__ == "__main__":
    main()
