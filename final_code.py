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
import json

# ── WARNA ──────────────────────────────────────────────────
NAVY       = (0.05, 0.10, 0.28, 1)
NAVY_MED   = (0.08, 0.14, 0.38, 1)
UNGU       = (0.42, 0.18, 0.78, 1)
UNGU_MUD   = (0.42, 0.18, 0.78, 0.12)
HIJAU      = (0.08, 0.72, 0.44, 1)
MERAH      = (0.90, 0.22, 0.22, 1)
KUNING     = (0.95, 0.70, 0.00, 1)
BG         = (0.95, 0.95, 0.98, 1)
PUTIH      = (1.00, 1.00, 1.00, 1)
GELAP      = (0.10, 0.10, 0.18, 1)
ABU        = (0.60, 0.62, 0.68, 1)
ABU_MD     = (0.95, 0.95, 0.97, 1)
ORANGE     = (1.00, 0.55, 0.00, 1)
ORANGE_MUD = (1.00, 0.55, 0.00, 0.12) 
BIRU       = (0.20, 0.60, 0.86, 1)
BIRU_MUDA  = (0.35, 0.75, 0.95, 1)

# ── KONSTANTA ──────────────────────────────────────────────
HARI_LIST = ["Senin", "Selasa", "Rabu", "Kamis"]
JAM_OPERASIONAL_MULAI = 7  # 07:00
JAM_OPERASIONAL_SELESAI = 17  # 17:00

SKS_CONFIG = {
    "1 SKS (50 menit)": 50,
    "2 SKS (100 menit)": 100,
    "3 SKS (150 menit)": 150,
}

DURASI_CONFIG = {
    "50 Menit (1 SKS)": 50,
    "100 Menit (2 SKS)": 100,
    "150 Menit (3 SKS)": 150,
}

def buat_slot_grid():
    slots = []
    start = JAM_OPERASIONAL_MULAI * 60  
    end   = JAM_OPERASIONAL_SELESAI * 60 
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
FILE_LOG_AKTIVITAS = os.path.join(BASE_DIR, "log_aktivitas.json")

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICON_FORM = os.path.join(ASSETS_DIR, "Form Booking.png")
ICON_GRID = os.path.join(ASSETS_DIR, "Grid Jadwal.png")
ICON_INFO = os.path.join(ASSETS_DIR, "Informasi.png")
ICON_RIWAYAT = os.path.join(ASSETS_DIR, "Riwayat.png")

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

def buat_file_contoh():
    try:
        if not os.path.exists(FILE_RUANG):
            df_ruang = pd.DataFrame({
                'kode_ruang': ['Ruang 101', 'Ruang 102', 'Ruang 103', 'Ruang 104', 
                              'Ruang 105', 'Ruang 106', 'Ruang 107', 'Ruang 108']
            })
            df_ruang.to_csv(FILE_RUANG, index=False)
        
        if not os.path.exists(FILE_ROMBEL):
            df_rombel = pd.DataFrame({
                'kode_rombel': ['INT 24', '2024 A', '2024 B', '2024 C', '2024 D', '2024 E',
                               'INT 25', '2025 A', '2025 B', '2025 C', '2025 D', '2025 E', 
                               '2025 F', '2025 G']
            })
            df_rombel.to_csv(FILE_ROMBEL, index=False)
        
        if not os.path.exists(FILE_BOOKING):
            df_booking = pd.DataFrame(columns=[
                'id_booking', 'rombel', 'hari', 'jam_mulai', 'jam_selesai', 'ruang',
                'mata_kuliah', 'tipe', 'status', 'waktu_booking', 'durasi_penggunaan',
                'kelas_selesai', 'waktu_selesai', 'antrian_ke'
            ])
            df_booking.to_csv(FILE_BOOKING, index=False)
            
        # Buat file log aktivitas
        if not os.path.exists(FILE_LOG_AKTIVITAS):
            with open(FILE_LOG_AKTIVITAS, 'w') as f:
                json.dump([], f)
    except Exception as e:
        print(f"Error creating example files: {e}")

buat_file_contoh()

# ==============================================================
# ACTIVITY LOGGER (Internal use only)
# ==============================================================
class ActivityLogger:
    """Mencatat semua aktivitas booking secara internal"""
    
    def __init__(self):
        self.logs = []
        self.lock = threading.Lock()
        self._load_logs()
    
    def _load_logs(self):
        """Memuat log dari file"""
        try:
            if os.path.exists(FILE_LOG_AKTIVITAS):
                with open(FILE_LOG_AKTIVITAS, 'r') as f:
                    self.logs = json.load(f)
            else:
                self.logs = []
        except Exception as e:
            print(f"Error loading logs: {e}")
            self.logs = []
    
    def _save_logs(self):
        """Menyimpan log ke file"""
        try:
            with open(FILE_LOG_AKTIVITAS, 'w') as f:
                json.dump(self.logs[-1000:], f)
        except Exception as e:
            print(f"Error saving logs: {e}")
    
    def add_log(self, tipe_aktivitas, detail, warna=UNGU):
        """Menambahkan log aktivitas baru"""
        with self.lock:
            log_entry = {
                'id': str(uuid.uuid4())[:8].upper(),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'tipe': tipe_aktivitas,
                'detail': detail,
                'warna': warna
            }
            self.logs.insert(0, log_entry)
            self._save_logs()
    
    def log_booking_created(self, rombel, ruang, hari, jam_mulai, jam_selesai, posisi_antrian):
        """Mencatat pembuatan booking baru"""
        if posisi_antrian == 1:
            detail = f"{rombel} membooking {ruang} pada {hari} {jam_mulai}-{jam_selesai} (Posisi Utama)"
        else:
            detail = f"{rombel} masuk antrean ke-{posisi_antrian} untuk {ruang} pada {hari} {jam_mulai}-{jam_selesai}"
        self.add_log("Booking Baru", detail)
    
    def log_booking_cancelled(self, rombel, ruang, hari, jam_mulai, jam_selesai, posisi):
        """Mencatat pembatalan booking"""
        detail = f"{rombel} membatalkan booking di {ruang} pada {hari} {jam_mulai}-{jam_selesai} (Antrean ke-{posisi})"
        self.add_log("Pembatalan", detail)
    
    def log_class_completed(self, rombel, ruang, hari, jam_mulai, jam_selesai):
        """Mencatat penyelesaian kelas"""
        detail = f"{rombel} menyelesaikan kelas di {ruang} pada {hari} {jam_mulai}-{jam_selesai}"
        self.add_log("Kelas Selesai", detail)
    
    def log_queue_shift(self, rombel, ruang, hari, jam_mulai, jam_selesai, posisi_baru):
        """Mencatat pergeseran antrean"""
        detail = f"{rombel} naik ke posisi ke-{posisi_baru} di {ruang} pada {hari} {jam_mulai}-{jam_selesai}"
        self.add_log("Pergeseran Antrean", detail)

# Global logger instance
activity_logger = ActivityLogger()

# ==============================================================
# HELPER WAKTU 
# ==============================================================
def parse_jam(s):
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
    try:
        jam_obj = parse_jam(jam_str)
        if jam_obj == time(0, 0):
            return False
        batas_mulai = time(JAM_OPERASIONAL_MULAI, 0)
        batas_akhir = time(JAM_OPERASIONAL_SELESAI, 0)
        return batas_mulai <= jam_obj <= batas_akhir
    except:
        return False

# ==============================================================
# QUEUE MANAGEMENT
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
        # Ubah semua data yang sudah ada menjadi jadwal tetap (MERAH)
        self._convert_existing_to_tetap()
        
    def _convert_existing_to_tetap(self):
        """Mengubah semua data booking yang sudah ada menjadi jadwal tetap (berwarna MERAH)"""
        with self.lock:
            if self.booking_df is not None and not self.booking_df.empty:
                # Hitung jumlah data yang akan diubah
                if 'tipe' in self.booking_df.columns:
                    # Ubah semua yang tipe-nya bukan 'tetap' menjadi 'tetap'
                    mask = self.booking_df['tipe'] != 'tetap'
                    if mask.any():
                        self.booking_df.loc[mask, 'tipe'] = 'tetap'
                        self.booking_df.loc[mask, 'antrian_ke'] = 1
                        self.simpan()
                        print(f"✅ {mask.sum()} data diubah menjadi jadwal tetap (warna MERAH)")
                    else:
                        print(f"✅ Semua data sudah berupa jadwal tetap")
                else:
                    # Jika kolom tipe tidak ada, tambahkan
                    self.booking_df['tipe'] = 'tetap'
                    self.booking_df['antrian_ke'] = 1
                    self.simpan()
                    print(f"✅ Kolom 'tipe' ditambahkan, {len(self.booking_df)} data menjadi jadwal tetap (warna MERAH)")
                
                # Tampilkan statistik
                jml_tetap = len(self.booking_df[self.booking_df['tipe'] == 'tetap'])
                print(f"📊 Total jadwal tetap di database: {jml_tetap}")
            else:
                print("📋 Database booking kosong")
        
    def _load_all_data(self):
        with self.lock:
            try:
                if os.path.exists(FILE_RUANG):
                    try:
                        self.ruang_df = pd.read_csv(FILE_RUANG)
                        self.ruang_sorted = sorted(self.ruang_df['kode_ruang'].tolist())
                    except Exception as e:
                        print(f"Error loading ruang: {e}")
                        self.ruang_df = pd.DataFrame({'kode_ruang': []})
                        self.ruang_sorted = []
                
                if os.path.exists(FILE_ROMBEL):
                    try:
                        self.rombel_df = pd.read_csv(FILE_ROMBEL)
                    except Exception as e:
                        print(f"Error loading rombel: {e}")
                        self.rombel_df = pd.DataFrame({'kode_rombel': []})
                
                self._load_booking()
                
                if not os.path.exists(FILE_BACKUP) and os.path.exists(FILE_BOOKING):
                    shutil.copy(FILE_BOOKING, FILE_BACKUP)
            except Exception as e:
                print(f"Error loading data: {e}")
                self.booking_df = self._create_empty_booking_df()

    def _create_empty_booking_df(self):
        return pd.DataFrame(columns=[
            'id_booking', 'rombel', 'hari', 'jam_mulai', 'jam_selesai', 'ruang',
            'mata_kuliah', 'tipe', 'status', 'waktu_booking', 'durasi_penggunaan',
            'kelas_selesai', 'waktu_selesai', 'antrian_ke'
        ])

    def _load_booking(self):
        with self.lock:
            try:
                if os.path.exists(FILE_BOOKING):
                    df = pd.read_csv(FILE_BOOKING)
                    if not df.empty and 'id_booking' in df.columns:
                        # Pastikan semua kolom yang diperlukan ada
                        defaults = {
                            'mata_kuliah': '', 
                            'durasi_penggunaan': 0,
                            'kelas_selesai': 'Belum', 
                            'waktu_selesai': '',
                            'tipe': 'booking',  # Default booking
                            'antrian_ke': 1,
                            'status': 'aktif'
                        }
                        for col, default in defaults.items():
                            if col not in df.columns:
                                df[col] = default
                        
                        # Bersihkan data tipe (hapus spasi, lower case)
                        if 'tipe' in df.columns:
                            df['tipe'] = df['tipe'].astype(str).str.strip().str.lower()
                            df['tipe'] = df['tipe'].replace('nan', 'booking')
                            df['tipe'] = df['tipe'].fillna('booking')
                        
                        # Bersihkan data status
                        if 'status' in df.columns:
                            df['status'] = df['status'].astype(str).str.strip().str.lower()
                            df['status'] = df['status'].replace('nan', 'aktif')
                            df['status'] = df['status'].fillna('aktif')
                        
                        df = df.replace('nan', '')
                        df = df.fillna('')
                        self.booking_df = df
                    else:
                        self.booking_df = self._create_empty_booking_df()
                else:
                    self.booking_df = self._create_empty_booking_df()
            except Exception as e:
                print(f"Error loading booking: {e}")
                self.booking_df = self._create_empty_booking_df()

    def simpan(self): 
        with self.lock:
            try:
                self.booking_df.to_csv(FILE_BOOKING, index=False)
            except Exception as e:
                print(f"Error saving booking: {e}")

    def hitung_antrian_slot(self, hari, jm, js, ruang):
        if self.booking_df is None or self.booking_df.empty:
            return 0, False
        with self.lock:
            aktif = self.booking_df[
                (self.booking_df['hari'] == hari) &
                (self.booking_df['ruang'] == ruang) &
                (self.booking_df['status'] == 'aktif')
            ]
            count = 0
            is_tetap = False
            for _, row in aktif.iterrows():
                if overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    # Pastikan tipe dibaca dengan benar
                    tipe_row = str(row.get('tipe', 'booking')).lower().strip()
                    if tipe_row == 'tetap':
                        is_tetap = True
                    else:
                        count += 1
            return count, is_tetap

    def cari_rekomendasi_ruang(self, hari, jam_mulai_req, durasi):
        hasil = []
        js = menit_ke_jam(jam_mulai_req, durasi)
        if js is None or parse_jam(js) > time(JAM_OPERASIONAL_SELESAI, 0):
            return hasil
        
        for ruang in self.ruang_sorted:
            count, is_tetap = self.hitung_antrian_slot(hari, jam_mulai_req, js, ruang)
            if not is_tetap:
                hasil.append({
                    'jam_mulai': jam_mulai_req, 
                    'jam_selesai': js, 
                    'ruang': ruang, 
                    'antrian_ke': count + 1
                })
        return hasil

    def cari_rekomendasi_jam(self, hari, ruang, durasi):
        hasil = []
        for jm_slot, _ in JAM_SLOT_GRID:
            js = menit_ke_jam(jm_slot, durasi)
            if js is None or parse_jam(js) > time(JAM_OPERASIONAL_SELESAI, 0):
                continue
            count, is_tetap = self.hitung_antrian_slot(hari, jm_slot, js, ruang)
            if not is_tetap: 
                hasil.append({
                    'jam_mulai': jm_slot, 
                    'jam_selesai': js, 
                    'ruang': ruang, 
                    'antrian_ke': count + 1
                })
        return hasil

    def tambah_booking(self, rombel, hari, jm, js, ruang, mk='', durasi=0):
        with self.lock:
            if self.cek_rombel_slot(rombel, hari, jm, js):
                raise ValueError(f"Rombel {rombel} sudah memiliki jadwal di slot ini")
            
            count, is_tetap = self.hitung_antrian_slot(hari, jm, js, ruang)
            if is_tetap:
                raise ValueError(f"Ruang {ruang} dikunci oleh Jadwal Tetap!")
            
            new_id = str(uuid.uuid4())[:8].upper()
            new_row = {
                'id_booking': new_id, 
                'rombel': rombel, 
                'hari': hari, 
                'jam_mulai': jm, 
                'jam_selesai': js,
                'ruang': ruang, 
                'mata_kuliah': mk if mk else '', 
                'tipe': 'booking', 
                'status': 'aktif',
                'waktu_booking': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'durasi_penggunaan': durasi, 
                'kelas_selesai': 'Belum', 
                'waktu_selesai': '',
                'antrian_ke': count + 1
            }
            
            self.booking_df = pd.concat([self.booking_df, pd.DataFrame([new_row])], ignore_index=True)
            self.simpan()
            
            # Log aktivitas booking
            global activity_logger
            activity_logger.log_booking_created(rombel, ruang, hari, jm, js, count + 1)
            
            return new_id, count + 1

    def tambah_jadwal_tetap(self, rombel, hari, jam_mulai, jam_selesai, ruang, mata_kuliah=''):
        """Menambahkan jadwal tetap (warna MERAH) - tidak bisa dibatalkan/dihapus"""
        with self.lock:
            # Cek apakah slot sudah ada jadwal tetap
            count, is_tetap = self.hitung_antrian_slot(hari, jam_mulai, jam_selesai, ruang)
            if is_tetap:
                raise ValueError(f"Slot ini sudah memiliki jadwal tetap!")
            
            new_id = str(uuid.uuid4())[:8].upper()
            new_row = {
                'id_booking': new_id,
                'rombel': rombel,
                'hari': hari,
                'jam_mulai': jam_mulai,
                'jam_selesai': jam_selesai,
                'ruang': ruang,
                'mata_kuliah': mata_kuliah if mata_kuliah else '',
                'tipe': 'tetap',  # ← PENTING: tipe 'tetap' untuk warna MERAH
                'status': 'aktif',
                'waktu_booking': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'durasi_penggunaan': 50,  # Default 1 SKS
                'kelas_selesai': 'Belum',
                'waktu_selesai': '',
                'antrian_ke': 1
            }
            
            self.booking_df = pd.concat([self.booking_df, pd.DataFrame([new_row])], ignore_index=True)
            self.simpan()
            
            # Log aktivitas
            global activity_logger
            activity_logger.add_log("Jadwal Tetap", f"Menambahkan jadwal tetap: {rombel} - {ruang} ({hari} {jam_mulai}-{jam_selesai})")
            
            return new_id

    def _geser_antrian_maju(self, hari, jm, js, ruang):
        with self.lock:
            for idx, row in self.booking_df.iterrows():
                if (row['hari'] == hari and 
                    row['ruang'] == ruang and 
                    row['status'] == 'aktif' and 
                    'antrian_ke' in row and
                    row['antrian_ke'] > 1 and
                    overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai']))):
                    curr_q = int(row['antrian_ke'])
                    new_q = max(1, curr_q - 1)
                    self.booking_df.at[idx, 'antrian_ke'] = new_q
                    
                    # Log pergeseran antrean
                    global activity_logger
                    activity_logger.log_queue_shift(row['rombel'], ruang, hari, 
                                                    row['jam_mulai'], row['jam_selesai'], new_q)

    def batalkan(self, id_booking):
        with self.lock:
            mask = self.booking_df['id_booking'] == id_booking
            if mask.any():
                row = self.booking_df[mask].iloc[0]
                
                # Cek apakah jadwal tetap
                if row.get('tipe') == 'tetap':
                    raise ValueError("❌ Jadwal tetap tidak dapat dibatalkan!")
                
                posisi = row.get('antrian_ke', 1)
                self.booking_df.loc[mask, 'status'] = 'batal'
                
                # Log pembatalan
                global activity_logger
                activity_logger.log_booking_cancelled(row['rombel'], row['ruang'], row['hari'],
                                                      row['jam_mulai'], row['jam_selesai'], posisi)
                
                self._geser_antrian_maju(row['hari'], row['jam_mulai'], row['jam_selesai'], row['ruang'])
                self.simpan()

    def kelas_selesai(self, id_booking): 
        with self.lock:
            mask = self.booking_df['id_booking'] == id_booking

            if mask.any():
                row = self.booking_df[mask].iloc[0]
                
                # Cek apakah jadwal tetap
                if row.get('tipe') == 'tetap':
                    # Jadwal tetap tidak bisa ditandai selesai, tetap aktif
                    raise ValueError("❌ Jadwal tetap tidak dapat ditandai selesai!")
                    return

                # booking utama selesai -> nonaktifkan
                self.booking_df.loc[mask, 'kelas_selesai'] = 'Selesai'
                self.booking_df.loc[mask, 'status'] = 'selesai'
                self.booking_df.loc[mask, 'waktu_selesai'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Log penyelesaian kelas
                global activity_logger
                activity_logger.log_class_completed(row['rombel'], row['ruang'], row['hari'],
                                                    row['jam_mulai'], row['jam_selesai'])

                hari = row['hari']
                ruang = row['ruang']
                jm = row['jam_mulai']
                js = row['jam_selesai']

                # semua antrean di slot yg sama
                antrian = self.booking_df[
                    (self.booking_df['hari'] == hari) &
                    (self.booking_df['ruang'] == ruang) &
                    (self.booking_df['status'] == 'aktif')
                ]

                for idx, item in antrian.iterrows():
                    if overlap(jm, js,
                               str(item['jam_mulai']),
                               str(item['jam_selesai'])):
                        if 'antrian_ke' in item and item['antrian_ke'] > 1:
                            new_q = item['antrian_ke'] - 1
                            self.booking_df.at[idx, 'antrian_ke'] = new_q
                            
                            # Log pergeseran antrean
                            activity_logger.log_queue_shift(item['rombel'], ruang, hari,
                                                           item['jam_mulai'], item['jam_selesai'], new_q)

                self.simpan()

    def reset_jadwal(self):
        with self.lock:
            if os.path.exists(FILE_BACKUP):
                shutil.copy(FILE_BACKUP, FILE_BOOKING)
                self._load_booking()
                
                # Log reset jadwal
                global activity_logger
                activity_logger.add_log("Reset Jadwal", "Semua booking direset ke kondisi awal")
                return True
            return False

    def cek_slot_ruang(self, hari, jm, js, ruang):
        if self.booking_df is None or self.booking_df.empty: 
            return None
        with self.lock:
            aktif = self.booking_df[(self.booking_df['hari'] == hari) &
                                    (self.booking_df['ruang'] == ruang) &
                                    (self.booking_df['status'] == 'aktif')]
            aktif_sorted = aktif.sort_values(by=['tipe', 'antrian_ke'], ascending=[False, True])
            for _, row in aktif_sorted.iterrows():
                if overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    return row
            return None

    def dapatkan_semua_antrian_slot(self, hari, jm, js, ruang):
        if self.booking_df is None or self.booking_df.empty:
            return []
        with self.lock:
            aktif = self.booking_df[
                (self.booking_df['hari'] == hari) &
                (self.booking_df['ruang'] == ruang) &
                (self.booking_df['status'] == 'aktif')
            ]
            hasil = []
            for _, row in aktif.iterrows():
                if overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    item = row.to_dict()
                    # Pastikan tipe terbaca dengan benar
                    if 'tipe' not in item or pd.isna(item['tipe']):
                        item['tipe'] = 'booking'
                    else:
                        item['tipe'] = str(item['tipe']).lower().strip()
                    
                    if item.get('mata_kuliah') == 'nan' or item.get('mata_kuliah') is None:
                        item['mata_kuliah'] = ''
                    if 'antrian_ke' not in item or pd.isna(item['antrian_ke']):
                        item['antrian_ke'] = 1
                    hasil.append(item)
            
            # Urutkan: jadwal tetap di atas, lalu berdasarkan antrian_ke
            hasil.sort(key=lambda x: (0 if x.get('tipe') == 'tetap' else 1, x.get('antrian_ke', 1)))
            return hasil

    def cek_rombel_slot(self, rombel, hari, jm, js):
        if self.booking_df is None or self.booking_df.empty: 
            return False
        with self.lock:
            aktif = self.booking_df[(self.booking_df['rombel'] == rombel) &
                                    (self.booking_df['hari'] == hari) &
                                    (self.booking_df['status'] == 'aktif')]
            for _, row in aktif.iterrows():
                if overlap(jm, js, str(row['jam_mulai']), str(row['jam_selesai'])):
                    return True
            return False

    def get_rombel_list(self):
        with self.lock:
            if self.rombel_df is None or self.rombel_df.empty:
                return []
            urutan = ["INT 24","2024 A","2024 B","2024 C","2024 D","2024 E",
                      "INT 25","2025 A","2025 B","2025 C","2025 D","2025 E","2025 F","2025 G"]
            semua = self.rombel_df['kode_rombel'].tolist()
            return [r for r in urutan if r in semua]

    def get_ruang_list(self): 
        with self.lock:
            if self.ruang_df is not None and not self.ruang_df.empty:
                return self.ruang_df['kode_ruang'].tolist()
            return []

    def get_statistik(self):
        with self.lock:
            if self.booking_df is None or self.booking_df.empty:
                return {'total_booking': 0, 'ruang_terpakai': 0, 'rombel_aktif': 0, 'total_batal': 0, 'total_selesai': 0}
            aktif = self.booking_df[self.booking_df['status'] == 'aktif']
            return {
                'total_booking': len(aktif),
                'ruang_terpakai': len(set(aktif['ruang'])) if not aktif.empty else 0,
                'rombel_aktif': len(set(aktif['rombel'])) if not aktif.empty else 0,
                'total_batal': len(self.booking_df[self.booking_df['status'] == 'batal']),
                'total_selesai': len(self.booking_df[self.booking_df['kelas_selesai'] == 'Selesai']),
            }

    def riwayat_booking(self, page=0, items_per_page=20, filter_status='Semua'):
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
    w.bind(pos=lambda a, v: setattr(r, 'pos', v), size=lambda a, v: setattr(r, 'size', v))

def bg_round(w, c, rad=10):
    with w.canvas.before:
        Color(*c)
        r = RoundedRectangle(pos=w.pos, size=w.size, radius=[rad])
    w.bind(pos=lambda a, v: setattr(r, 'pos', v), size=lambda a, v: setattr(r, 'size', v))

def tombol(text, warna, cb, h=dp(44), r=10, fs=dp(14)):
    b = Button(text=text, size_hint_y=None, height=h,
               background_normal='', background_color=(0,0,0,0),
               color=PUTIH, font_size=fs, bold=True, markup=False)
    bg_round(b, warna, r)
    b.bind(on_press=cb)
    def dn(i, t):
        if i.collide_point(*t.pos): 
            anim = Animation(opacity=0.72, duration=0.07)
            anim.start(i)
    def up(i, t): 
        anim = Animation(opacity=1.0, duration=0.1)
        anim.start(i)
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
    lbl = Label(text=f'{icon}  {pesan}', font_size=dp(14), color=GELAP, bold=True, halign='center', valign='middle', markup=False)
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
    inner.add_widget(lbl)
    outer.add_widget(inner)
    pop = Popup(title='', content=outer, size_hint=(0.42, 0.13), auto_dismiss=True, separator_height=0, title_size=0)
    pop.open()
    Clock.schedule_once(lambda *a: pop.dismiss(), durasi)

def popup_ok(judul, pesan, warna=None):
    if warna is None: 
        warna = UNGU
    box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))
    bg_round(box, PUTIH, 12)
    lbl = Label(text=pesan, font_size=dp(13), color=GELAP, halign='left', valign='top', markup=False)
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    box.add_widget(lbl)
    pop = Popup(title=judul, content=box, size_hint=(0.52, 0.62), auto_dismiss=False, title_color=PUTIH, separator_color=warna)
    box.add_widget(tombol('OK', warna, lambda *a: pop.dismiss(), h=dp(42)))
    pop.open()
    return pop

def popup_konfirmasi(judul, pesan, cb_ya, warna_ya=MERAH):
    box = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(12))
    bg_round(box, PUTIH, 12)
    lbl = Label(text=pesan, font_size=dp(14), color=GELAP, halign='center', valign='middle', markup=False)
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
    box.add_widget(lbl)
    baris = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
    pop = Popup(title=judul, content=box, size_hint=(0.44, 0.36), auto_dismiss=False, title_color=PUTIH, separator_color=warna_ya)
    def ya(*a): 
        pop.dismiss()
        cb_ya()
    baris.add_widget(tombol('Ya, Lanjutkan', warna_ya, ya, h=dp(42)))
    baris.add_widget(tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(42)))
    box.add_widget(baris)
    pop.open()

# ==============================================================
# DIALOG REKOMENDASI SLOT
# ==============================================================
def popup_pilih_slot_dinamis(dm, mode_cari, rombel, hari, jam_mulai, durasi, ruang_target, mk, on_booked):
    if mode_cari == 'Cari Berdasarkan Jam':
        slots = dm.cari_rekomendasi_ruang(hari, jam_mulai, durasi)
        title_text = f'Rekomendasi Ruangan - Jam {jam_mulai}'
    else:
        slots = dm.cari_rekomendasi_jam(hari, ruang_target, durasi)
        title_text = f'Rekomendasi Jam - {ruang_target}'

    box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
    bg_round(box, PUTIH, 12)

    if not slots:
        box.add_widget(Label(text='Tidak ada slot kosong yang tersedia.', font_size=dp(14), color=GELAP, halign='center', markup=False))
        pop = Popup(title='Slot Tidak Tersedia', content=box, size_hint=(0.44, 0.32), auto_dismiss=False, separator_color=MERAH)
        box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(40)))
        pop.open()
        return

    box.add_widget(Label(text=f'Hasil Filter ({hari} - {durasi} Menit):\nPilih opsi di bawah untuk masuk ke antrean:', 
                        font_size=dp(13), color=NAVY, bold=True, size_hint_y=None, height=dp(40), halign='center', markup=False))

    sv = ScrollView(size_hint=(1, 1))
    grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(8), padding=[0, dp(4)])
    grid.bind(minimum_height=grid.setter('height'))

    pop = Popup(title=title_text, content=box, size_hint=(0.52, 0.68), auto_dismiss=False, title_color=NAVY, separator_color=UNGU)

    for slot in slots:
        jm_opt = slot['jam_mulai']
        js_opt = slot['jam_selesai']
        ru_opt = slot['ruang']
        antrian = slot['antrian_ke']
        
        warna_slot = HIJAU if antrian == 1 else ORANGE
        teks_posisi = "[UTAMA]" if antrian == 1 else f"[ANTREAN KE-{antrian}]"
        
        btn_s = Button(text=f'{ru_opt}\n{jm_opt} - {js_opt}\n{teks_posisi}',
                       size_hint_y=None, height=dp(65),
                       background_normal='', background_color=(0, 0, 0, 0),
                       color=PUTIH, font_size=dp(11), bold=True,
                       markup=False, halign='center')
        bg_round(btn_s, warna_slot, 8)
        
        dm_ref = weakref.ref(dm)
        
        def buat_cb(j_m, j_s, r_u):
            def cb(*a):
                dm_local = dm_ref()
                if dm_local is None: 
                    return
                try:
                    id_b, pos_ke = dm_local.tambah_booking(rombel, hari, j_m, j_s, r_u, mk, durasi)
                    pop.dismiss()
                    
                    if pos_ke == 1:
                        notif(f'Booking Utama Berhasil! {r_u} ({j_m}-{j_s})', HIJAU)
                    else:
                        notif(f'Masuk Antrean Ke-{pos_ke} di {r_u}!', KUNING)
                        
                    if on_booked: 
                        on_booked()
                except ValueError as e:
                    notif(str(e), MERAH)
            return cb
        
        btn_s.bind(on_press=buat_cb(jm_opt, js_opt, ru_opt))
        grid.add_widget(btn_s)

    sv.add_widget(grid)
    box.add_widget(sv)
    box.add_widget(tombol('Batal', ABU, lambda *a: pop.dismiss(), h=dp(40)))
    pop.open()

def topbar(root_widget, title, manager_ref, tombol_list):
    top = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(20), dp(10)], spacing=dp(10))
    bg_rect(top, NAVY)
    top.add_widget(Label(text=title, color=PUTIH, font_size=dp(16), bold=True, halign='left', valign='middle'))

    def pindah_screen(screen_name):
        app = App.get_running_app()
        if app and app.root: 
            app.root.current = screen_name

    for teks, warna, screen in tombol_list:
        b = tombol(teks, warna, lambda *a, s=screen: pindah_screen(s), h=dp(34), r=7, fs=dp(12))
        b.size_hint = (None, None)
        b.width = dp(100)
        top.add_widget(b)
    root_widget.add_widget(top)

# ==============================================================
# POPUP INFORMASI APLIKASI
# ==============================================================
def popup_info_aplikasi(dm):
    """Popup informasi tentang aplikasi"""
    
    # Container utama
    content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(16))
    bg_round(content, PUTIH, 12)
    
    # Header dengan icon dan judul
    header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80), spacing=dp(8))
    
    # Judul
    judul_box = BoxLayout(size_hint_y=None, height=dp(40))
    icon_label = Label(text='📋', font_size=dp(32), size_hint_x=None, width=dp(50))
    judul_label = Label(text='Tentang Aplikasi', font_size=dp(20), bold=True, color=NAVY, 
                        halign='left', valign='middle')
    judul_label.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    judul_box.add_widget(icon_label)
    judul_box.add_widget(judul_label)
    judul_box.add_widget(Label(size_hint_x=1))
    header.add_widget(judul_box)
    
    # Garis pemisah
    line = BoxLayout(size_hint_y=None, height=dp(2))
    bg_rect(line, UNGU)
    header.add_widget(line)
    
    content.add_widget(header)
    
    # Area scroll untuk konten
    sv = ScrollView(size_hint=(1, 1))
    info_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(24))
    info_container.bind(minimum_height=info_container.setter('height'))
    
    # ==================== STATISTIK ====================
    stat = dm.get_statistik()
    stat_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
    stat_box.height = dp(180)
    
    # Header statistik dengan background
    stat_header = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
    bg_round(stat_header, UNGU_MUD, 6)
    stat_icon = Label(text='📊', font_size=dp(16), size_hint_x=None, width=dp(30))
    stat_judul = Label(text='Statistik Penggunaan', font_size=dp(14), bold=True, color=UNGU, 
                       size_hint_x=1, halign='left', valign='middle')
    stat_judul.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    stat_header.add_widget(stat_icon)
    stat_header.add_widget(stat_judul)
    stat_box.add_widget(stat_header)
    
    # Grid statistik 2 kolom
    stat_grid = GridLayout(cols=2, spacing=dp(12), padding=[dp(8), dp(8)], size_hint_y=None)
    stat_grid.height = dp(120)
    
    stat_items = [
        ('Total Jadwal Tetap', len(dm.booking_df[dm.booking_df['tipe'] == 'tetap']) if not dm.booking_df.empty else 0),
        ('Ruang Terpakai', stat['ruang_terpakai']),
        ('Rombel Aktif', stat['rombel_aktif']),
        ('Booking Batal', stat['total_batal']),
        ('Kelas Selesai', stat['total_selesai']),
    ]
    
    for label, nilai in stat_items:
        stat_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        stat_row.add_widget(Label(text=label, font_size=dp(12), color=ABU, halign='left', 
                                  size_hint_x=0.6, valign='middle'))
        stat_row.add_widget(Label(text=str(nilai), font_size=dp(13), bold=True, color=GELAP, 
                                  halign='right', size_hint_x=0.4, valign='middle'))
        stat_grid.add_widget(stat_row)
    
    stat_box.add_widget(stat_grid)
    info_container.add_widget(stat_box)
    
    # ==================== INFORMASI SISTEM ====================
    sistem_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
    sistem_box.height = dp(130)
    
    # Header sistem dengan background
    sistem_header = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
    bg_round(sistem_header, UNGU_MUD, 6)
    sistem_icon = Label(text='ℹ️', font_size=dp(16), size_hint_x=None, width=dp(30))
    sistem_judul = Label(text='Informasi Sistem', font_size=dp(14), bold=True, color=UNGU, 
                         size_hint_x=1, halign='left', valign='middle')
    sistem_judul.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    sistem_header.add_widget(sistem_icon)
    sistem_header.add_widget(sistem_judul)
    sistem_box.add_widget(sistem_header)
    
    # Container untuk items sistem
    sistem_items_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
    sistem_items_container.height = dp(80)
    
    sistem_items = [
        ('Jam Operasional', f'Senin - Kamis, {JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI:02d}:00'),
        ('Durasi per SKS', '1 SKS = 50 menit'),
        ('Mekanisme', 'Jadwal tetap berwarna MERAH'),
    ]
    
    for label, nilai in sistem_items:
        sistem_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(8))
        lbl_label = Label(text=f'• {label}', font_size=dp(12), color=ABU, halign='left', 
                          size_hint_x=0.35, valign='middle')
        lbl_label.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
        lbl_nilai = Label(text=nilai, font_size=dp(12), color=GELAP, halign='left', 
                          size_hint_x=0.65, valign='middle')
        lbl_nilai.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
        sistem_row.add_widget(lbl_label)
        sistem_row.add_widget(lbl_nilai)
        sistem_items_container.add_widget(sistem_row)
    
    sistem_box.add_widget(sistem_items_container)
    info_container.add_widget(sistem_box)
    
    # ==================== FITUR UNGGULAN ====================
    fitur_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
    fitur_box.height = dp(150)
    
    # Header fitur dengan background
    fitur_header = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
    bg_round(fitur_header, UNGU_MUD, 6)
    fitur_icon = Label(text='⚙️', font_size=dp(16), size_hint_x=None, width=dp(30))
    fitur_judul = Label(text='Fitur Unggulan', font_size=dp(14), bold=True, color=UNGU, 
                        size_hint_x=1, halign='left', valign='middle')
    fitur_judul.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    fitur_header.add_widget(fitur_icon)
    fitur_header.add_widget(fitur_judul)
    fitur_box.add_widget(fitur_header)
    
    # Container untuk fitur items
    fitur_items_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
    fitur_items_container.height = dp(100)
    
    fitur_items = [
        '✓ Semua data di CSV otomatis menjadi jadwal tetap (MERAH)',
        '✓ Booking baru masuk sebagai antrean (UNGU/ORANGE)',
        '✓ Grid jadwal visual per jam dengan warna berbeda',
        '✓ Riwayat booking lengkap',
        '✓ Jadwal tetap tidak bisa dibatalkan'
    ]
    
    for item in fitur_items:
        lbl = Label(text=item, font_size=dp(11), color=GELAP, halign='left', 
                    size_hint_y=None, height=dp(18))
        lbl.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
        fitur_items_container.add_widget(lbl)
    
    fitur_box.add_widget(fitur_items_container)
    info_container.add_widget(fitur_box)
    
    # ==================== PENGEMBANG ====================
    dev_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
    dev_box.height = dp(130)
    
    # Header pengembang dengan background
    dev_header = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
    bg_round(dev_header, UNGU_MUD, 6)
    dev_icon = Label(text='👨‍💻', font_size=dp(16), size_hint_x=None, width=dp(30))
    dev_judul = Label(text='Pengembang', font_size=dp(14), bold=True, color=UNGU, 
                      size_hint_x=1, halign='left', valign='middle')
    dev_judul.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    dev_header.add_widget(dev_icon)
    dev_header.add_widget(dev_judul)
    dev_box.add_widget(dev_header)
    
    # Container untuk items pengembang
    dev_items_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
    dev_items_container.height = dp(80)
    
    dev_items = [
        '• Program Studi Sains Data',
        '• Fakultas Matematika dan Ilmu Pengetahuan Alam',
        '• Universitas Negeri Surabaya'
    ]
    
    for item in dev_items:
        lbl = Label(text=item, font_size=dp(12), color=GELAP, halign='left', 
                    size_hint_y=None, height=dp(22))
        lbl.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
        dev_items_container.add_widget(lbl)
    
    dev_box.add_widget(dev_items_container)
    info_container.add_widget(dev_box)
    
    # ==================== VERSI ====================
    versi_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
    versi_box.height = dp(40)
    
    # Garis pemisah sebelum versi
    separator = BoxLayout(size_hint_y=None, height=dp(1))
    bg_rect(separator, ABU_MD)
    versi_box.add_widget(separator)
    
    versi_label = Label(text='Versi 3.0.0 | Auto Convert to MERAH | © 2024', font_size=dp(10), color=ABU, 
                        halign='center', size_hint_y=None, height=dp(30))
    versi_label.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
    versi_box.add_widget(versi_label)
    info_container.add_widget(versi_box)
    
    sv.add_widget(info_container)
    content.add_widget(sv)
    
    # Tombol tutup
    btn_tutup = tombol('Tutup', HIJAU, lambda *a: None, h=dp(42), r=8, fs=dp(14))
    
    # Buat popup
    pop = Popup(title='', content=content, size_hint=(0.55, 0.70),
                auto_dismiss=True, separator_height=0)
    
    # Update fungsi tombol
    btn_tutup.bind(on_press=pop.dismiss)
    content.add_widget(btn_tutup)
    
    pop.open()

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

        top = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(20), dp(12)], spacing=dp(10))
        bg_rect(top, NAVY)
        top.add_widget(Label(text='Sistem Informasi Booking Ruang Kelas (Queue Dinamis)\nUniversitas Negeri Surabaya  -  Prodi Sains Data', 
                            color=PUTIH, font_size=dp(15), bold=True, halign='left', valign='middle'))
        root.add_widget(top)

        main = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(18))

        wc = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(130), padding=dp(20), spacing=dp(8))
        bg_round(wc, PUTIH, 14)
        wc.add_widget(Label(text='Selamat Datang!', font_size=dp(22), bold=True, color=NAVY, halign='center', size_hint_y=None, height=dp(36)))
        wc.add_widget(Label(text='Sistem Booking Ruang Kelas Berbasis Queue Terurut Dinamis\nFakultas Matematika dan Ilmu Pengetahuan Alam - UNESA\n✨ Semua data di CSV otomatis menjadi JADWAL TETAP (WARNA MERAH) ✨', 
                           font_size=dp(13), color=ABU, halign='center', size_hint_y=None, height=dp(65)))
        main.add_widget(wc)

        menu_grid = GridLayout(cols=4, spacing=dp(16), size_hint_y=None, height=dp(240))
        menus = [
            (ICON_FORM, '📝', 'Form Booking', 'Booking ruang kelas\nuntuk perkuliahan', UNGU, 'form'),
            (ICON_GRID, '📊', 'Grid Jadwal', 'Lihat jadwal ruang\nsecara visual per jam', HIJAU, 'grid'),
            (ICON_RIWAYAT, '📜', 'Riwayat', 'Lihat semua riwayat\npeminjaman ruang', BIRU, 'history'),
            (ICON_INFO, 'ℹ️', 'Informasi', 'Lihat informasi\nsistem aplikasi', ORANGE, 'info'),
        ]
        
        for icon_path, icon_text, judul, desc, warna, screen in menus:
            card = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))
            bg_round(card, PUTIH, 14)
            if os.path.exists(icon_path):
                card.add_widget(Image(source=icon_path, size_hint_y=None, height=dp(70), allow_stretch=True))
            else:
                card.add_widget(Label(text=icon_text, font_size=dp(40), size_hint_y=None, height=dp(70)))
            
            card.add_widget(Label(text=judul, font_size=dp(15), bold=True, color=NAVY, halign='center', size_hint_y=None, height=dp(28)))
            card.add_widget(Label(text=desc, font_size=dp(11), color=ABU, halign='center', size_hint_y=None, height=dp(36)))
            
            if screen == 'info':
                b = tombol('Lihat Info', warna, lambda *a: popup_info_aplikasi(self.dm), h=dp(36), r=8, fs=dp(12))
            else:
                b = tombol('Buka', warna, lambda *a, s=screen: setattr(self.manager, 'current', s), h=dp(36), r=8, fs=dp(12))
            card.add_widget(b)
            menu_grid.add_widget(card)
        main.add_widget(menu_grid)

        info = BoxLayout(size_hint_y=None, height=dp(72), padding=dp(20), spacing=dp(6))
        bg_round(info, NAVY_MED, 10)
        info.add_widget(Label(text=f'⚠️ PERHATIAN: Semua data yang sudah ada di data_booking.csv otomatis menjadi JADWAL TETAP (WARNA MERAH)\nJam Operasional: Senin - Kamis  |  {JAM_OPERASIONAL_MULAI:02d}:00 - {JAM_OPERASIONAL_SELESAI:02d}:00', 
                             font_size=dp(11), color=PUTIH, halign='center'))
        main.add_widget(info)

        root.add_widget(main)
        self.add_widget(root)

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

        topbar(
            root,
            'Form Booking Ruang',
            self.manager,
            [('Home', UNGU, 'home'), ('Grid', HIJAU, 'grid'), ('Riwayat', BIRU, 'history')]
        )

        sv = ScrollView()
        body = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(14),
            size_hint_y=None
        )
        body.bind(minimum_height=body.setter('height'))

        body.add_widget(Label(
            text='Peminjaman Ruang Kelas',
            font_size=dp(20),
            bold=True,
            color=NAVY,
            size_hint_y=None,
            height=dp(36),
            halign='left'
        ))

        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=dp(20),
            spacing=dp(12)
        )
        card.bind(minimum_height=card.setter('height'))
        bg_round(card, PUTIH, 14)

        # Peringatan tentang jadwal tetap
        warning_box = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8))
        bg_round(warning_box, ORANGE_MUD, 6)
        warning_box.add_widget(Label(text='⚠️ PERINGATAN: Semua jadwal yang sudah ada di CSV adalah JADWAL TETAP (MERAH) dan tidak dapat diubah! Booking baru akan masuk antrean.', 
                                     font_size=dp(11), color=MERAH, bold=True, halign='center', valign='middle'))
        card.add_widget(warning_box)

        # Rombel
        card.add_widget(lbl_field('Rombel / Kelas'))
        self.sp_rombel = sp_ui(self.dm.get_rombel_list(), 'Pilih Rombel')
        card.add_widget(self.sp_rombel)

        # Hari
        card.add_widget(lbl_field('Hari'))
        self.sp_hari = sp_ui(list(HARI_LIST), 'Pilih Hari')
        card.add_widget(self.sp_hari)

        # Durasi
        card.add_widget(lbl_field('Durasi Penggunaan'))
        self.sp_durasi = sp_ui(list(DURASI_CONFIG.keys()), 'Pilih Durasi')
        card.add_widget(self.sp_durasi)

        # MK
        card.add_widget(lbl_field('Mata Kuliah (opsional)'))
        self.ti_mk = TextInput(
            hint_text='Contoh: Struktur Data Dan Algoritma',
            size_hint_y=None,
            height=dp(44),
            font_size=dp(14),
            multiline=False,
            background_color=ABU_MD
        )
        card.add_widget(self.ti_mk)

        # Metode
        card.add_widget(lbl_field('Metode Pencarian / Filter Rekomendasi (Opsional)'))
        self.sp_metode = sp_ui(
            ['Cari Berdasarkan Jam', 'Cari Berdasarkan Ruangan'],
            'Cari Berdasarkan Jam'
        )
        self.sp_metode.bind(text=self._ganti_input_metode)
        card.add_widget(self.sp_metode)

        # Dinamis input
        self.container_dinamis = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(75),
            spacing=dp(2)
        )
        card.add_widget(self.container_dinamis)
        self._ganti_input_metode(None, 'Cari Berdasarkan Jam')

        # tombol cari
        self.btn_cari = tombol(
            'CARI RUANG KOSONG / ANTREAN',
            UNGU,
            self._cari,
            h=dp(50)
        )
        card.add_widget(self.btn_cari)

        # label status
        self.lbl_q = Label(
            text='',
            font_size=dp(12),
            color=UNGU,
            size_hint_y=None,
            height=dp(22),
            halign='center'
        )
        card.add_widget(self.lbl_q)

        body.add_widget(card)
        sv.add_widget(body)
        root.add_widget(sv)
        self.add_widget(root)

    def _ganti_input_metode(self, spinner, value):
        self.container_dinamis.clear_widgets()

        if value == 'Cari Berdasarkan Jam':
            self.container_dinamis.add_widget(
                lbl_field('Cari Jam Mulai (HH:MM contoh: 08:00)')
            )

            self.ti_jam = TextInput(
                text='08:00',
                hint_text='07:00 / 09:30',
                size_hint_y=None,
                height=dp(44),
                font_size=dp(14),
                multiline=False,
                background_color=ABU_MD
            )
            self.container_dinamis.add_widget(self.ti_jam)

        else:
            self.container_dinamis.add_widget(lbl_field('Cari Ruangan Target'))

            ruang_list = self.dm.get_ruang_list()
            default = ruang_list[0] if ruang_list else 'Pilih Ruang'

            self.sp_ruang_target = sp_ui(ruang_list, default)
            self.container_dinamis.add_widget(self.sp_ruang_target)

    def _cari(self, *a):
        r = self.sp_rombel.text
        h = self.sp_hari.text
        d = self.sp_durasi.text
        mk = self.ti_mk.text.strip()
        mode = self.sp_metode.text

        if 'Pilih' in r or 'Pilih' in h or 'Pilih' in d:
            notif('Lengkapi Rombel, Hari, dan Durasi!', MERAH)
            return

        dur = DURASI_CONFIG[d]
        jm_val = ""
        ruang_target_val = ""

        if mode == 'Cari Berdasarkan Jam':
            jm_val = self.ti_jam.text.strip()

            if not jm_val or not validasi_jam_operasional(jm_val):
                notif('Format jam salah / di luar jam operasional!', MERAH)
                return

            waktu_selesai = menit_ke_jam(jm_val, dur)

            if waktu_selesai is None or parse_jam(waktu_selesai) > time(JAM_OPERASIONAL_SELESAI, 0):
                notif('Durasi terlalu panjang!', MERAH)
                return

        else:
            ruang_target_val = self.sp_ruang_target.text

            if 'Pilih' in ruang_target_val or not ruang_target_val:
                notif('Ruangan target tidak valid!', MERAH)
                return

        self.lbl_q.text = 'Mengecek ketersediaan...'

        Clock.schedule_once(
            lambda *a: self._buka_rekomendasi(
                mode, r, h, jm_val, dur, ruang_target_val, mk
            ),
            0.15
        )

    def _buka_rekomendasi(self, mode, r, h, jm, dur, ruang_target, mk):
        self.lbl_q.text = ''

        popup_pilih_slot_dinamis(
            self.dm,
            mode,
            r,
            h,
            jm,
            dur,
            ruang_target,
            mk,
            lambda: setattr(self.manager, 'current', 'grid')
        )

    def on_enter(self):
        self.dm._load_booking()

# ==============================================================
# SCREEN 2: GRID JADWAL
# ==============================================================
class GridScreen(Screen):
    def __init__(self, dm, **kw):
        super().__init__(**kw)
        self.dm = dm
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        bg_rect(root, BG)
        topbar(root, 'Grid Ruang Kelas (Queue Antrean)', self.manager, [('Home', UNGU, 'home'), ('Form', HIJAU, 'form'), ('Riwayat', BIRU, 'history')])

        fbar = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(16), dp(8)], spacing=dp(10))
        bg_rect(fbar, NAVY_MED)
        fbar.add_widget(Label(text='Hari:', size_hint=(None, 1), width=dp(36), color=PUTIH, font_size=dp(13), bold=True))
        
        self.sp_hari = Spinner(text='Senin', values=list(HARI_LIST), size_hint=(None, None), width=dp(100), height=dp(36), 
                              color=PUTIH, font_size=dp(13), bold=True)
        bg_round(self.sp_hari, UNGU, 8)
        self.sp_hari.bind(text=self._refresh)
        fbar.add_widget(self.sp_hari)

        legend_items = [
            (MERAH, 'Jadwal Tetap (Data CSV)', '🔴'),
            (HIJAU, 'Tersedia', '🟢'),
            (UNGU, 'Booking Baru (Queue)', '🟣'),
            (ORANGE, 'Waiting List', '🟠')
        ]
        
        for wc, tl, icon in legend_items:
            leg_box = BoxLayout(size_hint=(None, None), width=dp(150), height=dp(30), spacing=dp(4))
            color_box = BoxLayout(size_hint=(None, None), width=dp(20), height=dp(20))
            bg_round(color_box, wc, 3)
            leg_box.add_widget(color_box)
            leg_box.add_widget(Label(text=tl, color=PUTIH, font_size=dp(10), bold=True, halign='left', size_hint_x=1))
            fbar.add_widget(leg_box)

        self.lbl_stat = Label(text='', font_size=dp(11), color=PUTIH, halign='right')
        fbar.add_widget(self.lbl_stat)
        
        root.add_widget(fbar)
        self.sv = ScrollView()
        self.gw = BoxLayout(orientation='vertical', spacing=dp(2))
        self.sv.add_widget(self.gw)
        root.add_widget(self.sv)
        self.add_widget(root)

    def on_enter(self): 
        self._refresh()

    def _refresh(self, *a):
        try:
            self.gw.clear_widgets()
            self.dm._load_booking()
            hari = self.sp_hari.text
            ruang_list = self.dm.get_ruang_list()
            if not ruang_list: 
                return
                
            cols = len(ruang_list) + 1
            
            h_row = GridLayout(cols=cols, size_hint_y=None, height=dp(48), spacing=dp(2))
            bg_rect(h_row, NAVY)
            h_row.add_widget(Label(text='JAM\n(1 SKS)', color=PUTIH, font_size=dp(11), bold=True, halign='center'))
            for r in ruang_list: 
                h_row.add_widget(Label(text=r, color=PUTIH, font_size=dp(10.5), bold=True, halign='center'))
            self.gw.add_widget(h_row)

            sv_in = ScrollView()
            rows = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
            rows.bind(minimum_height=rows.setter('height'))

            for i, (jm, js) in enumerate(JAM_SLOT_GRID):
                row_bg = (0.97, 0.97, 1.0, 1) if i % 2 == 0 else PUTIH
                baris = GridLayout(cols=cols, size_hint_y=None, height=dp(60), spacing=dp(2))
                bg_rect(baris, row_bg)
                baris.add_widget(Label(text=f'{jm}\n{js}', font_size=dp(11), color=NAVY, bold=True, halign='center'))

                for ruang in ruang_list:
                    all_queue = self.dm.dapatkan_semua_antrian_slot(hari, jm, js, ruang)
                    
                    if all_queue:
                        # Cek apakah ada jadwal tetap di slot ini
                        is_tetap = any(str(x.get('tipe', '')).lower().strip() == 'tetap' for x in all_queue)
                        
                        if is_tetap:
                            # 🔴 WARNA MERAH untuk jadwal tetap (data dari CSV)
                            teks = 'JADWAL TETAP'
                            w_bg = MERAH
                            # Tampilkan info rombel jika ada
                            if all_queue:
                                rombel_tetap = all_queue[0].get('rombel', '')
                                mk_tetap = all_queue[0].get('mata_kuliah', '')
                                if mk_tetap and str(mk_tetap).lower() not in ('nan', '', 'none'):
                                    teks = f'{rombel_tetap}\n{mk_tetap}'
                                else:
                                    teks = f'{rombel_tetap}'
                        else:
                            # Ambil data booking pertama
                            antrian_ke = all_queue[0].get('antrian_ke', 1)
                            if antrian_ke == 1:
                                # 🟣 WARNA UNGU untuk booking utama
                                w_bg = UNGU
                                kelas = all_queue[0].get("rombel", "-")
                                mk_text = all_queue[0].get("mata_kuliah", "-")
                                if mk_text and str(mk_text).lower() not in ('nan', '', 'none'):
                                    teks = f'{kelas}\n{mk_text}'
                                else:
                                    teks = f'{kelas}'
                                
                                if len(all_queue) > 1:
                                    teks += f'\n(+{len(all_queue)-1})'
                            else:
                                # 🟠 WARNA ORANGE untuk waiting list
                                w_bg = ORANGE
                                kelas = all_queue[0].get("rombel", "-")
                                teks = f'{kelas}\n(Antrean ke-{antrian_ke})'
                    else:
                        # 🟢 WARNA HIJAU untuk slot tersedia
                        teks = 'Tersedia'
                        w_bg = HIJAU

                    sel = Button(text=teks, font_size=dp(10), background_normal='', background_color=(0,0,0,0), 
                                color=PUTIH, size_hint_y=None, height=dp(60), bold=True, halign='center')
                    
                    sel.canvas.before.clear()
                    
                    with sel.canvas.before:
                        Color(*w_bg)
                        rr = RoundedRectangle(pos=sel.pos, size=sel.size, radius=[5])
                    
                    def update_rect(instance, value, rect=rr):
                        rect.pos = instance.pos
                        rect.size = instance.size
                    
                    sel.bind(pos=update_rect, size=update_rect)
                    
                    sel.hari, sel.jm, sel.js, sel.ruang, sel.all_queue = hari, jm, js, ruang, all_queue
                    sel.bind(on_press=self._klik_slot_grid)
                    baris.add_widget(sel)
                rows.add_widget(baris)

            sv_in.add_widget(rows)
            self.gw.add_widget(sv_in)
            
            stat = self.dm.get_statistik()
            jml_tetap = len(self.dm.booking_df[self.dm.booking_df['tipe'] == 'tetap']) if not self.dm.booking_df.empty else 0
            self.lbl_stat.text = f'Jadwal Tetap: {jml_tetap} | Total Booking: {stat["total_booking"]} | Ruang Terpakai: {stat["ruang_terpakai"]}'
            
        except Exception as e:
            print(f"Error refreshing grid: {e}")
            import traceback
            traceback.print_exc()

    def _klik_slot_grid(self, sel):
        hari, jm, js, ruang, all_queue = sel.hari, sel.jm, sel.js, sel.ruang, sel.all_queue
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        bg_round(box, PUTIH, 12)

        if all_queue:
            is_tetap = any(str(x.get('tipe', '')) == 'tetap' for x in all_queue)
            
            if is_tetap:
                txt_detail = f"🔴 JADWAL TETAP (Dari Data CSV)\n\n"
                txt_detail += f" Ruangan: {ruang}\n"
                txt_detail += f" Waktu: {hari}, {jm} - {js}\n\n"
                txt_detail += f"===============================\n\n"
                for idx, item in enumerate(all_queue):
                    if item.get('tipe') == 'tetap':
                        txt_detail += f" Kelas: {item['rombel']}\n"
                        mk_value = item.get('mata_kuliah', '-')
                        if mk_value == 'nan' or mk_value == '' or mk_value is None:
                            mk_value = '-'
                        txt_detail += f" Mata Kuliah: {mk_value}\n"
                        break
                txt_detail += "\n"
                txt_detail += "⚠️ Slot ini merupakan JADWAL TETAP dari data CSV.\n"
                txt_detail += "Tidak dapat diubah, dibatalkan, atau ditimpa booking baru."
                
                lbl_detail = Label(text=txt_detail, font_size=dp(13), color=GELAP, halign='left', valign='top', markup=False)
                lbl_detail.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
                box.add_widget(lbl_detail)
                pop = Popup(title='Detail Jadwal Tetap (CSV)', content=box, size_hint=(0.48, 0.48), auto_dismiss=False)
                box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(38)))
                pop.open()
            else:
                txt_detail = f" Ruangan: {ruang}\n"
                txt_detail += f" Waktu: {hari}, {jm} - {js}\n\n"
                
                for idx, item in enumerate(all_queue):
                    if item['antrian_ke'] == 1:
                        tag = " [UTAMA]"
                    else:
                        tag = f" [ANTREAN KE-{item['antrian_ke']}]"
                    
                    txt_detail += f"{tag}\n"
                    txt_detail += f"    Kelas: {item['rombel']}\n"
                    
                    mk_value = item.get('mata_kuliah', '-')
                    if mk_value == 'nan' or mk_value == '' or mk_value is None:
                        mk_value = '-'
                    txt_detail += f"    MK: {mk_value}\n"
                    
                    status = item.get('status', 'aktif')
                    if status == 'aktif':
                        txt_detail += f"    Status: Aktif\n"
                    else:
                        txt_detail += f"    Status: {status}\n"
                    txt_detail += "\n"
                
                lbl_detail = Label(text=txt_detail, font_size=dp(12), color=GELAP, halign='left', valign='top', markup=False)
                lbl_detail.bind(size=lambda w, v: setattr(w, 'text_size', (w.width, None)))
                box.add_widget(lbl_detail)
                
                pop = Popup(title='Detail Manajemen Queue', content=box, size_hint=(0.48, 0.62), auto_dismiss=False)
                
                if all_queue and all_queue[0].get('tipe') == 'booking' and all_queue[0].get('status') == 'aktif':
                    def batalkan_utama():
                        def do():
                            self.dm.batalkan(all_queue[0]['id_booking'])
                            self._refresh()
                            notif('✅ Booking Utama Keluar! Antrean berikutnya bergeser naik.', KUNING)
                        popup_konfirmasi('Batalkan Utama?', f'Keluarkan kelas {all_queue[0]["rombel"]} dari slot ini?', do)
                    box.add_widget(tombol('🗑️ Batalkan Kelas Utama (Dequeue)', MERAH, batalkan_utama, h=dp(40)))
                
                if all_queue and all_queue[0].get('tipe') == 'booking' and all_queue[0].get('status') == 'aktif':
                    def selesai_utama():
                        self.dm.kelas_selesai(all_queue[0]['id_booking'])
                        self._refresh()
                        notif('✅ Kelas selesai! Antrean otomatis diperbarui.', HIJAU)
                    box.add_widget(tombol('✓ Tandai Kelas Selesai', HIJAU, selesai_utama, h=dp(40)))
                
                box.add_widget(tombol('Tutup', ABU, lambda *a: pop.dismiss(), h=dp(38)))
                pop.open()
        else:
            notif("📝 Gunakan menu utama Form Booking untuk pendaftaran terurut!", UNGU)

# ==============================================================
# SCREEN 3: RIWAYAT TRANSAKSI
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
        topbar(root, 'Riwayat Booking', self.manager, [('Home', UNGU, 'home'), ('Form', HIJAU, 'form'), ('Grid', BIRU, 'grid')])

        fbar = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(16), dp(8)], spacing=dp(10))
        bg_rect(fbar, NAVY_MED)
        fbar.add_widget(Label(text='Filter:', size_hint=(None, 1), width=dp(44), color=PUTIH, font_size=dp(13), bold=True))
        
        self.sp_filter = sp_ui(['Semua', 'aktif', 'batal', 'Selesai', 'tetap'], 'Semua')
        self.sp_filter.bind(text=self._refresh)
        fbar.add_widget(self.sp_filter)
        fbar.add_widget(Label(size_hint=(1, 1)))

        btn_reset = tombol('Reset Jadwal', MERAH, self._reset_jadwal, h=dp(34), r=7, fs=dp(12))
        btn_reset.size_hint = (None, None)
        btn_reset.width = dp(110)
        fbar.add_widget(btn_reset)

        # HEADER TABLE
        th = BoxLayout(size_hint_y=None, height=dp(42), padding=[dp(8), dp(8)], spacing=dp(4))
        bg_round(th, NAVY, 6)
        for teks, sx in [('ID', 0.08), ('Rombel', 0.09), ('Hari', 0.07), 
                        ('Mulai', 0.07), ('Selesai', 0.07), ('Ruang', 0.08), 
                        ('Tipe', 0.10), ('Waktu Booking', 0.12),
                        ('Status', 0.09), ('Aksi', 0.19)]:
            th.add_widget(Label(text=teks, color=PUTIH, font_size=dp(11), bold=True, size_hint_x=sx, halign='center'))

        pagination_bar = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(10), dp(5)], spacing=dp(10))
        bg_rect(pagination_bar, ABU_MD)
        
        self.btn_prev = tombol('◀ Sebelumnya', NAVY, self._prev_page, h=dp(36), r=6, fs=dp(11))
        self.btn_prev.size_hint = (None, None)
        self.btn_prev.width = dp(110)
        self.lbl_page = Label(text='Halaman 1', color=NAVY, font_size=dp(12), bold=True, size_hint=(None, None), width=dp(100))
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
            if self.dm.reset_jadwal(): 
                notif('Jadwal berhasil dikembalikan semula!', HIJAU)
            self._refresh()
        popup_konfirmasi('Reset Jadwal', 'Semua log booking baru akan dibersihkan. Lanjutkan?', do, MERAH)

    def on_enter(self):
        self.dm._load_booking()
        self.current_page = 0
        self._refresh()

    def _refresh(self, *a):
        try:
            self.content.clear_widgets()
            f = self.sp_filter.text
            
            if self.dm.booking_df is None or self.dm.booking_df.empty:
                self.total_items = 0
                self.lbl_page.text = 'Halaman 1 / 1'
                self.btn_prev.disabled = True
                self.btn_next.disabled = True
                return
                
            df_full = self.dm.booking_df.copy()
            if df_full.empty:
                self.total_items = 0
                self.lbl_page.text = 'Halaman 1 / 1'
                self.btn_prev.disabled = True
                self.btn_next.disabled = True
                return
            
            # Filter berdasarkan tipe
            if f == 'tetap':
                df_full = df_full[df_full['tipe'] == 'tetap']
            elif f == 'aktif':
                df_full = df_full[df_full['status'] == 'aktif']
            elif f == 'batal':
                df_full = df_full[df_full['status'] == 'batal']
            elif f == 'Selesai':
                df_full = df_full[df_full['kelas_selesai'] == 'Selesai']
            
            # Urutkan berdasarkan waktu booking
            df_full = df_full.sort_values('waktu_booking', ascending=False)
            
            self.total_items = len(df_full)
            start = self.current_page * self.items_per_page
            end = start + self.items_per_page
            df = df_full.iloc[start:end]
            
            total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
            self.lbl_page.text = f'Halaman {self.current_page + 1} / {total_pages}'
            self.btn_prev.disabled = (self.current_page == 0)
            self.btn_next.disabled = (self.current_page >= total_pages - 1)

            if df.empty: 
                return

            for _, row in df.iterrows():
                is_tetap = row['tipe'] == 'tetap'
                selesai = str(row.get('kelas_selesai', '')) == 'Selesai'
                aktif = row['status'] == 'aktif'
                
                if is_tetap:
                    row_bg = (1.0, 0.9, 0.9, 1)  # Merah muda untuk jadwal tetap
                elif selesai:
                    row_bg = (0.93, 0.98, 0.93, 1)
                elif not aktif:
                    row_bg = (0.98, 0.95, 0.95, 1)
                else:
                    row_bg = (0.97, 0.97, 1.0, 1)
                
                item = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(8), dp(6)], spacing=dp(4))
                bg_round(item, row_bg, 6)

                # Ambil waktu_booking
                waktu_booking = row.get('waktu_booking', '')
                if pd.isna(waktu_booking) or waktu_booking == '' or waktu_booking == 'nan':
                    waktu_booking = '-'
                else:
                    try:
                        if ' ' in waktu_booking:
                            waktu_booking = waktu_booking.split()[1][:5]
                    except:
                        pass
                
                if is_tetap:
                    st = 'JADWAL TETAP'
                    tipe_text = '🔴 Tetap'
                else:
                    st = 'Selesai' if selesai else ('Aktif' if aktif else 'Batal')
                    tipe_text = '📝 Booking'

                for val, sx in [(row['id_booking'], 0.08), (row['rombel'], 0.09), (row['hari'], 0.07),
                                (str(row['jam_mulai']), 0.07), (str(row['jam_selesai']), 0.07),
                                (row['ruang'], 0.08), (tipe_text, 0.10), (waktu_booking, 0.12),
                                (st, 0.09)]:
                    lbl = Label(text=val, color=GELAP if not is_tetap else MERAH, 
                               font_size=dp(11), size_hint_x=sx, halign='center', bold=is_tetap)
                    item.add_widget(lbl)

                btn_box = BoxLayout(size_hint_x=0.19, spacing=dp(4))
                id_b = row['id_booking']

                if not is_tetap and aktif and not selesai:
                    btn_s = Button(text='Selesai', font_size=dp(10), bold=True, size_hint=(0.5, 1), color=PUTIH)
                    bg_round(btn_s, HIJAU, 5)
                    def mk_sel(id_booking):
                        return lambda *a: [self.dm.kelas_selesai(id_booking), notif('Kelas selesai!', HIJAU), self._refresh()]
                    btn_s.bind(on_press=mk_sel(id_b))
                    btn_box.add_widget(btn_s)

                if not is_tetap and aktif:
                    btn_b = Button(text='Batal', font_size=dp(10), bold=True, size_hint=(0.5, 1), color=PUTIH)
                    bg_round(btn_b, MERAH, 5)
                    def mk_batal(id_booking):
                        def cb(*a):
                            def do(): 
                                try:
                                    self.dm.batalkan(id_booking)
                                    notif('Booking dibatalkan', MERAH)
                                    self._refresh()
                                except ValueError as e:
                                    notif(str(e), MERAH)
                            popup_konfirmasi('Batalkan?', f'Hapus booking {id_booking}?', do, MERAH)
                        return cb
                    btn_b.bind(on_press=mk_batal(id_b))
                    btn_box.add_widget(btn_b)
                elif is_tetap:
                    lbl_info = Label(text='Tidak bisa diubah', font_size=dp(9), color=ABU, size_hint=(1, 1), halign='center')
                    btn_box.add_widget(lbl_info)

                item.add_widget(btn_box)
                self.content.add_widget(item)
        except Exception as e:
            print(f"Error history: {e}")
            import traceback
            traceback.print_exc()

# ==============================================================
# APP ENTRY POINT
# ==============================================================
class BookingApp(App):
    def build(self):
        Window.size = (1220, 730)
        Window.clearcolor = BG
        try:
            dm = DataManager()
            queue = BookingQueue()
            self.sm = ScreenManager(transition=FadeTransition(duration=0.18))
            self.sm.add_widget(HomeScreen(dm=dm, name='home'))
            self.sm.add_widget(FormScreen(dm=dm, queue=queue, name='form'))
            self.sm.add_widget(GridScreen(dm=dm, name='grid'))
            self.sm.add_widget(HistoryScreen(dm=dm, name='history'))
            self.sm.current = 'home'
            return self.sm
        except Exception as e:
            root = BoxLayout()
            root.add_widget(Label(text=f'Fatal Error: {str(e)}', color=MERAH))
            return root

if __name__ == '__main__':
    BookingApp().run()