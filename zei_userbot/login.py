"""Ephemeral Telegram login. OTP/password never reach persistent storage."""
import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, PasswordHashInvalidError, FloodWaitError


def validate_api(api_id, api_hash):
    if type(api_id) is not int or api_id <= 0 or not isinstance(api_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{32}", api_hash):
        raise ValueError("Periksa API ID dan API Hash milikmu.")


class Login:
    def __init__(self, owner, api_id, api_hash, client_factory=TelegramClient):
        validate_api(api_id, api_hash)
        self.owner, self.api_id, self.api_hash = owner, api_id, api_hash
        self.client = client_factory(StringSession(), api_id, api_hash, receive_updates=False, connection_retries=1, request_retries=1)
        self.phone = self.code_hash = None
        self.ready = False

    async def begin(self, phone):
        if not isinstance(phone, str) or not re.fullmatch(r"\+[1-9][0-9]{6,14}", phone):
            raise ValueError("Gunakan nomor internasional, misalnya +628123456789.")
        await self.client.connect()
        result = await self.client.send_code_request(phone)
        self.phone, self.code_hash = phone, result.phone_code_hash
        return "otp"

    async def code(self, code):
        if not self.phone or not self.code_hash: raise ValueError("Minta kode login terlebih dahulu.")
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{4,8}", code): raise ValueError("Masukkan kode Telegram yang valid.")
        try:
            await self.client.sign_in(phone=self.phone, code=code, phone_code_hash=self.code_hash)
        except SessionPasswordNeededError:
            return {"step": "password"}
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            raise ValueError("Kode salah atau kedaluwarsa. Periksa kode atau mulai lagi.") from None
        return await self.identity()

    async def password(self, password):
        if not isinstance(password, str) or not 1 <= len(password) <= 256: raise ValueError("Masukkan password 2FA.")
        try:
            await self.client.sign_in(password=password)
        except PasswordHashInvalidError:
            raise ValueError("Password 2FA belum sesuai.") from None
        return await self.identity()

    async def identity(self):
        me = await self.client.get_me()
        self.ready = True
        if not me or me.bot or me.id != self.owner:
            await self.close(discard=True)
            raise PermissionError("Gunakan akun Telegram yang sama dengan akun pembuka bot induk.")
        self.ready = True
        return {"step": "summary", "name": " ".join(x for x in (me.first_name, me.last_name) if x), "username": me.username or "", "id": me.id}

    def credentials(self):
        if not self.ready: raise ValueError("Login belum selesai.")
        return {"api_id": self.api_id, "api_hash": self.api_hash, "session": self.client.session.save()}

    async def close(self, discard=False):
        try:
            if discard and self.ready:
                await self.client.log_out()
        finally:
            self.ready = False
            self.phone = self.code_hash = None
            await self.client.disconnect()
