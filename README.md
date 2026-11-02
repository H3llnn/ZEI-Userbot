# ZΞI Userbot

**ZΞI Project · Maintained by Zeisss**

Runtime akun Telegram untuk pengguna yang diizinkan melalui ZΞI Gate. Fondasi ditulis baru; tidak menjalankan startup atau memuat modul Man-Userbot.

## Pemakaian

Pasang bersama folder ZEI-Gate melalui python install.py di Gate. Runtime diluncurkan oleh Gate setelah login melalui Mini App. Jangan menjalankan worker langsung dengan argumen sesi; Gate mengirim kredensial lewat stdin privat dan menyimpan sesi terenkripsi.

Satu akun per pengguna, ID harus sama dengan pembuka bot induk. Pengguna mengendalikan akunnya sendiri melalui .help di chat tempat ia dapat mengirim pesan. Prefix bisa diubah dengan .prefix ! atau tombol pengaturan yang membuka bot induk secara privat. Prefix dan catatan tetap tersimpan saat koneksi ulang.

## Perintah tersedia

- Dasar: help, ping, id, status, prefix.
- Catatan teks: save, notes, get, delnote.
- Pesan: say, purge (maksimal 100 pesan milik sendiri), afk, unafk.
- Akun: whois, setname, setbio, stats.
- Admin grup/channel: ban, unban, kick, pin, unpin, promote, demote, invite, title, chatinfo. Tetap memerlukan hak Telegram yang sesuai.
- Utilitas: hash SHA-256, time UTC, calc tanpa evaluasi kode, getlink.
- Otomatis: filter, filters, delfilter, welcome, pmpermit, approve, disapprove. PMpermit memberi pemberitahuan, tidak memblokir orang otomatis; kontak dibebaskan. AFK dan filter memiliki jeda balasan.

Semua perintah hanya menerima pesan keluar dari ID pemilik. Pengaturan/kredensial setiap akun terpisah. Server tidak menyediakan shell/eval, unggah file sistem server, atau perintah sudo pengguna lain.

## Cakupan referensi

Ini belum setara seluruh modul Man-Userbot. Inventaris [MODULES.md](MODULES.md) menunjukkan modul yang sudah memiliki padanan dasar dan yang belum tersedia; padanan dasar tidak berarti seluruh opsi modul aslinya telah dipindahkan. Fitur yang membutuhkan layanan eksternal atau perangkat media belum diaktifkan hanya untuk membuat daftar terlihat lengkap.

## Uji

`sh
python -m pip install .
python -m unittest discover -s tests -v
`

Uji akun nyata, OTP, 2FA, hak admin grup, dan mode inline masih memerlukan akun/server Telegram milik pemilik. Tes otomatis menggunakan objek Telegram tiruan.

## Lisensi dan sumber

GPL-3.0; lihat LICENSE dan THIRD_PARTY_NOTICES.md. Fondasi milik proyek ini tetap mengakui pustaka serta repo referensi, dan tidak mengklaim kode pihak lain sebagai ciptaan baru.
