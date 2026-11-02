"""Original owner-only commands. No shell/eval or third-party startup code."""
import asyncio
import html
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from .state import State
from .tools import GROUPS, COMMANDS, execute as execute_tool

CATEGORIES = {
    "dasar": {"ping": "Cek koneksi", "id": "Lihat ID akun/chat", "help": "Buka bantuan"},
    "catatan": {"save": "Balas teks: save nama", "notes": "Daftar catatan", "get": "get nama", "delnote": "delnote nama"},
    "pesan": {"purge": "Balas pesan awal: purge (maks. 100 pesan milikmu)", "say": "say teks", "afk": "afk alasan", "unafk": "Matikan AFK"},
    "pengaturan": {"prefix": "prefix simbol", "status": "Status ruangmu"},
}
CATEGORIES.update(GROUPS)
HELP = {k: v for group in CATEGORIES.values() for k, v in group.items()}


class Runtime:
    def __init__(self, owner, credentials, path, helper="", client_factory=TelegramClient):
        self.owner, self.helper = owner, helper
        self.state = State(path)
        self.client = client_factory(StringSession(credentials["session"]), credentials["api_id"], credentials["api_hash"], connection_retries=1, request_retries=1)
        self.started = time.monotonic()
        self.afk_cooldown = {}
        self.permit_notified = set()
        self.filter_cooldown = {}

    async def start(self):
        try:
            await self.client.connect()
            me = await self.client.get_me()
            if not me or me.id != self.owner or me.bot:
                raise PermissionError("Identitas sesi Userbot tidak cocok.")
            self.client.add_event_handler(self.command, events.NewMessage(outgoing=True))
            self.client.add_event_handler(self.incoming, events.NewMessage(incoming=True))
            self.client.add_event_handler(self.welcome, events.ChatAction())
        except BaseException:
            await self.client.disconnect()
            raise

    async def stop(self):
        await self.client.disconnect()
        self.state.close()

    def parse(self, text, sender, outgoing=True):
        if not outgoing or sender != self.owner or not text.startswith(self.state.prefix): return None
        parts = text[len(self.state.prefix):].split(maxsplit=1)
        if not parts or parts[0].lower() not in HELP: return None
        return parts[0].lower(), parts[1] if len(parts) > 1 else ""

    async def command(self, event):
        parsed = self.parse(event.raw_text or "", event.sender_id, event.out)
        if parsed is None: return
        cmd, arg = parsed
        try:
            text = await self.execute(cmd, arg, event)
            if text is not None: await event.edit(text, parse_mode="html", link_preview=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            await event.edit("🔎 Belum berhasil. Periksa format perintah, izin chat, dan koneksi, lalu coba lagi.")

    async def execute(self, cmd, arg, event):
        h = html.escape
        if cmd in COMMANDS: return await execute_tool(self,cmd,arg,event)
        if cmd == "ping":
            start = time.monotonic()
            await event.edit("⚡ Menghubungkan…")
            return f"⚡ Pong · {round((time.monotonic()-start)*1000)} ms"
        if cmd == "help":
            if self.helper:
                try:
                    results = await self.client.inline_query(self.helper, "zei-help")
                    if results:
                        await results[0].click(event.chat_id, reply_to=event.reply_to_msg_id)
                        await event.delete()
                        return None
                except Exception:
                    pass
            return self.help_text()
        if cmd == "prefix":
            self.state.set("prefix", arg)
            return f"✅ Prefix diperbarui\nSekarang gunakan <code>{h(self.state.prefix)}help</code> untuk membuka menu."
        if cmd == "id":
            reply = await event.get_reply_message()
            return f"✦ ID chat: <code>{event.chat_id}</code>\nID akun: <code>{reply.sender_id if reply else self.owner}</code>"
        if cmd == "status":
            return f"✦ ZΞI Userbot\n🟢 Aktif · {int(time.monotonic()-self.started)} detik\nPrefix: <code>{h(self.state.prefix)}</code>\nMaintained by Zeisss"
        if cmd == "save":
            reply = await event.get_reply_message()
            if not arg or len(arg) > 40 or not reply or not reply.raw_text: return "Balas pesan teks dengan <code>save nama</code>."
            with self.state.conn:
                self.state.conn.execute("INSERT INTO notes VALUES (?,?) ON CONFLICT(name) DO UPDATE SET text=excluded.text", (arg, reply.raw_text))
            return f"✅ Catatan <b>{h(arg)}</b> tersimpan."
        if cmd == "notes":
            rows = self.state.conn.execute("SELECT name FROM notes ORDER BY name LIMIT 50").fetchall()
            return "🗒 Catatanmu\n" + ("\n".join(h(r[0]) for r in rows) or "Belum ada catatan.")
        if cmd == "get":
            row = self.state.conn.execute("SELECT text FROM notes WHERE name=?", (arg,)).fetchone()
            return h(row[0]) if row else "🔎 Catatan belum ditemukan."
        if cmd == "delnote":
            with self.state.conn: self.state.conn.execute("DELETE FROM notes WHERE name=?", (arg,))
            return "✅ Catatan dihapus."
        if cmd == "say": return h(arg) if arg else "Tulis teks setelah perintah say."
        if cmd == "afk":
            self.state.set("afk", arg[:500] or "Sedang tidak tersedia.")
            return "🌙 AFK aktif. Aku akan membalas pesan pribadi untukmu."
        if cmd == "unafk":
            self.state.set("afk", None)
            return "✨ Selamat datang kembali. AFK dimatikan."
        if cmd == "purge":
            reply = await event.get_reply_message()
            if not reply or reply.id >= event.id: return "Balas pesan awal yang ingin kamu hapus."
            ids = []
            async for msg in self.client.iter_messages(event.chat_id, min_id=reply.id-1, max_id=event.id+1, limit=101):
                if msg.sender_id == self.owner: ids.append(msg.id)
                if len(ids) > 100: return "Maksimal 100 pesan milikmu per perintah. Pilih rentang lebih kecil."
            await self.client.delete_messages(event.chat_id, ids)
            return None

    def help_text(self, category=None):
        groups = {category: CATEGORIES[category]} if category in CATEGORIES else CATEGORIES
        text = "✦ <b>ZΞI Userbot</b>\nSemua kendali ada di tanganmu.\n\n"
        for name, commands in groups.items():
            text += f"<b>{html.escape(name.title())}</b>\n" + "\n".join(f"<code>{html.escape(self.state.prefix+k)}</code> · {html.escape(v)}" for k,v in commands.items()) + "\n\n"
        return text + "<i>Maintained by Zeisss</i>"

    async def incoming(self, event):
        if event.sender_id == self.owner: return
        now = time.monotonic()
        if event.is_private:
            sender = await event.get_sender()
            if not sender or sender.bot: return
            if self.state.get('pmpermit',False) and sender.id not in self.state.get('approved',[]) and not getattr(sender,'contact',False):
                if sender.id not in self.permit_notified:
                    if len(self.permit_notified)>1000: self.permit_notified.clear()
                    self.permit_notified.add(sender.id)
                    await event.reply('🔐 Pesanmu sudah diterima. Tunggu pemilik akun mengizinkan percakapan, ya.',parse_mode=None)
                return
            reason = self.state.get('afk')
            if reason and now-self.afk_cooldown.get(event.chat_id,-301)>=300:
                self.afk_cooldown[event.chat_id]=now
                if len(self.afk_cooldown)>1000: self.afk_cooldown={k:v for k,v in self.afk_cooldown.items() if now-v<300}
                await event.reply('🌙 Pemilik akun sedang tidak tersedia.\n'+reason,parse_mode=None)
                return
        text=(event.raw_text or '').strip().lower()
        answer=self.state.get('filters',{}).get(text)
        if answer and now-self.filter_cooldown.get(event.chat_id,-31)>=30:
            self.filter_cooldown[event.chat_id]=now
            if len(self.filter_cooldown)>1000: self.filter_cooldown={k:v for k,v in self.filter_cooldown.items() if now-v<30}
            await event.reply(answer,parse_mode=None)

    async def welcome(self,event):
        if not (event.user_joined or event.user_added): return
        text=self.state.get('welcomes',{}).get(str(event.chat_id))
        if not text: return
        users=await event.get_users()
        names=', '.join((getattr(user,'first_name','') or 'teman') for user in users)
        await event.reply(text.replace('{nama}',names),parse_mode=None)
