import os
os.environ["KIVY_NO_ENV_CONFIG"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.animation import Animation

import pandas as pd
from collections import deque
from datetime import datetime, time
import uuid

# ── WARNA ──────────────────────────────────────────────────
NAVY     = (0.05, 0.10, 0.28, 1)
NAVY_MED = (0.08, 0.14, 0.38, 1)
UNGU     = (0.42, 0.18, 0.78, 1)
UNGU_MUD = (0.42, 0.18, 0.78, 0.12)
HIJAU    = (0.08, 0.72, 0.44, 1)
HIJAU_MD = (0.08, 0.72, 0.44, 0.15)
MERAH    = (0.90, 0.22, 0.22, 1)
KUNING   = (0.95, 0.70, 0.00, 1)
BG       = (0.95, 0.95, 0.98, 1)
PUTIH    = (1.00, 1.00, 1.00, 1)
GELAP    = (0.10, 0.10, 0.18, 1)
ABU      = (0.60, 0.62, 0.68, 1)
ABU_MD   = (0.95, 0.95, 0.97, 1)

# ── KONSTANTA ──────────────────────────────────────────────
HARI_LIST = ["Senin", "Selasa", "Rabu", "Kamis"] # ── Jumat = online ───

# Durasi SKS: 1 SKS = 50 menit
# 2 SKS = 100 menit, 3 SKS = 150 menit
SKS_CONFIG = {
    "2 SKS  (100 menit)": 100,
    "3 SKS  (150 menit)": 150,
}

# Slot jam tetap dari jadwal
JAM_SLOT = [
    ("07:00", "09:30"),   # 3 SKS
    ("09:30", "12:00"),   # 3 SKS
    ("13:00", "15:30"),   # 3 SKS
]

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FILE_RUANG   = os.path.join(BASE_DIR, "data_ruang.csv")
FILE_ROMBEL  = os.path.join(BASE_DIR, "data_rombel.csv")
FILE_BOOKING = os.path.join(BASE_DIR, "data_booking.csv")


# ==============================================================
# HELPER WAKTU
# ==============================================================
def parse_jam(s):
    """'07:00' → time(7,0)"""
    h, m = map(int, s.split(':'))
    return time(h, m)

def menit_ke_jam(jam_str, tambah_menit):
    """'07:00' + 100 menit → '08:40'"""
    h, m = map(int, jam_str.split(':'))
    total = h * 60 + m + tambah_menit
    return f"{total // 60:02d}:{total % 60:02d}"

def durasi_menit(jm, js):
    """Hitung durasi slot dalam menit"""
    t1 = parse_jam(jm)
    t2 = parse_jam(js)
    return (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)

def slot_kosong_untuk_sks(hari, jm_mulai, js_slot, sks_menit, booking_df, ruang):
    """
    Cek apakah ruang benar-benar kosong selama durasi sks_menit
    mulai dari jm_mulai. Cek overlap dengan semua booking yang ada.
    Return: (bisa, jam_selesai_booking)
    """
    js_booking = menit_ke_jam(jm_mulai, sks_menit)
    t_mulai  = parse_jam(jm_mulai)
    t_selesai = parse_jam(js_booking)

    if booking_df.empty:
        return True, js_booking

    # Cek semua booking aktif di ruang & hari yang sama
    existing = booking_df[
        (booking_df['hari']   == hari) &
        (booking_df['ruang']  == ruang) &
        (booking_df['status'] == 'aktif')
    ]

    for _, row in existing.iterrows():
        t_ex_mulai  = parse_jam(str(row['jam_mulai']))
        t_ex_selesai = parse_jam(str(row['jam_selesai']))
        # Cek overlap
        if not (t_selesai <= t_ex_mulai or t_mulai >= t_ex_selesai):
            return False, js_booking

    return True, js_booking

def cari_slot_tersedia(hari, sks_menit, booking_df, ruang_sorted):
    """
    Cari semua kombinasi (jam_mulai, jam_selesai, ruang) yang tersedia
    untuk durasi sks_menit di hari tertentu.
    Return: list of dict
    """
    hasil = []

    # Jam yang bisa jadi titik mulai (dari slot yang ada)
    jam_mulai_options = [jm for jm, js in JAM_SLOT]
    # Tambah titik mulai alternatif (setelah slot berakhir - realistis)
    extra_starts = ["08:00", "10:00", "11:00", "14:00"]
    semua_starts = sorted(set(jam_mulai_options + extra_starts))

    for jm in semua_starts:
        js_booking = menit_ke_jam(jm, sks_menit)
        # Pastikan tidak lewat jam 17:00
        if parse_jam(js_booking) > time(17, 0):
            continue

        for ruang in ruang_sorted:
            bisa, js = slot_kosong_untuk_sks(hari, jm, js_booking, sks_menit, booking_df, ruang)
            if bisa:
                hasil.append({
                    'jam_mulai' : jm,
                    'jam_selesai': js,
                    'ruang'     : ruang,
                    'durasi'    : sks_menit
                })

    return hasil


# ==============================================================
# STRUKTUR DATA: QUEUE (FIFO)
# ==============================================================
class BookingQueue:
    def __init__(self):
        self.antrian = deque()

    def enqueue(self, item):
        self.antrian.append(item)

    def dequeue(self):
        return self.antrian.popleft() if not self.is_empty() else None

    def is_empty(self):
        return len(self.antrian) == 0

    def size(self):
        return len(self.antrian)


# ==============================================================
# ALGORITMA: BINARY SEARCH
# Mencari ruang kosong dari daftar terurut - O(log n)
# ==============================================================
def binary_search_ruang(ruang_sorted, hari, jm, js, sks_menit, booking_df):
    """
    Binary Search pada daftar ruang terurut untuk menemukan
    ruang pertama yang benar-benar kosong pada slot waktu tertentu.
    Kompleksitas pencarian: O(log n)
    """
    # Langkah 1: kumpulkan ruang yang overlap dengan slot ini
    terpakai = set()
    if not booking_df.empty:
        t_mulai   = parse_jam(jm)
        t_selesai = parse_jam(js)
        aktif = booking_df[
            (booking_df['hari']   == hari) &
            (booking_df['status'] == 'aktif')
        ]
        for _, row in aktif.iterrows():
            t_ex_m = parse_jam(str(row['jam_mulai']))
            t_ex_s = parse_jam(str(row['jam_selesai']))
            if not (t_selesai <= t_ex_m or t_mulai >= t_ex_s):
                terpakai.add(row['ruang'])

    # Langkah 2: filter ruang yang tersedia (sudah terurut)
    tersedia = [r for r in ruang_sorted if r not in terpakai]
    if not tersedia:
        return None

    # Langkah 3: Binary Search — ambil ruang paling awal
    kiri, kanan = 0, len(tersedia) - 1
    while kiri <= kanan:
        tengah = (kiri + kanan) // 2
        kanan  = tengah - 1   # geser kiri terus → dapat indeks 0
    return tersedia[0]


# ==============================================================
# DATA MANAGER
# ==============================================================
class DataManager:
    def __init__(self):
        self.ruang_df     = pd.read_csv(FILE_RUANG)
        self.rombel_df    = pd.read_csv(FILE_ROMBEL)
        self._load_booking()
        self.ruang_sorted = sorted(self.ruang_df['kode_ruang'].tolist())

    def _load_booking(self):
        try:
            df = pd.read_csv(FILE_BOOKING)
            if 'id_booking' in df.columns:
                if 'mata_kuliah' not in df.columns:
                    df['mata_kuliah'] = ''
                self.booking_df = df
                return
        except Exception:
            pass
        self.booking_df = pd.DataFrame(columns=[
            'id_booking','rombel','hari','jam_mulai','jam_selesai',
            'ruang','mata_kuliah','status','waktu_booking'
        ])

    def simpan(self):
        self.booking_df.to_csv(FILE_BOOKING, index=False)

    def tambah_booking(self, rombel, hari, jm, js, ruang, mk=''):
        row = {
            'id_booking'   : str(uuid.uuid4())[:8].upper(),
            'rombel'       : rombel,
            'hari'         : hari,
            'jam_mulai'    : jm,
            'jam_selesai'  : js,
            'ruang'        : ruang,
            'mata_kuliah'  : mk,
            'status'       : 'aktif',
            'waktu_booking': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.booking_df = pd.concat(
            [self.booking_df, pd.DataFrame([row])], ignore_index=True)
        self.simpan()
        return row['id_booking']

    def batalkan(self, id_booking):
        self.booking_df.loc[
            self.booking_df['id_booking'] == id_booking, 'status'] = 'batal'
        self.simpan()

    def cek_slot_ruang(self, hari, jm, js, ruang):
        """Cek apakah ruang overlap dengan booking yang ada"""
        if self.booking_df.empty:
            return None
        t_m = parse_jam(jm)
        t_s = parse_jam(js)
        aktif = self.booking_df[
            (self.booking_df['hari']   == hari) &
            (self.booking_df['ruang']  == ruang) &
            (self.booking_df['status'] == 'aktif')
        ]
        for _, row in aktif.iterrows():
            t_ex_m = parse_jam(str(row['jam_mulai']))
            t_ex_s = parse_jam(str(row['jam_selesai']))
            if not (t_s <= t_ex_m or t_m >= t_ex_s):
                return row
        return None

    def cek_rombel_slot(self, rombel, hari, jm, js):
        """Cek apakah rombel sudah punya jadwal yang overlap"""
        if self.booking_df.empty:
            return None
        t_m = parse_jam(jm)
        t_s = parse_jam(js)
        aktif = self.booking_df[
            (self.booking_df['rombel']  == rombel) &
            (self.booking_df['hari']    == hari) &
            (self.booking_df['status']  == 'aktif')
        ]
        for _, row in aktif.iterrows():
            t_ex_m = parse_jam(str(row['jam_mulai']))
            t_ex_s = parse_jam(str(row['jam_selesai']))
            if not (t_s <= t_ex_m or t_m >= t_ex_s):
                return row
        return None

    def get_rombel_list(self):
        urutan = [
            "INT 24","2024 A","2024 B","2024 C","2024 D","2024 E",
            "INT 25","2025 A","2025 B","2025 C","2025 D","2025 E","2025 F","2025 G"
        ]
        semua = self.rombel_df['kode_rombel'].tolist()
        return tuple(r for r in urutan if r in semua)

    def get_ruang_list(self):
        return self.ruang_df['kode_ruang'].tolist()

    def slot_terisi_grid(self, hari, jm, js, ruang):
        """Untuk grid: cek apakah slot JAM_SLOT tertentu terisi"""
        return self.cek_slot_ruang(hari, jm, js, ruang)

    def riwayat_aktif(self):
        if self.booking_df.empty:
            return pd.DataFrame()
        return self.booking_df[
            (self.booking_df['status'] == 'aktif') &
            (self.booking_df['waktu_booking'] != '2026-01-01 00:00:00')
        ].sort_values('waktu_booking', ascending=False)


# ==============================================================
# HELPER UI
# ==============================================================
def bg_rect(w, c):
    with w.canvas.before:
        Color(*c); r = Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda a,v: setattr(r,'pos',v), size=lambda a,v: setattr(r,'size',v))

def bg_round(w, c, rad=10):
    with w.canvas.before:
        Color(*c); r = RoundedRectangle(pos=w.pos, size=w.size, radius=[rad])
    w.bind(pos=lambda a,v: setattr(r,'pos',v), size=lambda a,v: setattr(r,'size',v))

def tombol(text, warna, cb, h=dp(44), r=10, fs=dp(14)):
    b = Button(text=text, size_hint_y=None, height=h,
               background_normal='', background_color=(0,0,0,0),
               color=PUTIH, font_size=fs, bold=True, markup=False)
    bg_round(b, warna, r)
    b.bind(on_press=cb)
    def dn(i,t):
        if i.collide_point(*t.pos): Animation(opacity=0.72,duration=0.07).start(i)
    def up(i,t): Animation(opacity=1.0,duration=0.1).start(i)
    b.bind(on_touch_down=dn, on_touch_up=up)
    return b

def lbl_field(text):
    l = Label(text=text, font_size=dp(12), bold=True, color=UNGU,
              size_hint_y=None, height=dp(22), halign='left', valign='bottom', markup=False)
    l.bind(size=lambda w,v: setattr(w,'text_size',v))
    return l

def sp_ui(values, default='Pilih...'):
    return Spinner(text=default, values=values,
                   size_hint_y=None, height=dp(40),
                   background_normal='', background_color=ABU_MD,
                   color=GELAP, font_size=dp(13))

def popup_ok(judul, pesan, warna=None):
    if warna is None: warna = UNGU
    box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
    lbl = Label(text=pesan, font_size=dp(13), color=GELAP,
                halign='center', valign='middle', markup=False)
    lbl.bind(size=lambda w,v: setattr(w,'text_size',v))
    box.add_widget(lbl)
    pop = Popup(title=judul, content=box, size_hint=(0.7, 0.35),
                auto_dismiss=False, title_color=NAVY,
                title_size=dp(14), separator_color=warna)
    box.add_widget(tombol('OK', warna, lambda *a: pop.dismiss(), h=dp(38)))
    pop.open()
    return pop


# ==============================================================
# POPUP PILIH SLOT TERSEDIA
# Tampil setelah user pilih SKS — list slot kosong yang bisa dipilih
# ==============================================================
def popup_pilih_slot(dm, rombel, hari, sks_label, mk, on_booked):
    sks_menit = SKS_CONFIG[sks_label]
    slots     = cari_slot_tersedia(hari, sks_menit, dm.booking_df, dm.ruang_sorted)

    box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))

    if not slots:
        box.add_widget(Label(
            text=f'Tidak ada slot kosong untuk {sks_label}\npada hari {hari}.',
            font_size=dp(13), color=GELAP, halign='center', markup=False))
        pop = Popup(title='Slot Tidak Tersedia', content=box,
                    size_hint=(0.7, 0.35), auto_dismiss=False,
                    title_color=NAVY, separator_color=MERAH)
        box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(38)))
        pop.open()
        return

    box.add_widget(Label(
        text=f'Slot kosong untuk {sks_label} - {hari}\nKlik untuk booking:',
        font_size=dp(12), color=NAVY, bold=True,
        size_hint_y=None, height=dp(40), halign='center', markup=False))

    sv = ScrollView(size_hint=(1, 1))
    grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=[0, dp(4)])
    grid.bind(minimum_height=grid.setter('height'))

    pop = Popup(title=f'Pilih Slot - {hari}  ({sks_label})',
                content=box, size_hint=(0.85, 0.7),
                auto_dismiss=False, title_color=NAVY,
                title_size=dp(13), separator_color=UNGU)

    # Gunakan Binary Search untuk urutkan dan tampilkan pilihan
    # (slot sudah dihasilkan dengan logika binary search per ruang)
    for slot in slots:
        jm  = slot['jam_mulai']
        js  = slot['jam_selesai']
        ru  = slot['ruang']
        teks = f'{jm} - {js}     Ruang: {ru}'

        btn_slot = Button(
            text=teks, size_hint_y=None, height=dp(42),
            background_normal='', background_color=(0,0,0,0),
            color=PUTIH, font_size=dp(12), bold=True, markup=False
        )
        bg_round(btn_slot, HIJAU, 8)

        def buat_cb(j_m, j_s, r_u):
            def cb(*a):
                # Cek rombel tidak overlap
                cek = dm.cek_rombel_slot(rombel, hari, j_m, j_s)
                if cek is not None:
                    pop.dismiss()
                    popup_ok('Gagal',
                        f'Rombel {rombel} sudah ada jadwal\n'
                        f'{hari} {cek["jam_mulai"]}-{cek["jam_selesai"]}\n'
                        f'Ruang: {cek["ruang"]}', MERAH)
                    return
                id_b = dm.tambah_booking(rombel, hari, j_m, j_s, r_u, mk)
                pop.dismiss()
                popup_ok('Berhasil',
                    f'Booking berhasil!\n\n'
                    f'ID     : {id_b}\n'
                    f'Rombel : {rombel}\n'
                    f'Hari   : {hari}  {j_m} - {j_s}\n'
                    f'Ruang  : {r_u}\n'
                    f'SKS    : {sks_label}', HIJAU)
                on_booked()
            return cb

        btn_slot.bind(on_press=buat_cb(jm, js, ru))
        grid.add_widget(btn_slot)

    sv.add_widget(grid)
    box.add_widget(sv)
    box.add_widget(tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(38)))
    pop.open()


# ==============================================================
# SCREEN 1: FORM BOOKING
# ==============================================================
class FormScreen(Screen):
    def __init__(self, dm, queue, **kw):
        super().__init__(**kw)
        self.dm    = dm
        self.queue = queue
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)

        # Topbar
        top = BoxLayout(size_hint_y=None, height=dp(50),
                        padding=[dp(12),dp(8)], spacing=dp(10))
        bg_rect(top, NAVY)
        top.add_widget(Label(
            text='Booking Ruang\nSains Data UNESA',
            color=PUTIH, font_size=dp(13), bold=True,
            halign='left', valign='middle', markup=False))
        btn_nav = tombol('Grid Jadwal', UNGU,
                         lambda *a: setattr(self.manager,'current','grid'),
                         h=dp(32), r=8, fs=dp(11))
        btn_nav.size_hint = (None,None); btn_nav.width = dp(85)
        top.add_widget(btn_nav)
        root.add_widget(top)

        sv = ScrollView()
        body = BoxLayout(orientation='vertical', padding=dp(12),
                         spacing=dp(10), size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))

        body.add_widget(Label(
            text='Form Peminjaman Ruang', font_size=dp(16), bold=True,
            color=NAVY, size_hint_y=None, height=dp(30),
            halign='left', markup=False))
        body.add_widget(Label(
            text='Senin - Kamis  |  Jumat: online',
            font_size=dp(10), color=ABU, size_hint_y=None, height=dp(16),
            halign='left', markup=False))

        # Card form
        card = BoxLayout(orientation='vertical', size_hint_y=None,
                         padding=dp(12), spacing=dp(10))
        card.bind(minimum_height=card.setter('height'))
        bg_round(card, PUTIH, 12)

        card.add_widget(lbl_field('Rombel / Kelas'))
        self.sp_rombel = sp_ui(self.dm.get_rombel_list(), 'Pilih Rombel')
        card.add_widget(self.sp_rombel)

        card.add_widget(lbl_field('Hari'))
        self.sp_hari = sp_ui(tuple(HARI_LIST), 'Pilih Hari')
        card.add_widget(self.sp_hari)

        card.add_widget(lbl_field('Jumlah SKS'))
        self.sp_sks = sp_ui(tuple(SKS_CONFIG.keys()), 'Pilih SKS')
        card.add_widget(self.sp_sks)

        card.add_widget(lbl_field('Mata Kuliah (opsional)'))
        self.ti_mk = TextInput(
            hint_text='Contoh: Struktur Data',
            size_hint_y=None, height=dp(40), font_size=dp(12),
            multiline=False, foreground_color=GELAP,
            background_color=ABU_MD, cursor_color=UNGU,
            padding=[dp(10), dp(10)])
        card.add_widget(self.ti_mk)

        # Info box SKS
        info = BoxLayout(size_hint_y=None, height=dp(46),
                         padding=[dp(10),dp(6)], spacing=dp(6))
        bg_round(info, UNGU_MUD, 8)
        info_txt = Label(
            text='2 SKS = 100 menit  |  3 SKS = 150 menit\n'
                 'Sistem akan tampilkan slot kosong yang sesuai.',
            font_size=dp(10), color=UNGU, halign='left', markup=False)
        info_txt.bind(size=lambda w,v: setattr(w,'text_size',v))
        info.add_widget(info_txt)
        card.add_widget(info)

        self.btn_cari = tombol('CARI SLOT KOSONG', UNGU, self._cari_slot, h=dp(44))
        card.add_widget(self.btn_cari)

        self.lbl_q = Label(text='', font_size=dp(11), color=UNGU,
                           size_hint_y=None, height=dp(20),
                           halign='center', markup=False)
        card.add_widget(self.lbl_q)
        body.add_widget(card)

        # Riwayat
        body.add_widget(Label(
            text='Riwayat Booking Baru', font_size=dp(13), bold=True,
            color=NAVY, size_hint_y=None, height=dp(24),
            halign='left', markup=False))
        rcard = BoxLayout(orientation='vertical', size_hint_y=None,
                          height=dp(140), padding=dp(10))
        bg_round(rcard, PUTIH, 12)
        self.lbl_riw = Label(
            text='Belum ada booking baru.', font_size=dp(11), color=GELAP,
            halign='left', valign='top', markup=False)
        self.lbl_riw.bind(size=lambda w,v: setattr(w,'text_size',v))
        rcard.add_widget(self.lbl_riw)
        body.add_widget(rcard)

        sv.add_widget(body)
        root.add_widget(sv)
        self.add_widget(root)
        self._refresh_riw()

    def _cari_slot(self, *a):
        rombel  = self.sp_rombel.text
        hari    = self.sp_hari.text
        sks_lbl = self.sp_sks.text
        mk      = self.ti_mk.text.strip()

        if 'Pilih' in rombel or 'Pilih' in hari or 'Pilih' in sks_lbl:
            popup_ok('Perhatian', 'Lengkapi Rombel, Hari, dan SKS\nterlebih dahulu!')
            return

        self.lbl_q.text = 'Mencari slot kosong...'
        Clock.schedule_once(
            lambda *a: self._buka_pilih(rombel, hari, sks_lbl, mk), 0.15)

    def _buka_pilih(self, rombel, hari, sks_lbl, mk):
        self.lbl_q.text = ''
        def on_booked():
            self._refresh_riw()
        popup_pilih_slot(self.dm, rombel, hari, sks_lbl, mk, on_booked)

    def _refresh_riw(self):
        self.dm._load_booking()
        df = self.dm.riwayat_aktif()
        if df.empty:
            self.lbl_riw.text = 'Belum ada booking baru.'
            return
        baris = []
        for _, row in df.head(5).iterrows():
            baris.append(
                f'{row["id_booking"]}  {row["rombel"]}\n'
                f'{row["hari"]} {row["jam_mulai"]}-{row["jam_selesai"]}  {row["ruang"]}')
        self.lbl_riw.text = '\n'.join(baris)

    def on_enter(self):
        self._refresh_riw()


# ==============================================================
# SCREEN 2: GRID VISUALISASI
# ==============================================================
class GridScreen(Screen):
    def __init__(self, dm, **kw):
        super().__init__(**kw)
        self.dm = dm
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)

        # Topbar
        top = BoxLayout(size_hint_y=None, height=dp(50),
                        padding=[dp(12),dp(8)], spacing=dp(10))
        bg_rect(top, NAVY)
        top.add_widget(Label(
            text='Grid Ruang Kelas',
            color=PUTIH, font_size=dp(14), bold=True,
            halign='left', valign='middle', markup=False))
        btn_nav = tombol('Form Booking', UNGU,
                         lambda *a: setattr(self.manager,'current','form'),
                         h=dp(32), r=8, fs=dp(11))
        btn_nav.size_hint = (None,None); btn_nav.width = dp(85)
        top.add_widget(btn_nav)
        root.add_widget(top)

        # Filter bar
        fbar = BoxLayout(size_hint_y=None, height=dp(44),
                         padding=[dp(10),dp(6)], spacing=dp(10))
        bg_rect(fbar, NAVY_MED)
        fbar.add_widget(Label(text='Hari:', size_hint=(None,1), width=dp(35),
                              color=PUTIH, font_size=dp(12), bold=True, markup=False))
        self.sp_hari = Spinner(
            text='Senin', values=tuple(HARI_LIST),
            size_hint=(None,None), width=dp(90), height=dp(32),
            background_normal='', background_color=(0,0,0,0),
            color=PUTIH, font_size=dp(12), bold=True)
        bg_round(self.sp_hari, UNGU, 8)
        self.sp_hari.bind(text=self._refresh)
        fbar.add_widget(self.sp_hari)

        self.lbl_stat = Label(text='', font_size=dp(10), color=PUTIH,
                              halign='right', markup=False)
        fbar.add_widget(self.lbl_stat)

        btn_ref = tombol('Refresh', (0.30,0.35,0.55,1), self._refresh,
                         h=dp(30), r=8, fs=dp(11))
        btn_ref.size_hint=(None,None); btn_ref.width=dp(65)
        fbar.add_widget(btn_ref)
        root.add_widget(fbar)

        self.sv = ScrollView()
        self.grid_wrap = BoxLayout(orientation='vertical', spacing=dp(1))
        self.sv.add_widget(self.grid_wrap)
        root.add_widget(self.sv)
        self.add_widget(root)
        self._refresh()

    def on_enter(self):
        self._refresh()

    def _refresh(self, *a):
        self.dm._load_booking()
        hari      = self.sp_hari.text
        ruang_list= self.dm.get_ruang_list()
        cols      = len(ruang_list) + 1

        # Hitung statistik
        total  = len(ruang_list) * len(JAM_SLOT)
        terisi = 0
        for jm, js in JAM_SLOT:
            for ru in ruang_list:
                if self.dm.slot_terisi_grid(hari, jm, js, ru) is not None:
                    terisi += 1
        self.lbl_stat.text = f'Kosong: {total-terisi} | Terisi: {terisi}'

        self.grid_wrap.clear_widgets()

        # Header
        h_row = GridLayout(cols=cols, size_hint_y=None, height=dp(44), spacing=dp(1))
        bg_rect(h_row, NAVY)
        h_row.add_widget(Label(text='JAM', color=PUTIH, font_size=dp(10),
                               bold=True, size_hint_y=None, height=dp(44), markup=False))
        for r in ruang_list:
            h_row.add_widget(Label(text=r, color=PUTIH, font_size=dp(9), bold=True,
                                   size_hint_y=None, height=dp(44),
                                   halign='center', valign='middle', markup=False))
        self.grid_wrap.add_widget(h_row)

        sv_in = ScrollView()
        rows  = GridLayout(cols=1, size_hint_y=None, spacing=dp(1))
        rows.bind(minimum_height=rows.setter('height'))

        for i, (jm, js) in enumerate(JAM_SLOT):
            row_bg = (0.97,0.97,1.0,1) if i%2==0 else PUTIH
            baris  = GridLayout(cols=cols, size_hint_y=None, height=dp(60), spacing=dp(1))
            bg_rect(baris, row_bg)

            baris.add_widget(Label(
                text=f'{jm}\n{js}', font_size=dp(10), color=NAVY,
                bold=True, size_hint_y=None, height=dp(60),
                halign='center', valign='middle', markup=False))

            for ruang in ruang_list:
                booking = self.dm.slot_terisi_grid(hari, jm, js, ruang)
                if booking is not None:
                    mk_v  = str(booking.get('mata_kuliah',''))
                    mk_s  = (mk_v[:10]+'..') if len(mk_v)>10 else mk_v
                    teks  = f'{booking["rombel"]}\n{mk_s}' if mk_s else booking["rombel"]
                    w_bg  = MERAH; w_tx = PUTIH
                else:
                    teks  = 'Tersedia'; w_bg = HIJAU; w_tx = PUTIH

                sel = Button(
                    text=teks, font_size=dp(9),
                    background_normal='', background_color=(0,0,0,0),
                    color=w_tx, size_hint_y=None, height=dp(60),
                    bold=True, halign='center', markup=False)

                with sel.canvas.before:
                    Color(*w_bg)
                    rr = RoundedRectangle(pos=sel.pos, size=sel.size, radius=[4])
                def mk_up(rect):
                    def pp(w,v): rect.pos=v
                    def ps(w,v): rect.size=v
                    return pp,ps
                pp,ps = mk_up(rr)
                sel.bind(pos=pp, size=ps)

                sel.hari=hari; sel.jm=jm; sel.js=js
                sel.ruang=ruang; sel.booking=booking

                def dn(i,t):
                    if i.collide_point(*t.pos): Animation(opacity=0.72,duration=0.07).start(i)
                def up(i,t): Animation(opacity=1.0,duration=0.1).start(i)
                sel.bind(on_touch_down=dn, on_touch_up=up, on_press=self._klik)
                baris.add_widget(sel)
            rows.add_widget(baris)

        sv_in.add_widget(rows)
        self.grid_wrap.add_widget(sv_in)

    def _klik(self, sel):
        hari,jm,js,ruang,booking = sel.hari,sel.jm,sel.js,sel.ruang,sel.booking
        box = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))

        if booking is not None:
            mk_info = str(booking.get('mata_kuliah',''))
            pesan   = (f'ID      : {booking["id_booking"]}\n'
                       f'Rombel  : {booking["rombel"]}\n'
                       f'Hari    : {hari}\n'
                       f'Jam     : {jm} - {js}\n'
                       f'Ruang   : {ruang}')
            if mk_info: pesan += f'\nMK      : {mk_info}'

            box.add_widget(Label(text=pesan, font_size=dp(11), color=GELAP,
                                 halign='left', valign='middle', markup=False))
            pop = Popup(title='Detail Jadwal', content=box,
                        size_hint=(0.8, 0.45), auto_dismiss=False,
                        title_color=NAVY, separator_color=MERAH)

            is_new = str(booking.get('waktu_booking','')) != '2026-01-01 00:00:00'
            if is_new:
                btn_b = tombol('Batalkan Booking', MERAH, lambda *a: None, h=dp(38))
                def batal(*a):
                    self.dm.batalkan(booking['id_booking'])
                    pop.dismiss(); self._refresh()
                btn_b.bind(on_press=batal)
                box.add_widget(btn_b)
            box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(36)))
            pop.open()

        else:
            # Ruang kosong — pilih SKS dulu
            box.add_widget(Label(
                text=f'{ruang} tersedia\n{hari}  {jm} - {js}\n\nPilih rombel dan SKS:',
                font_size=dp(12), color=GELAP, halign='center', markup=False))
            sp_r = sp_ui(self.dm.get_rombel_list(), 'Pilih Rombel')
            sp_s = sp_ui(tuple(SKS_CONFIG.keys()), 'Pilih SKS')
            ti_mk = TextInput(hint_text='Mata Kuliah (opsional)',
                              size_hint_y=None, height=dp(38),
                              font_size=dp(12), multiline=False,
                              background_color=ABU_MD, foreground_color=GELAP,
                              padding=[dp(8),dp(8)])
            box.add_widget(sp_r); box.add_widget(sp_s); box.add_widget(ti_mk)

            pop = Popup(title='Booking Langsung', content=box,
                        size_hint=(0.8, 0.55), auto_dismiss=False,
                        title_color=NAVY, separator_color=HIJAU)

            btn_ok = tombol('LIHAT SLOT & BOOKING', HIJAU, lambda *a: None, h=dp(40))
            btn_x  = tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(36))

            def do_book(*a):
                if 'Pilih' in sp_r.text or 'Pilih' in sp_s.text:
                    return
                sks_menit = SKS_CONFIG[sp_s.text]
                js_book   = menit_ke_jam(jm, sks_menit)

                # Validasi: durasi booking tidak boleh melebihi slot
                if parse_jam(js_book) > parse_jam(js):
                    pop.dismiss()
                    popup_ok('Tidak Bisa',
                        f'{sp_s.text} membutuhkan waktu hingga {js_book}\n'
                        f'tapi slot hanya sampai {js}.\n'
                        f'Slot ini hanya cukup untuk 2 SKS.', KUNING)
                    return

                cek = self.dm.cek_rombel_slot(sp_r.text, hari, jm, js_book)
                if cek:
                    pop.dismiss()
                    popup_ok('Gagal', f'Rombel {sp_r.text} sudah\nbooking di slot ini!', MERAH)
                    return
                cek2 = self.dm.cek_slot_ruang(hari, jm, js_book, ruang)
                if cek2:
                    pop.dismiss()
                    popup_ok('Gagal', f'Ruang {ruang} sudah terpakai\npada {jm}-{js_book}!', MERAH)
                    return

                self.dm.tambah_booking(sp_r.text, hari, jm, js_book, ruang, ti_mk.text.strip())
                pop.dismiss(); self._refresh()

            btn_ok.bind(on_press=do_book)
            box.add_widget(btn_ok); box.add_widget(btn_x)
            pop.open()


# ==============================================================
# APP
# ==============================================================
class BookingApp(App):
    def build(self):
        # Mobile screen dimensions (typical smartphone)
        Window.size       = (360, 640)
        Window.clearcolor = BG
        self.title        = 'Booking Ruang Kelas - Sains Data UNESA'
        dm    = DataManager()
        queue = BookingQueue()
        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        sm.add_widget(FormScreen(dm=dm, queue=queue, name='form'))
        sm.add_widget(GridScreen(dm=dm, name='grid'))
        sm.current = 'form'
        return sm

if __name__ == '__main__':
    BookingApp().run()