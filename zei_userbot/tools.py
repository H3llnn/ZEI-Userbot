"""Account and group tools implemented directly with Telegram methods."""
import hashlib
import html
from datetime import datetime, timezone
from telethon import functions, types

GROUPS = {
    "akun": {"whois":"Balas akun atau whois username", "setname":"setname nama depan", "setbio":"setbio deskripsi", "stats":"Statistik chat milik akun"},
    "admin": {"ban":"Balas anggota atau ban username", "unban":"unban username", "kick":"Balas anggota atau kick username", "pin":"Balas pesan", "unpin":"Lepas sematan", "promote":"Balas anggota", "demote":"Balas anggota", "invite":"invite username", "title":"title nama grup", "chatinfo":"Info chat"},
    "utilitas": {"hash":"hash teks (SHA-256)", "time":"Waktu UTC", "calc":"calc ekspresi matematika", "getlink":"Link pesan yang dibalas"},
    "otomatis": {"filter":"filter pemicu | balasan", "filters":"Daftar balasan otomatis", "delfilter":"delfilter pemicu", "welcome":"welcome pesan atau off", "pmpermit":"pmpermit on/off", "approve":"Balas akun atau approve username", "disapprove":"Balas akun atau disapprove username"},
}
COMMANDS = {k:v for group in GROUPS.values() for k,v in group.items()}


def calculate(text):
    import ast
    import operator
    ops = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
    if len(text) > 120: raise ValueError("Ekspresi terlalu panjang.")
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float) and abs(node.value) <= 10**12: return node.value
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            value=visit(node.operand);return -value if isinstance(node.op,ast.USub) else value
        if isinstance(node,ast.BinOp) and type(node.op) in ops:
            value=ops[type(node.op)](visit(node.left),visit(node.right))
            if abs(value)>10**15: raise ValueError("Hasil terlalu besar.")
            return value
        raise ValueError("Gunakan angka dan operator + - * / // % saja.")
    return visit(ast.parse(text,mode="eval").body)


async def target(event, arg):
    reply = await event.get_reply_message()
    if arg: return await event.client.get_entity(arg.strip())
    if reply: return await reply.get_sender()
    raise ValueError("Balas pesan anggota atau masukkan username.")


async def execute(runtime, cmd, arg, event):
    client, state, h = runtime.client, runtime.state, html.escape
    if cmd == "hash": return "🔐 SHA-256\n<code>"+hashlib.sha256(arg.encode()).hexdigest()+"</code>"
    if cmd == "time": return "🕒 "+datetime.now(timezone.utc).strftime("%d %B %Y · %H:%M:%S UTC")
    if cmd == "calc": return "🧮 <code>"+h(str(calculate(arg)))+"</code>"
    if cmd == "getlink":
        reply=await event.get_reply_message()
        if not reply: return "Balas pesan yang ingin kamu ambil linknya."
        chat=await event.get_chat()
        if getattr(chat,"username",None): return f'https://t.me/{chat.username}/{reply.id}'
        if event.chat_id and str(event.chat_id).startswith("-100"): return f'https://t.me/c/{str(event.chat_id)[4:]}/{reply.id}'
        return "🔎 Chat ini tidak memiliki link pesan yang dapat dibagikan."
    if cmd == "whois":
        entity=await target(event,arg) if arg or event.is_reply else await client.get_me()
        name=" ".join(x for x in (getattr(entity,"first_name",None),getattr(entity,"last_name",None)) if x)
        return f'👤 <b>{h(name or getattr(entity,"title","Akun"))}</b>\nID: <code>{entity.id}</code>\nUsername: {h(getattr(entity,"username",None) or "—")}'
    if cmd == "setname":
        if not 1 <= len(arg) <= 64: return "Gunakan nama depan 1–64 karakter."
        await client(functions.account.UpdateProfileRequest(first_name=arg))
        return "✅ Nama akun diperbarui."
    if cmd == "setbio":
        if len(arg)>70: return "Bio maksimal 70 karakter."
        await client(functions.account.UpdateProfileRequest(about=arg))
        return "✅ Bio akun diperbarui."
    if cmd == "stats":
        count=groups=channels=private=0
        async for dialog in client.iter_dialogs():
            count+=1
            if dialog.is_user: private+=1
            elif dialog.is_group: groups+=1
            else: channels+=1
        return f"✦ Ruang akunmu\nChat: {count}\nPribadi: {private}\nGrup: {groups}\nChannel: {channels}"
    if cmd in ("approve","disapprove"):
        entity=await target(event,arg)
        values=set(state.get("approved",[]))
        if cmd=="approve": values.add(entity.id)
        else: values.discard(entity.id)
        state.set("approved",sorted(values))
        return "✅ Izin pesan pribadi diperbarui."
    if cmd=="pmpermit":
        if arg not in ("on","off"): return "Gunakan pmpermit on atau pmpermit off."
        state.set("pmpermit",arg=="on")
        return "🔐 Perlindungan pesan pribadi "+("aktif. Pesan dari akun belum disetujui akan mendapat pemberitahuan satu kali; tidak diblokir otomatis." if arg=="on" else "dimatikan.")
    if cmd in ("filter","filters","delfilter"):
        filters=state.get("filters",{})
        if cmd=="filters": return "✦ Balasan otomatis\n"+("\n".join(h(k) for k in filters) or "Belum ada pemicu.")
        if cmd=="delfilter": filters.pop(arg.lower(),None)
        else:
            key,sep,value=arg.partition("|")
            key,value=key.strip().lower(),value.strip()
            if not sep or not key or len(key)>60 or not value or len(value)>2000: return "Gunakan filter pemicu | balasan (pemicu maks. 60 karakter)."
            if key not in filters and len(filters)>=100: return "Maksimal 100 pemicu per akun."
            filters[key]=value
        state.set("filters",filters)
        return "✅ Balasan otomatis diperbarui."
    if event.is_private: return "🔎 Perintah ini digunakan di grup atau channel."
    if cmd=="chatinfo":
        chat=await event.get_chat()
        return f'✦ <b>{h(getattr(chat,"title","Chat"))}</b>\nID: <code>{event.chat_id}</code>\nAnggota: {getattr(chat,"participants_count",None) or "—"}'
    if cmd=="welcome":
        if not arg or len(arg)>2000: return "Gunakan welcome pesan atau welcome off."
        values=state.get("welcomes",{})
        if arg=="off": values.pop(str(event.chat_id),None)
        else: values[str(event.chat_id)]=arg
        state.set("welcomes",values)
        return "✅ Pesan sambutan diperbarui. Gunakan {nama} untuk menyebut anggota."
    if cmd in ("ban","kick","unban","promote","demote"):
        entity=await target(event,arg)
        if entity.id == runtime.owner: return "🔎 Pilih anggota lain."
        if cmd=="kick": await client.kick_participant(event.chat_id,entity)
        elif cmd in ("ban","unban"): await client.edit_permissions(event.chat_id,entity,view_messages=cmd=="unban")
        else:
            active=cmd=="promote"
            await client.edit_admin(event.chat_id,entity,change_info=active,post_messages=active,edit_messages=active,delete_messages=active,ban_users=active,invite_users=active,pin_messages=active,add_admins=False,is_admin=active)
        return "✅ Pengaturan anggota diperbarui."
    if cmd=="invite":
        entity=await target(event,arg)
        chat=await event.get_chat()
        if isinstance(chat,types.Chat): await client(functions.messages.AddChatUserRequest(chat.id,entity,fwd_limit=0))
        else: await client(functions.channels.InviteToChannelRequest(chat,[entity]))
        return "✅ Undangan anggota dikirim."
    if cmd in ("pin","unpin"):
        reply=await event.get_reply_message()
        if cmd=="pin" and not reply: return "Balas pesan yang ingin disematkan."
        if cmd=="pin": await client.pin_message(event.chat_id,reply.id,notify=False)
        else: await client.unpin_message(event.chat_id,reply.id if reply else None)
        return "✅ Sematan diperbarui."
    if cmd=="title":
        if not 1<=len(arg)<=128: return "Nama grup harus 1–128 karakter."
        chat=await event.get_chat()
        if isinstance(chat,types.Chat): await client(functions.messages.EditChatTitleRequest(chat.id,arg))
        else: await client(functions.channels.EditTitleRequest(chat,arg))
        return "✅ Nama chat diperbarui."
