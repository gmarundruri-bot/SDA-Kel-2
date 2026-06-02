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
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.uix.image import Image 

import pandas as pd
from collections import deque
from datetime import datetime, time
import uuid
import shutil
import threading
from functools import partial
import weakref

# ── WARNA ──────────────────────────────────────────────────
NAVY     = (0.05, 0.10, 0.28, 1)
NAVY_MED = (0.08, 0.14, 0.38, 1)
UNGU     = (0.42, 0.18, 0.78, 1)
UNGU_MUD = (0.42, 0.18, 0.78, 0.12)
HIJAU    = (0.08, 0.72, 0.44, 1)
MERAH    = (0.90, 0.22, 0.22, 1)
KUNING   = (0.95, 0.70, 0.00, 1)
BG       = (0.95, 0.95, 0.98, 1)
PUTIH    = (1.00, 1.00, 1.00, 1)
GELAP    = (0.10, 0.10, 0.18, 1)
ABU      = (0.60, 0.62, 0.68, 1)
ABU_MD   = (0.95, 0.95, 0.97, 1)
ORANGE   = (1.00, 0.55, 0.00, 1)
BIRU     = (0.20, 0.60, 0.86, 1)

# ── KONSTANTA ──────────────────────────────────────────────
HARI_LIST = ["Senin", "Selasa", "Rabu", "Kamis"]
JAM_OPERASIONAL_MULAI = 7  # 07:00
JAM_OPERASIONAL_SELESAI = 17  # 17:00

SKS_CONFIG = {
    "2 SKS (100 menit)": 100,
    "3 SKS (150 menit)": 150,
}

DURASI_CONFIG = {
    "50 Menit (1 SKS)": 50,
    "100 Menit (2 SKS)": 100,
    "150 Menit (3 SKS)": 150,
}

# Grid per 50 menit (1 SKS), 07:00 - 17:00
def buat_slot_grid():
    slots = []
    start = JAM_OPERASIONAL_MULAI * 60  # 07:00 dalam menit
    end   = JAM_OPERASIONAL_SELESAI * 60 # 17:00
    while start + 50 <= end:
        jm = f"{start//60:02d}:{start%60:02d}"
        js = f"{(start+50)//60:02d}:{(start+50)%60:02d}"
        slots.append((jm, js))
        start += 50
    return slots

JAM_SLOT_GRID = buat_slot_grid()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_RUANG   = os.path.join(BASE_DIR, "data_ruang.csv")
FILE_ROMBEL  = os.path.join(BASE_DIR, "data_rombel.csv")
FILE_BOOKING = os.path.join(BASE_DIR, "data_booking.csv")
FILE_BACKUP  = os.path.join(BASE_DIR, "data_booking_backup.csv")

# Assets 
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

ICON_FORM = os.path.join(ASSETS_DIR, "Form Booking.png")
ICON_GRID = os.path.join(ASSETS_DIR, "Grid Jadwal.png")
ICON_INFO = os.path.join(ASSETS_DIR, "Informasi.png")
ICON_RIWAYAT = os.path.join(ASSETS_DIR, "Riwayat.png")

# Buat folder assets jika belum ada
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)
    print(f"Folder {ASSETS_DIR} telah dibuat.")
    print("Silakan tambahkan file icon ke folder assets:")
    print("  - Form Booking.png")
    print("  - Grid Jadwal.png")
    print("  - Informasi.png")
    print("  - Riwayat.png")

# Cek dan buat file CSV contoh jika belum ada
def buat_file_contoh():
    try:
        # Buat file data_ruang.csv jika belum ada
        if not os.path.exists(FILE_RUANG):
            df_ruang = pd.DataFrame({
                'kode_ruang': ['Ruang 101', 'Ruang 102', 'Ruang 103', 'Ruang 104', 
                              'Ruang 105', 'Ruang 106', 'Ruang 107', 'Ruang 108']
            })
            df_ruang.to_csv(FILE_RUANG, index=False)
            print(f"File {FILE_RUANG} telah dibuat.")
        
        # Buat file data_rombel.csv jika belum ada
        if not os.path.exists(FILE_ROMBEL):
            df_rombel = pd.DataFrame({
                'kode_rombel': ['INT 24', '2024 A', '2024 B', '2024 C', '2024 D', '2024 E',
                               'INT 25', '2025 A', '2025 B', '2025 C', '2025 D', '2025 E', 
                               '2025 F', '2025 G']
            })
            df_rombel.to_csv(FILE_ROMBEL, index=False)
            print(f"File {FILE_ROMBEL} telah dibuat.")
        
        # Buat file data_booking.csv jika belum ada
        if not os.path.exists(FILE_BOOKING):
            df_booking = pd.DataFrame(columns=[
                'id_booking', 'rombel', 'hari', 'jam_mulai', 'jam_selesai', 'ruang',
                'mata_kuliah', 'tipe', 'status', 'waktu_booking', 'durasi_penggunaan',
                'kelas_selesai', 'waktu_selesai'
            ])
            df_booking.to_csv(FILE_BOOKING, index=False)
            print(f"File {FILE_BOOKING} telah dibuat.")
    except Exception as e:
        print(f"Error creating example files: {e}")

# Panggil fungsi untuk membuat file contoh
buat_file_contoh()

# ==============================================================
# HELPER WAKTU 
# ==============================================================
def parse_jam(s):
    """Parse waktu string ke time object dengan error handling yang lebih baik"""
    try:
        if not s or not isinstance(s, str):
            return time(0, 0)
        h, m = map(int, s.split(':'))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return time(h, m)
        return time(0, 0)
    except (ValueError, AttributeError):
        return time(0, 0)

def menit_ke_jam(jam_str, tambah):
    """Tambahkan menit ke jam string"""
    try:
        h, m = map(int, jam_str.split(':'))
        total = h * 60 + m + tambah
        jam_baru = total // 60
        menit_baru = total % 60
        if jam_baru > 23:
            return None
        return f"{jam_baru:02d}:{menit_baru:02d}"
    except (ValueError, AttributeError):
        return None

def overlap(jm1, js1, jm2, js2):
    """Cek apakah dua slot waktu overlap dengan benar"""
    try:
        t1_mulai = parse_jam(jm1)
        t1_selesai = parse_jam(js1)
        t2_mulai = parse_jam(jm2)
        t2_selesai = parse_jam(js2)
        
        if t1_mulai == time(0,0) or t1_selesai == time(0,0) or \
           t2_mulai == time(0,0) or t2_selesai == time(0,0):
            return False
            
        return not (t1_mulai >= t2_selesai or t2_mulai >= t1_selesai)
    except Exception:
        return False

def validasi_jam_operasional(jam_str):
    """Validasi apakah jam dalam range operasional"""
    try:
        jam_obj = parse_jam(jam_str)
        if jam_obj == time(0, 0):
            return False
        if jam_obj.minute not in [0, 30]:
            return False
        batas_mulai = time(JAM_OPERASIONAL_MULAI, 0)
        batas_akhir = time(JAM_OPERASIONAL_SELESAI, 0)
        return batas_mulai <= jam_obj <= batas_akhir
    except:
        return False

def hitung_durasi_menit(jam_mulai, jam_selesai):
    """Hitung durasi dalam menit antara dua waktu"""
    try:
        mulai = parse_jam(jam_mulai)
        selesai = parse_jam(jam_selesai)
        return (selesai.hour - mulai.hour) * 60 + (selesai.minute - mulai.minute)
    except:
        return 0

def cari_slot_tersedia(hari, jam_mulai_req, durasi, booking_df, ruang_sorted):
    """Cari slot tersedia untuk request booking"""
    hasil = []
    js = menit_ke_jam(jam_mulai_req, durasi)
    
    if js is None:
        return hasil
    
    if parse_jam(js) > time(JAM_OPERASIONAL_SELESAI, 0):
        return hasil
    
    for ruang in ruang_sorted:
        terpakai = False
        if booking_df is not None and not booking_df.empty:
            aktif = booking_df[
                (booking_df['hari'] == hari) &
                (booking_df['ruang'] == ruang) &
                (booking_df['status'] == 'aktif')
            ]
            for _, row in aktif.iterrows():
                if overlap(jam_mulai_req, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    terpakai = True
                    break
        if not terpakai:
            hasil.append({'jam_mulai': jam_mulai_req, 'jam_selesai': js, 'ruang': ruang})
    return hasil

# ==============================================================
# QUEUE
# ==============================================================
class BookingQueue:
    def __init__(self):
        self.antrian = deque()
        self.lock = threading.Lock()
    
    def enqueue(self, item): 
        with self.lock:
            self.antrian.append(item)
    
    def dequeue(self): 
        with self.lock:
            return self.antrian.popleft() if not self.is_empty() else None
    
    def is_empty(self): 
        with self.lock:
            return len(self.antrian) == 0
    
    def size(self): 
        with self.lock:
            return len(self.antrian)

# ==============================================================
# DATA MANAGER 
# ==============================================================
class DataManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.ruang_df = None
        self.rombel_df = None
        self.booking_df = None
        self.ruang_sorted = []
        self._load_all_data()
        
    def _load_all_data(self):
        """Load semua data dengan error handling"""
        with self.lock:
            try:
                # Load data ruang
                if os.path.exists(FILE_RUANG):
                    try:
                        self.ruang_df = pd.read_csv(FILE_RUANG)
                        if self.ruang_df.empty or 'kode_ruang' not in self.ruang_df.columns:
                            raise ValueError("Invalid structure")
                        self.ruang_sorted = sorted(self.ruang_df['kode_ruang'].tolist())
                    except Exception as e:
                        print(f"Error loading ruang: {e}")
                        self.ruang_df = pd.DataFrame({'kode_ruang': []})
                        self.ruang_sorted = []
                else:
                    self.ruang_df = pd.DataFrame({'kode_ruang': []})
                    self.ruang_sorted = []
                
                # Load data rombel
                if os.path.exists(FILE_ROMBEL):
                    try:
                        self.rombel_df = pd.read_csv(FILE_ROMBEL)
                        if self.rombel_df.empty or 'kode_rombel' not in self.rombel_df.columns:
                            raise ValueError("Invalid structure")
                    except Exception as e:
                        print(f"Error loading rombel: {e}")
                        self.rombel_df = pd.DataFrame({'kode_rombel': []})
                else:
                    self.rombel_df = pd.DataFrame({'kode_rombel': []})
                
                # Load data booking
                self._load_booking()
                
                # Buat backup jika belum ada
                if not os.path.exists(FILE_BACKUP) and os.path.exists(FILE_BOOKING):
                    shutil.copy(FILE_BOOKING, FILE_BACKUP)
                    
            except Exception as e:
                print(f"Error loading data: {e}")
                self.ruang_df = pd.DataFrame({'kode_ruang': []})
                self.rombel_df = pd.DataFrame({'kode_rombel': []})
                self.ruang_sorted = []
                self.booking_df = self._create_empty_booking_df()

    def _create_empty_booking_df(self):
        """Buat dataframe booking kosong dengan struktur yang benar"""
        return pd.DataFrame(columns=[
            'id_booking', 'rombel', 'hari', 'jam_mulai', 'jam_selesai', 'ruang',
            'mata_kuliah', 'tipe', 'status', 'waktu_booking', 'durasi_penggunaan',
            'kelas_selesai', 'waktu_selesai'
        ])

    def _load_booking(self):
        """Load data booking dengan error handling yang lebih baik"""
        with self.lock:
            try:
                if os.path.exists(FILE_BOOKING):
                    df = pd.read_csv(FILE_BOOKING)
                    if not df.empty and 'id_booking' in df.columns:
                        defaults = {
                            'mata_kuliah': '', 
                            'durasi_penggunaan': 0,
                            'kelas_selesai': 'Belum', 
                            'waktu_selesai': '',
                            'tipe': 'booking'
                        }
                        for col, default in defaults.items():
                            if col not in df.columns:
                                df[col] = default
                        
                        if 'tipe' in df.columns:
                            df['tipe'] = df['tipe'].fillna('booking')
                            df['tipe'] = df['tipe'].apply(lambda x: 'booking' if x not in ['tetap', 'booking'] else x)
                        
                        if 'status' not in df.columns:
                            df['status'] = 'aktif'
                        else:
                            df['status'] = df['status'].fillna('aktif')
                        
                        self.booking_df = df
                    else:
                        self.booking_df = self._create_empty_booking_df()
                else:
                    self.booking_df = self._create_empty_booking_df()
            except Exception as e:
                print(f"Error loading booking: {e}")
                self.booking_df = self._create_empty_booking_df()

    def simpan(self): 
        """Simpan data booking ke file dengan thread safety"""
        with self.lock:
            try:
                self.booking_df.to_csv(FILE_BOOKING, index=False)
            except Exception as e:
                print(f"Error saving booking: {e}")

    def tambah_booking(self, rombel, hari, jm, js, ruang, mk='', durasi=0):
        """Tambah booking baru dengan validasi"""
        with self.lock:
            if self.cek_rombel_slot(rombel, hari, jm, js):
                raise ValueError(f"Rombel {rombel} sudah memiliki jadwal di slot ini")
            
            if self.cek_slot_ruang(hari, jm, js, ruang):
                raise ValueError(f"Ruang {ruang} sudah terisi di slot ini")
            
            new_id = str(uuid.uuid4())[:8].upper()
            new_row = {
                'id_booking': new_id,
                'rombel': rombel, 
                'hari': hari, 
                'jam_mulai': jm, 
                'jam_selesai': js,
                'ruang': ruang, 
                'mata_kuliah': mk, 
                'tipe': 'booking',
                'status': 'aktif',
                'waktu_booking': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'durasi_penggunaan': durasi, 
                'kelas_selesai': 'Belum', 
                'waktu_selesai': ''
            }
            
            self.booking_df.loc[len(self.booking_df)] = new_row
            self.simpan() 
            return new_id

    def batalkan(self, id_booking):
        """Batalkan booking"""
        with self.lock:
            mask = self.booking_df['id_booking'] == id_booking
            if mask.any():
                self.booking_df.loc[mask, 'status'] = 'batal'
                self.simpan()

    def kelas_selesai(self, id_booking):
        """Tandai kelas sebagai selesai"""
        with self.lock:
            mask = self.booking_df['id_booking'] == id_booking
            if mask.any():
                self.booking_df.loc[mask, 'kelas_selesai'] = 'Selesai'
                self.booking_df.loc[mask, 'waktu_selesai'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.simpan()

    def reset_jadwal(self):
        """Reset ke jadwal awal"""
        with self.lock:
            if os.path.exists(FILE_BACKUP):
                shutil.copy(FILE_BACKUP, FILE_BOOKING)
                self._load_booking() 
                return True
            return False

    def cek_slot_ruang(self, hari, jm, js, ruang):
        """Cek apakah slot ruang sudah terisi"""
        if self.booking_df is None or self.booking_df.empty: 
            return None
        with self.lock:
            aktif = self.booking_df[(self.booking_df['hari'] == hari) &
                                    (self.booking_df['ruang'] == ruang) &
                                    (self.booking_df['status'] == 'aktif')]
            for _, row in aktif.iterrows():
                if overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    return row
            return None

    def cek_rombel_slot(self, rombel, hari, jm, js):
        """Cek apakah rombel sudah memiliki jadwal di slot tersebut"""
        if self.booking_df is None or self.booking_df.empty: 
            return None
        with self.lock:
            aktif = self.booking_df[(self.booking_df['rombel'] == rombel) &
                                    (self.booking_df['hari'] == hari) &
                                    (self.booking_df['status'] == 'aktif')]
            for _, row in aktif.iterrows():
                if overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    return row
            return None

    def get_rombel_list(self):
        """Dapatkan daftar rombel terurut"""
        with self.lock:
            if self.rombel_df is None or self.rombel_df.empty:
                return []
            urutan = ["INT 24","2024 A","2024 B","2024 C","2024 D","2024 E",
                      "INT 25","2025 A","2025 B","2025 C","2025 D","2025 E","2025 F","2025 G"]
            semua = self.rombel_df['kode_rombel'].tolist()
            return [r for r in urutan if r in semua]

    def get_ruang_list(self): 
        """Dapatkan daftar ruang"""
        with self.lock:
            if self.ruang_df is not None and not self.ruang_df.empty:
                return self.ruang_df['kode_ruang'].tolist()
            return []

    def get_statistik(self):
        """Dapatkan statistik penggunaan"""
        with self.lock:
            if self.booking_df is None or self.booking_df.empty:
                return {
                    'total_booking': 0,
                    'ruang_terpakai': 0,
                    'rombel_aktif': 0,
                    'total_batal': 0,
                    'total_selesai': 0,
                }
            
            aktif = self.booking_df[self.booking_df['status'] == 'aktif']
            return {
                'total_booking': len(aktif),
                'ruang_terpakai': len(set(aktif['ruang'])) if not aktif.empty else 0,
                'rombel_aktif': len(set(aktif['rombel'])) if not aktif.empty else 0,
                'total_batal': len(self.booking_df[self.booking_df['status'] == 'batal']),
                'total_selesai': len(self.booking_df[self.booking_df['kelas_selesai'] == 'Selesai']),
            }

    def riwayat_booking(self, page=0, items_per_page=20, filter_status='Semua'):
        """Dapatkan riwayat booking dengan pagination"""
        with self.lock:
            if self.booking_df is None or self.booking_df.empty: 
                return pd.DataFrame()
            
            df = self.booking_df[self.booking_df['tipe'] == 'booking'].sort_values('waktu_booking', ascending=False)
            
            if filter_status == 'aktif':
                df = df[df['status'] == 'aktif']
            elif filter_status == 'batal':
                df = df[df['status'] == 'batal']
            elif filter_status == 'Selesai':
                df = df[df['kelas_selesai'] == 'Selesai']
            
            start = page * items_per_page
            end = start + items_per_page
            return df.iloc[start:end] if not df.empty else df

# ==============================================================
# HELPER UI
# ==============================================================
def bg_rect(w, c):
    with w.canvas.before:
        Color(*c)
        r = Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda a, v: setattr(r, 'pos', v), 
           size=lambda a, v: setattr(r, 'size', v))

def bg_round(w, c, rad=10):
    with w.canvas.before:
        Color(*c)
        r = RoundedRectangle(pos=w.pos, size=w.size, radius=[rad])
    w.bind(pos=lambda a, v: setattr(r, 'pos', v), 
           size=lambda a, v: setattr(r, 'size', v))

def tombol(text, warna, cb, h=dp(44), r=10, fs=dp(14)):
    b = Button(text=text, size_hint_y=None, height=h,
               background_normal='', background_color=(0,0,0,0),
               color=PUTIH, font_size=fs, bold=True, markup=False)
    bg_round(b, warna, r)
    b.bind(on_press=cb)
    def dn(i, t):
        if i.collide_point(*t.pos): 
            Animation(opacity=0.72, duration=0.07).start(i)
    def up(i, t): 
        Animation(opacity=1.0, duration=0.1).start(i)
    b.bind(on_touch_down=dn, on_touch_up=up)
    return b

def lbl_field(text):
    l = Label(text=text, font_size=dp(13), bold=True, color=UNGU,
              size_hint_y=None, height=dp(26), halign='left', valign='bottom', markup=False)
    l.bind(size=lambda w, v: setattr(w, 'text_size', v))
    return l

def sp_ui(values, default='Pilih...'):
    if not values:
        values = ['Tidak ada data']
    return Spinner(text=default, values=list(values),
                   size_hint_y=None, height=dp(44),
                   background_normal='', background_color=ABU_MD,
                   color=GELAP, font_size=dp(14))

def notif(pesan, warna=None, durasi=2.2):
    if warna is None: 
        warna = HIJAU
    icon = '✅' if warna == HIJAU else ('❌' if warna == MERAH else '⚠️')

    outer = BoxLayout(padding=dp(3))
    bg_round(outer, warna, 14)

    inner = BoxLayout(padding=[dp(16), dp(12)], spacing=dp(10))
    bg_round(inner, PUTIH, 12)

    lbl = Label(text=f'{icon}  {pesan}', font_size=dp(14),
                color=GELAP, bold=True, halign='center', valign='middle', markup=False)
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
    inner.add_widget(lbl)
    outer.add_widget(inner)

    pop = Popup(title='', content=outer,
                size_hint=(0.42, 0.13),
                auto_dismiss=True,
                background_color=(0, 0, 0, 0.35),
                separator_height=0, title_size=0)
    pop.open()
    Clock.schedule_once(lambda *a: pop.dismiss(), durasi)

def popup_ok(judul, pesan, warna=None):
    if warna is None: 
        warna = UNGU
    box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))
    bg_round(box, PUTIH, 12)
    lbl = Label(text=pesan, font_size=dp(13), color=GELAP,
                halign='left', valign='top', markup=False)
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
    box.add_widget(lbl)
    pop = Popup(title=judul, content=box, size_hint=(0.52, 0.62),
                auto_dismiss=False, title_color=PUTIH,
                title_size=dp(15), separator_color=warna,
                background_color=(0, 0, 0, 0.45))
    box.add_widget(tombol('OK', warna, lambda *a: pop.dismiss(), h=dp(42)))
    pop.open()
    return pop

def popup_konfirmasi(judul, pesan, cb_ya, warna_ya=MERAH):
    box = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(12))
    bg_round(box, PUTIH, 12)
    lbl = Label(text=pesan, font_size=dp(14), color=GELAP,
                halign='center', valign='middle', markup=False)
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
    box.add_widget(lbl)
    baris = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
    pop = Popup(title=judul, content=box, size_hint=(0.44, 0.36),
                auto_dismiss=False, title_color=PUTIH,
                title_size=dp(15), separator_color=warna_ya,
                background_color=(0, 0, 0, 0.45))
    def ya(*a): 
        pop.dismiss()
        cb_ya()
    baris.add_widget(tombol('Ya, Lanjutkan', warna_ya, ya, h=dp(42)))
    baris.add_widget(tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(42)))
    box.add_widget(baris)
    pop.open()

# ==============================================================
# POPUP PILIH SLOT 
# ==============================================================
def popup_pilih_slot(dm, rombel, hari, jam_mulai, durasi, mk, on_booked):
    slots = cari_slot_tersedia(hari, jam_mulai, durasi, dm.booking_df, dm.ruang_sorted)
    box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

    if not slots:
        box.add_widget(Label(
            text=f'Tidak ada slot kosong untuk\njam {jam_mulai} durasi {durasi} menit\npada {hari}.',
            font_size=dp(14), color=GELAP, halign='center', markup=False))
        pop = Popup(title='Slot Tidak Tersedia', content=box,
                    size_hint=(0.44, 0.32), auto_dismiss=False,
                    title_color=NAVY, separator_color=MERAH,
                    background_color=(0, 0, 0, 0.45))
        box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(40)))
        pop.open()
        return

    js_akhir = menit_ke_jam(jam_mulai, durasi)
    if js_akhir is None:
        notif('Durasi melebihi batas operasional!', MERAH)
        return
        
    box.add_widget(Label(
        text=f'Slot tersedia: {hari}  {jam_mulai} - {js_akhir}  ({durasi} menit)\nPilih ruang:',
        font_size=dp(13), color=NAVY, bold=True,
        size_hint_y=None, height=dp(40), halign='center', markup=False))

    sv = ScrollView(size_hint=(1, 1))
    grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(8), padding=[0, dp(4)])
    grid.bind(minimum_height=grid.setter('height'))

    pop = Popup(title=f'Pilih Ruang - {jam_mulai} s/d {js_akhir}',
                content=box, size_hint=(0.50, 0.65),
                auto_dismiss=False, title_color=NAVY,
                title_size=dp(14), separator_color=UNGU,
                background_color=(0, 0, 0, 0.45))

    for slot in slots:
        jm, js, ru = slot['jam_mulai'], slot['jam_selesai'], slot['ruang']
        btn_s = Button(text=f'{ru}\n{jm}-{js}',
                       size_hint_y=None, height=dp(56),
                       background_normal='', background_color=(0, 0, 0, 0),
                       color=PUTIH, font_size=dp(12), bold=True,
                       markup=False, halign='center')
        bg_round(btn_s, HIJAU, 8)
        
        dm_ref = weakref.ref(dm)
        
        def buat_cb(j_m, j_s, r_u):
            def cb(*a):
                dm_local = dm_ref()
                if dm_local is None:
                    return
                try:
                    cek = dm_local.cek_rombel_slot(rombel, hari, j_m, j_s)
                    if cek is not None:
                        pop.dismiss()
                        notif(f'Rombel {rombel} sudah ada jadwal di slot ini!', MERAH)
                        return
                    id_b = dm_local.tambah_booking(rombel, hari, j_m, j_s, r_u, mk, durasi)
                    pop.dismiss()
                    notif(f'Booking berhasil!  {r_u}  {j_m}-{j_s}', HIJAU)
                    if on_booked:
                        on_booked()
                except ValueError as e:
                    notif(str(e), MERAH)
                except Exception as e:
                    notif(f'Error: {str(e)}', MERAH)
            return cb
        
        btn_s.bind(on_press=buat_cb(jm, js, ru))
        grid.add_widget(btn_s)

    sv.add_widget(grid)
    box.add_widget(sv)
    box.add_widget(tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(40)))
    pop.open()

# ==============================================================
# NAV BAR HELPER
# ==============================================================
def topbar(root_widget, title, manager_ref, tombol_list):
    top = BoxLayout(
        size_hint_y=None,
        height=dp(56),
        padding=[dp(20), dp(10)],
        spacing=dp(10)
    )
    bg_rect(top, NAVY)

    top.add_widget(
        Label(
            text=title,
            color=PUTIH,
            font_size=dp(16),
            bold=True,
            halign='left',
            valign='middle'
        )
    )

    def pindah_screen(screen_name):
        app = App.get_running_app()
        if app and app.root:
            app.root.current = screen_name

    for teks, warna, screen in tombol_list:
        b = tombol(
            teks,
            warna,
            lambda *a, s=screen: pindah_screen(s),
            h=dp(34),
            r=7,
            fs=dp(12)
        )
        b.size_hint = (None, None)
        b.width = dp(100)
        top.add_widget(b)

    root_widget.add_widget(top)

# ==============================================================
# SCREEN 0: HOME 
# ==============================================================
class HomeScreen(Screen):
    def __init__(self, dm, **kw):
        super().__init__(**kw)
        self.dm = dm
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)

        top = BoxLayout(size_hint_y=None, height=dp(70),
                        padding=[dp(20), dp(12)], spacing=dp(10))
        bg_rect(top, NAVY)
        top.add_widget(Label(
            text='Sistem Informasi Booking Ruang Kelas\nUniversitas Negeri Surabaya  -  Prodi Sains Data',
            color=PUTIH, font_size=dp(15), bold=True,
            halign='left', valign='middle', markup=False))
        root.add_widget(top)

        main = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(18))

        # Welcome card
        wc = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(130),
                       padding=dp(20), spacing=dp(8))
        bg_round(wc, PUTIH, 14)
        wc.add_widget(Label(text='Selamat Datang!', font_size=dp(22), bold=True,
                            color=NAVY, halign='center', size_hint_y=None, height=dp(36),
                            markup=False))
        wc.add_widget(Label(
            text='Sistem Booking Ruang Kelas untuk Prodi Sains Data\nFakultas Matematika dan Ilmu Pengetahuan Alam - UNESA',
            font_size=dp(13), color=ABU, halign='center',
            size_hint_y=None, height=dp(50), markup=False))
        main.add_widget(wc)

        # Menu cards - MENGGUNAKAN GAMBAR PNG (jika ada) atau EMOJI (fallback)
        menu_grid = GridLayout(cols=4, spacing=dp(16), size_hint_y=None, height=dp(240))
        
        # Data menu dengan icon: (icon_path, emoji, judul, deskripsi, warna, screen)
        menus = [
            (ICON_FORM, '📝', 'Form Booking', 'Booking ruang kelas\nuntuk perkuliahan', UNGU, 'form'),
            (ICON_GRID, '📊', 'Grid Jadwal', 'Lihat jadwal ruang\nsecara visual per jam', HIJAU, 'grid'),
            (ICON_RIWAYAT, '📜', 'Riwayat', 'Lihat semua riwayat\npeminjaman ruang', BIRU, 'history'),
            (ICON_INFO, 'ℹ️', 'Informasi', 'Statistik dan info\npenggunaan ruangan', ORANGE, 'info_popup'),
        ]
        
        for icon_path, emoji, judul, desc, warna, screen in menus:
            card = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))
            bg_round(card, PUTIH, 14)
            
            # Cek apakah file icon PNG ada
            if os.path.exists(icon_path):
                # Tampilkan gambar PNG
                img = Image(source=icon_path, size_hint_y=None, height=dp(70), allow_stretch=True)
                card.add_widget(img)
            else:
                # Tampilkan emoji sebagai fallback
                lbl_icon = Label(text=emoji, font_size=dp(50), 
                               size_hint_y=None, height=dp(70),
                               halign='center', valign='middle')
                card.add_widget(lbl_icon)
            
            card.add_widget(Label(text=judul, font_size=dp(15), bold=True,
                                  color=NAVY, halign='center',
                                  size_hint_y=None, height=dp(28), markup=False))
            card.add_widget(Label(text=desc, font_size=dp(11), color=ABU,
                                  halign='center', size_hint_y=None, height=dp(36),
                                  markup=False))
            
            if screen == 'info_popup':
                b = tombol('Lihat Info', warna, self._show_info, h=dp(36), r=8, fs=dp(12))
            else:
                b = tombol('Buka', warna,
                           lambda *a, s=screen: setattr(self.manager, 'current', s),
                           h=dp(36), r=8, fs=dp(12))
            card.add_widget(b)
            menu_grid.add_widget(card)
        
        main.add_widget(menu_grid)

        # Info operasional
        info = BoxLayout(size_hint_y=None, height=dp(72), padding=dp(16), spacing=dp(6))
        bg_round(info, NAVY_MED, 10)
        info.add_widget(Label(
            text=f'Jam Operasional: Senin - Kamis  |  {JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI:02d}:00\n'
                 'Jumat: Pembelajaran Online  (booking tidak tersedia)\n'
                 'Grid menampilkan per 1 SKS (50 menit)',
            font_size=dp(12), color=PUTIH, halign='center', markup=False))
        main.add_widget(info)

        root.add_widget(main)
        self.add_widget(root)

    def _show_info(self, *a):
        stat = self.dm.get_statistik()
        pesan = (
            f'Statistik Penggunaan Ruangan\n\n'
            f'Total Booking Aktif   : {stat["total_booking"]}\n'
            f'Total Booking Batal   : {stat["total_batal"]}\n'
            f'Total Kelas Selesai   : {stat["total_selesai"]}\n'
            f'Rombel Aktif               : {stat["rombel_aktif"]}\n\n'

            f'Informasi Umum :\n'
            f'1 SKS = 50 menit\n'
            f'Grid jadwal per 50 menit ({JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI:02d}:00)\n'
            f'Booking bisa durasi fleksibel per sks\n'
            f'Pembatalan via halaman Riwayat atau Grid\n\n'
        )
        popup_ok('Informasi Sistem', pesan, UNGU)

# ==============================================================
# SCREEN 1: FORM BOOKING
# ==============================================================
class FormScreen(Screen):
    def __init__(self, dm, queue, **kw):
        super().__init__(**kw)
        self.dm = dm
        self.queue = queue
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)
        topbar(root, 'Form Booking Ruang', self.manager,
               [('Home', UNGU, 'home'), ('Grid', HIJAU, 'grid'), ('Riwayat', BIRU, 'history')])

        sv = ScrollView()
        body = BoxLayout(orientation='vertical', padding=dp(20),
                         spacing=dp(14), size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))

        body.add_widget(Label(text='Peminjaman Ruang Kelas', font_size=dp(20), bold=True,
                              color=NAVY, size_hint_y=None, height=dp(36),
                              halign='left', markup=False))
        body.add_widget(Label(
            text=f'Senin - Kamis {JAM_OPERASIONAL_MULAI:02d}:00-{JAM_OPERASIONAL_SELESAI:02d}:00  |  Jumat: pembelajaran online (tidak tersedia)',
            font_size=dp(12), color=ABU, size_hint_y=None, height=dp(20),
            halign='left', markup=False))

        card = BoxLayout(orientation='vertical', size_hint_y=None,
                         padding=dp(20), spacing=dp(12))
        card.bind(minimum_height=card.setter('height'))
        bg_round(card, PUTIH, 14)

        card.add_widget(lbl_field('Rombel / Kelas'))
        self.sp_rombel = sp_ui(self.dm.get_rombel_list(), 'Pilih Rombel')
        card.add_widget(self.sp_rombel)

        card.add_widget(lbl_field('Hari'))
        self.sp_hari = sp_ui(tuple(HARI_LIST), 'Pilih Hari')
        card.add_widget(self.sp_hari)

        card.add_widget(lbl_field(f'Jam Mulai  (format HH:MM, contoh: 08:00)  |  Range: {JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI-1:02d}:00 (menit 00 atau 30)'))
        self.ti_jam = TextInput(hint_text='07:00 / 09:30 / 13:00',
                                size_hint_y=None, height=dp(44), font_size=dp(14),
                                multiline=False, foreground_color=GELAP,
                                background_color=ABU_MD, cursor_color=UNGU,
                                padding=[dp(12), dp(12)])
        card.add_widget(self.ti_jam)

        card.add_widget(lbl_field('Durasi Penggunaan'))
        self.sp_durasi = sp_ui(tuple(DURASI_CONFIG.keys()), 'Pilih Durasi')
        card.add_widget(self.sp_durasi)

        card.add_widget(lbl_field('Mata Kuliah (opsional)'))
        self.ti_mk = TextInput(hint_text='Contoh: Struktur Data Dan Algoritma',
                               size_hint_y=None, height=dp(44), font_size=dp(14),
                               multiline=False, foreground_color=GELAP,
                               background_color=ABU_MD, cursor_color=UNGU,
                               padding=[dp(12), dp(12)])
        card.add_widget(self.ti_mk)

        info = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(12), dp(8)])
        bg_round(info, UNGU_MUD, 8)
        info.add_widget(Label(
            text=f'Sistem mencari ruang kosong. Durasi fleksibel 30-150 menit. '
                 f'Jam mulai antara {JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI-1:02d}:00.',
            font_size=dp(11.5), color=UNGU, halign='left', markup=False))
        card.add_widget(info)

        self.btn_cari = tombol('CARI SLOT KOSONG', UNGU, self._cari, h=dp(50))
        card.add_widget(self.btn_cari)
        self.lbl_q = Label(text='', font_size=dp(12), color=UNGU,
                           size_hint_y=None, height=dp(22), halign='center', markup=False)
        card.add_widget(self.lbl_q)
        body.add_widget(card)
        sv.add_widget(body)
        root.add_widget(sv)
        self.add_widget(root)

    def _cari(self, *a):
        r = self.sp_rombel.text
        h = self.sp_hari.text
        d = self.sp_durasi.text
        jm = self.ti_jam.text.strip()
        mk = self.ti_mk.text.strip()
        
        if 'Pilih' in r or 'Pilih' in h or 'Pilih' in d:
            notif('Lengkapi Rombel, Hari, dan Durasi!', MERAH)
            return
        if not jm:
            notif('Isi jam mulai terlebih dahulu!', MERAH)
            return
        
        try:
            jam_obj = parse_jam(jm)
            if jam_obj == time(0, 0):
                notif('Format jam salah! Gunakan HH:MM', MERAH)
                return
        except:
            notif('Format jam salah! Gunakan HH:MM', MERAH)
            return
        
        if not validasi_jam_operasional(jm):
            notif(f'Jam mulai harus antara {JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI-1:02d}:00 dengan menit 00 atau 30!', MERAH)
            return
        
        dur = DURASI_CONFIG[d]
        
        waktu_selesai = menit_ke_jam(jm, dur)
        if waktu_selesai is None:
            notif(f'Durasi terlalu panjang! Kelas harus selesai sebelum {JAM_OPERASIONAL_SELESAI:02d}:00', MERAH)
            return
            
        if parse_jam(waktu_selesai) > time(JAM_OPERASIONAL_SELESAI, 0):
            notif(f'Durasi terlalu panjang! Kelas harus selesai sebelum {JAM_OPERASIONAL_SELESAI:02d}:00', MERAH)
            return
        
        self.lbl_q.text = 'Mencari slot kosong...'
        Clock.schedule_once(lambda *a: self._buka(r, h, jm, dur, mk), 0.15)

    def _buka(self, r, h, jm, dur, mk):
        self.lbl_q.text = ''
        popup_pilih_slot(self.dm, r, h, jm, dur, mk, lambda: None)

    def on_enter(self):
        self.dm._load_booking()

# ==============================================================
# SCREEN 2: GRID 
# ==============================================================
class GridScreen(Screen):
    def __init__(self, dm, **kw):
        super().__init__(**kw)
        self.dm = dm
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)
        topbar(root, 'Grid Ruang Kelas  (per 1 SKS = 50 menit)', self.manager,
               [('Home', UNGU, 'home'), ('Form', HIJAU, 'form'), ('Riwayat', BIRU, 'history')])

        fbar = BoxLayout(size_hint_y=None, height=dp(52),
                         padding=[dp(16), dp(8)], spacing=dp(10))
        bg_rect(fbar, NAVY_MED)
        fbar.add_widget(Label(text='Hari:', size_hint=(None, 1), width=dp(36),
                              color=PUTIH, font_size=dp(13), bold=True, markup=False))
        self.sp_hari = Spinner(text='Senin', values=tuple(HARI_LIST),
                               size_hint=(None, None), width=dp(100), height=dp(36),
                               background_normal='', background_color=(0, 0, 0, 0),
                               color=PUTIH, font_size=dp(13), bold=True)
        bg_round(self.sp_hari, UNGU, 8)
        self.sp_hari.bind(text=self._refresh)
        fbar.add_widget(self.sp_hari)

        for wc, tl in [(HIJAU, 'Tersedia'), (MERAH, 'Jadwal Tetap'), (MERAH, 'Booking Baru')]:
            leg = Button(text=tl, size_hint=(None, None), width=dp(100), height=dp(30),
                         background_normal='', background_color=(0, 0, 0, 0),
                         color=PUTIH, font_size=dp(11), bold=True, markup=False)
            bg_round(leg, wc, 5)
            fbar.add_widget(leg)

        self.lbl_stat = Label(text='', font_size=dp(11), color=PUTIH,
                              halign='right', markup=False)
        fbar.add_widget(self.lbl_stat)
        btn_ref = tombol('Refresh', (0.28, 0.32, 0.52, 1), self._refresh, h=dp(32), r=7, fs=dp(12))
        btn_ref.size_hint = (None, None)
        btn_ref.width = dp(72)
        fbar.add_widget(btn_ref)

        root.add_widget(fbar)
        self.sv = ScrollView()
        self.gw = BoxLayout(orientation='vertical', spacing=dp(2))
        self.sv.add_widget(self.gw)
        root.add_widget(self.sv)
        self.add_widget(root)
        self._refresh()

    def on_enter(self):
        self._refresh()

    def _refresh(self, *a):
        try:
            self.gw.clear_widgets()
            
            self.dm._load_booking()
            hari = self.sp_hari.text
            ruang_list = self.dm.get_ruang_list()
            
            if not ruang_list:
                self.gw.add_widget(Label(text='Tidak ada data ruang', color=MERAH))
                return
                
            cols = len(ruang_list) + 1

            terisi = sum(1 for jm, js in JAM_SLOT_GRID for ru in ruang_list
                         if self.dm.cek_slot_ruang(hari, jm, js, ru) is not None)
            total = len(JAM_SLOT_GRID) * len(ruang_list)
            self.lbl_stat.text = f'{total - terisi} kosong  |  {terisi} terisi  |  {len(JAM_SLOT_GRID)} slot'

            h_row = GridLayout(cols=cols, size_hint_y=None, height=dp(48), spacing=dp(2))
            bg_rect(h_row, NAVY)
            h_row.add_widget(Label(text='JAM\n(1 SKS)', color=PUTIH, font_size=dp(11),
                                   bold=True, size_hint_y=None, height=dp(48),
                                   halign='center', markup=False))
            for r in ruang_list:
                h_row.add_widget(Label(text=r, color=PUTIH, font_size=dp(10.5), bold=True,
                                       size_hint_y=None, height=dp(48),
                                       halign='center', valign='middle', markup=False))
            self.gw.add_widget(h_row)

            sv_in = ScrollView()
            rows = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
            rows.bind(minimum_height=rows.setter('height'))

            for i, (jm, js) in enumerate(JAM_SLOT_GRID):
                row_bg = (0.97, 0.97, 1.0, 1) if i % 2 == 0 else PUTIH
                baris = GridLayout(cols=cols, size_hint_y=None, height=dp(60), spacing=dp(2))
                bg_rect(baris, row_bg)

                baris.add_widget(Label(text=f'{jm}\n{js}', font_size=dp(11), color=NAVY,
                                       bold=True, size_hint_y=None, height=dp(60),
                                       halign='center', valign='middle', markup=False))

                for ruang in ruang_list:
                    booking = self.dm.cek_slot_ruang(hari, jm, js, ruang)
                    if booking is not None:
                        mk_v = str(booking.get('mata_kuliah', ''))
                        mk_s = (mk_v[:10] + '..') if len(mk_v) > 10 else mk_v
                        teks = f'{booking["rombel"]}\n{mk_s}' if mk_s else booking["rombel"]
                        tipe = str(booking.get('tipe', 'tetap'))
                        w_bg = MERAH if tipe == 'booking' else MERAH
                        w_tx = PUTIH
                    else:
                        teks = 'Tersedia'
                        w_bg = HIJAU
                        w_tx = PUTIH

                    sel = Button(text=teks, font_size=dp(10),
                                 background_normal='', background_color=(0, 0, 0, 0),
                                 color=w_tx, size_hint_y=None, height=dp(60),
                                 bold=True, halign='center', markup=False)
                    
                    with sel.canvas.before:
                        Color(*w_bg)
                        rr = RoundedRectangle(pos=sel.pos, size=sel.size, radius=[5])
                    
                    sel.bind(pos=lambda inst, val, rect=rr: setattr(rect, 'pos', val))
                    sel.bind(size=lambda inst, val, rect=rr: setattr(rect, 'size', val))
                    
                    sel.hari = hari
                    sel.jm = jm
                    sel.js = js
                    sel.ruang = ruang
                    sel.booking = booking
                    
                    sel.bind(on_press=self._klik)
                    baris.add_widget(sel)
                rows.add_widget(baris)

            sv_in.add_widget(rows)
            self.gw.add_widget(sv_in)
        except Exception as e:
            print(f"Error refreshing grid: {e}")
            self.gw.clear_widgets()
            self.gw.add_widget(Label(text=f'Error: {str(e)}', color=MERAH))

    def _klik(self, sel):
        hari, jm, js, ruang, booking = sel.hari, sel.jm, sel.js, sel.ruang, sel.booking
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        bg_round(box, PUTIH, 12)

        if booking is not None:
            mk_info = str(booking.get('mata_kuliah', ''))
            tipe = str(booking.get('tipe', 'tetap'))
            pesan = (f'ID      : {booking["id_booking"]}\n'
                     f'Rombel  : {booking["rombel"]}\n'
                     f'Hari    : {hari}   {jm} - {js}\n'
                     f'Ruang   : {ruang}\n'
                     f'Tipe    : {"Jadwal Tetap" if tipe == "tetap" else "Booking Baru"}')
            if mk_info:
                pesan += f'\nMK      : {mk_info}'
            box.add_widget(Label(text=pesan, font_size=dp(13), color=GELAP,
                                 halign='left', markup=False))
            pop = Popup(title='Detail Jadwal', content=box,
                        size_hint=(0.44, 0.50), auto_dismiss=False,
                        title_color=NAVY, separator_color=MERAH if tipe == 'tetap' else UNGU,
                        background_color=(0, 0, 0, 0.45))
            if tipe == 'booking':
                def batal(*a):
                    def do():
                        self.dm.batalkan(booking['id_booking'])
                        pop.dismiss()
                        self._refresh()
                        notif('Booking dibatalkan', MERAH)
                    popup_konfirmasi('Batalkan?',
                                     f'Batalkan booking\n{booking["rombel"]} {hari} {jm}?', do, MERAH)
                box.add_widget(tombol('Batalkan Booking', MERAH, batal, h=dp(40)))
            box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(38)))
            pop.open()
        else:
            box.add_widget(Label(text=f'{ruang} tersedia\n{hari}  {jm} - {js}\nPilih rombel & durasi:',
                                 font_size=dp(14), color=GELAP, halign='center', markup=False))
            sp_r = sp_ui(self.dm.get_rombel_list(), 'Pilih Rombel')
            sp_d = sp_ui(tuple(DURASI_CONFIG.keys()), 'Pilih Durasi')
            ti_mk = TextInput(hint_text='Mata Kuliah (opsional)',
                              size_hint_y=None, height=dp(40), font_size=dp(13),
                              multiline=False, background_color=ABU_MD,
                              foreground_color=GELAP, padding=[dp(10), dp(10)])
            box.add_widget(sp_r)
            box.add_widget(sp_d)
            box.add_widget(ti_mk)
            pop = Popup(title='Booking Langsung', content=box,
                        size_hint=(0.44, 0.60), auto_dismiss=False,
                        title_color=NAVY, separator_color=HIJAU,
                        background_color=(0, 0, 0, 0.45))
            btn_ok = tombol('BOOKING', HIJAU, lambda *a: None, h=dp(44))
            btn_x = tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(38))
            
            def do_book(*a):
                if 'Pilih' in sp_r.text or 'Pilih' in sp_d.text:
                    notif('Pilih rombel dan durasi!', MERAH)
                    return
                dur = DURASI_CONFIG[sp_d.text]
                js_book = menit_ke_jam(jm, dur)
                
                if js_book is None:
                    pop.dismiss()
                    notif(f'Durasi melebihi batas operasional!', KUNING)
                    return
                
                if parse_jam(js_book) > parse_jam(js):
                    pop.dismiss()
                    notif(f'Durasi melebihi slot ini (sampai {js})', KUNING)
                    return
                
                if parse_jam(js_book) > time(JAM_OPERASIONAL_SELESAI, 0):
                    pop.dismiss()
                    notif(f'Kelas harus selesai sebelum {JAM_OPERASIONAL_SELESAI:02d}:00', KUNING)
                    return
                
                try:
                    cek = self.dm.cek_rombel_slot(sp_r.text, hari, jm, js_book)
                    if cek:
                        pop.dismiss()
                        notif(f'Rombel {sp_r.text} sudah ada jadwal di slot ini!', MERAH)
                        return
                    cek2 = self.dm.cek_slot_ruang(hari, jm, js_book, ruang)
                    if cek2:
                        pop.dismiss()
                        notif(f'Ruang {ruang} sudah terpakai!', MERAH)
                        return
                    self.dm.tambah_booking(sp_r.text, hari, jm, js_book, ruang, ti_mk.text.strip(), dur)
                    pop.dismiss()
                    self._refresh()
                    notif(f'Booking berhasil!  {ruang}  {jm}-{js_book}', HIJAU)
                except ValueError as e:
                    notif(str(e), MERAH)
            
            btn_ok.bind(on_press=do_book)
            box.add_widget(btn_ok)
            box.add_widget(btn_x)
            pop.open()

# ==============================================================
# SCREEN 3: RIWAYAT 
# ==============================================================
class HistoryScreen(Screen):
    def __init__(self, dm, **kw):
        super().__init__(**kw)
        self.dm = dm
        self.current_page = 0
        self.items_per_page = 20
        self.total_items = 0
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)
        topbar(root, 'Riwayat Booking', self.manager,
               [('Home', UNGU, 'home'), ('Form', HIJAU, 'form'), ('Grid', BIRU, 'grid')])

        fbar = BoxLayout(size_hint_y=None, height=dp(52),
                         padding=[dp(16), dp(8)], spacing=dp(10))
        bg_rect(fbar, NAVY_MED)
        fbar.add_widget(Label(text='Filter:', size_hint=(None, 1), width=dp(44),
                              color=PUTIH, font_size=dp(13), bold=True, markup=False))
        self.sp_filter = Spinner(text='Semua', values=('Semua', 'aktif', 'batal', 'Selesai'),
                                 size_hint=(None, None), width=dp(110), height=dp(36),
                                 background_normal='', background_color=(0, 0, 0, 0),
                                 color=PUTIH, font_size=dp(13), bold=True)
        bg_round(self.sp_filter, UNGU, 8)
        self.sp_filter.bind(text=self._refresh)
        fbar.add_widget(self.sp_filter)

        stat = self.dm.get_statistik()
        for val, lbl, warna in [(stat['total_booking'], 'Aktif', HIJAU),
                                (stat['total_batal'], 'Batal', MERAH),
                                (stat['total_selesai'], 'Selesai', BIRU)]:
            b = Button(text=f'{val} {lbl}', size_hint=(None, None), width=dp(90), height=dp(32),
                       background_normal='', background_color=(0, 0, 0, 0),
                       color=PUTIH, font_size=dp(12), bold=True, markup=False)
            bg_round(b, warna, 5)
            fbar.add_widget(b)
        fbar.add_widget(Label(size_hint=(1, 1)))

        btn_reset = tombol('Reset Jadwal', MERAH, self._reset_jadwal, h=dp(34), r=7, fs=dp(12))
        btn_reset.size_hint = (None, None)
        btn_reset.width = dp(110)
        fbar.add_widget(btn_reset)

        th = BoxLayout(size_hint_y=None, height=dp(42), padding=[dp(8), dp(8)], spacing=dp(4))
        bg_round(th, NAVY, 6)
        for teks, sx in [('ID', 0.09), ('Rombel', 0.09), ('Hari', 0.08), ('Mulai', 0.08),
                         ('Selesai', 0.08), ('Ruang', 0.09), ('MK', 0.14),
                         ('Durasi', 0.07), ('Status', 0.09), ('Aksi', 0.19)]:
            th.add_widget(Label(text=teks, color=PUTIH, font_size=dp(11), bold=True,
                                size_hint_x=sx, halign='center', markup=False))

        pagination_bar = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(10), dp(5)], spacing=dp(10))
        bg_rect(pagination_bar, ABU_MD)
        
        self.btn_prev = tombol('◀ Sebelumnya', NAVY, self._prev_page, h=dp(36), r=6, fs=dp(11))
        self.btn_prev.size_hint = (None, None)
        self.btn_prev.width = dp(110)
        
        self.lbl_page = Label(text='Halaman 1', color=NAVY, font_size=dp(12), bold=True,
                              size_hint=(None, None), width=dp(100))
        
        self.btn_next = tombol('Selanjutnya ▶', NAVY, self._next_page, h=dp(36), r=6, fs=dp(11))
        self.btn_next.size_hint = (None, None)
        self.btn_next.width = dp(110)
        
        pagination_bar.add_widget(Label(size_hint=(1, 1)))
        pagination_bar.add_widget(self.btn_prev)
        pagination_bar.add_widget(self.lbl_page)
        pagination_bar.add_widget(self.btn_next)
        pagination_bar.add_widget(Label(size_hint=(1, 1)))

        sv = ScrollView()
        self.content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        self.content.bind(minimum_height=self.content.setter('height'))
        sv.add_widget(self.content)

        root.add_widget(fbar)
        root.add_widget(th)
        root.add_widget(sv)
        root.add_widget(pagination_bar)
        self.add_widget(root)

    def _prev_page(self, *a):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh()

    def _next_page(self, *a):
        if (self.current_page + 1) * self.items_per_page < self.total_items:
            self.current_page += 1
            self._refresh()

    def _reset_jadwal(self, *a):
        def do():
            ok = self.dm.reset_jadwal()
            if ok:
                notif('Jadwal berhasil direset ke jadwal tetap!', HIJAU)
            else:
                notif('Gagal reset - file backup tidak ada', MERAH)
            self._refresh()
        popup_konfirmasi('Reset Jadwal',
                         'Semua booking baru akan dihapus.\nJadwal dikembalikan ke jadwal awal.\nLanjutkan?',
                         do, MERAH)

    def on_enter(self):
        self.dm._load_booking()
        self.current_page = 0
        self._refresh()

    def _refresh(self, *a):
        try:
            self.content.clear_widgets()
            f = self.sp_filter.text
            
            df_full = self.dm.booking_df[self.dm.booking_df['tipe'] == 'booking'] if not self.dm.booking_df.empty else pd.DataFrame()
            if not df_full.empty:
                if f == 'aktif':
                    df_full = df_full[df_full['status'] == 'aktif']
                elif f == 'batal':
                    df_full = df_full[df_full['status'] == 'batal']
                elif f == 'Selesai':
                    df_full = df_full[df_full['kelas_selesai'] == 'Selesai']
            
            self.total_items = len(df_full)
            
            df = self.dm.riwayat_booking(self.current_page, self.items_per_page, f)

            total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
            self.lbl_page.text = f'Halaman {self.current_page + 1} / {total_pages}'
            self.btn_prev.disabled = (self.current_page == 0)
            self.btn_next.disabled = (self.current_page >= total_pages - 1)

            if df.empty:
                self.content.add_widget(Label(text='Belum ada data booking baru.',
                                              font_size=dp(14), color=ABU,
                                              size_hint_y=None, height=dp(80),
                                              halign='center', markup=False))
                return

            for _, row in df.iterrows():
                selesai = str(row.get('kelas_selesai', '')) == 'Selesai'
                aktif = row['status'] == 'aktif'

                row_bg = (0.93, 0.98, 0.93, 1) if selesai else ((0.97, 0.97, 1.0, 1) if aktif else (0.98, 0.95, 0.95, 1))
                item = BoxLayout(size_hint_y=None, height=dp(52),
                                 padding=[dp(8), dp(6)], spacing=dp(4))
                bg_round(item, row_bg, 6)

                mk = str(row.get('mata_kuliah', ''))
                mk = (mk[:13] + '..') if len(mk) > 13 else mk
                dur = f'{int(row.get("durasi_penggunaan", 0))}m' if row.get('durasi_penggunaan', 0) else '-'
                st = ('Selesai' if selesai else ('Aktif' if aktif else 'Batal'))
                wst = HIJAU if selesai else (GELAP if aktif else MERAH)

                for val, sx in [(row['id_booking'], 0.09), (row['rombel'], 0.09), (row['hari'], 0.08),
                                (str(row['jam_mulai']), 0.08), (str(row['jam_selesai']), 0.08),
                                (row['ruang'], 0.09), (mk or '-', 0.14), (dur, 0.07)]:
                    item.add_widget(Label(text=val, color=GELAP, font_size=dp(11),
                                          size_hint_x=sx, halign='center', markup=False))
                item.add_widget(Label(text=st, color=wst, font_size=dp(11), bold=True,
                                      size_hint_x=0.09, halign='center', markup=False))

                btn_box = BoxLayout(size_hint_x=0.19, spacing=dp(4))
                id_b = row['id_booking']

                if aktif and not selesai:
                    btn_s = Button(text='Selesai', font_size=dp(10), bold=True,
                                   size_hint=(0.5, 1), background_normal='',
                                   background_color=(0, 0, 0, 0), color=PUTIH, markup=False)
                    bg_round(btn_s, HIJAU, 5)
                    
                    def mk_sel(id_booking):
                        def cb(*a):
                            self.dm.kelas_selesai(id_booking)
                            notif('Kelas ditandai selesai!', HIJAU)
                            self._refresh()
                        return cb
                    
                    btn_s.bind(on_press=mk_sel(id_b))
                    btn_box.add_widget(btn_s)

                if aktif:
                    btn_b = Button(text='Batal', font_size=dp(10), bold=True,
                                   size_hint=(0.5, 1), background_normal='',
                                   background_color=(0, 0, 0, 0), color=PUTIH, markup=False)
                    bg_round(btn_b, MERAH, 5)
                    
                    def mk_batal(id_booking):
                        def cb(*a):
                            def do():
                                self.dm.batalkan(id_booking)
                                notif('Booking dibatalkan', MERAH)
                                self._refresh()
                            popup_konfirmasi('Batalkan?', f'Batalkan booking\n{id_booking}?', do, MERAH)
                        return cb
                    
                    btn_b.bind(on_press=mk_batal(id_b))
                    btn_box.add_widget(btn_b)

                item.add_widget(btn_box)
                self.content.add_widget(item)
        except Exception as e:
            print(f"Error refreshing history: {e}")
            self.content.clear_widgets()
            self.content.add_widget(Label(text=f'Error: {str(e)}', color=MERAH))

# ==============================================================
# APP 
# ==============================================================
class BookingApp(App):
    def build(self):
        Window.size = (1200, 720)
        Window.clearcolor = BG

        try:
            dm = DataManager()
            queue = BookingQueue()

            self.sm = ScreenManager(
                transition=FadeTransition(duration=0.18)
            )

            self.sm.add_widget(HomeScreen(dm=dm, name='home'))
            self.sm.add_widget(FormScreen(dm=dm, queue=queue, name='form'))
            self.sm.add_widget(GridScreen(dm=dm, name='grid'))
            self.sm.add_widget(HistoryScreen(dm=dm, name='history'))

            self.sm.current = 'home'

            Window.bind(on_keyboard=self.on_back)

            return self.sm
        except Exception as e:
            print(f"Error building app: {e}")
            root = BoxLayout()
            root.add_widget(Label(text=f'Error: {str(e)}', color=MERAH))
            return root

    def on_back(self, window, key, *args):
        if key == 27:
            if self.sm.current != 'home':
                self.sm.current = 'home'
                return True
            return False

if __name__ == '__main__':
    BookingApp().run()