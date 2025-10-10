#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Araç Bakım Kayıtları Yönetim Sistemi - Modern GUI
PyQt6 ile geliştirilmiş modern arayüz
"""

import sys
import sqlite3
import pandas as pd
import os
import requests  # Güncelleme sistemi için
import json      # JSON işlemleri için
import shutil    # Dosya kopyalama için
import subprocess # Sistem komutları için
import base64    # GitHub API için base64 encoding
from datetime import datetime
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtCore import QTextStream
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit, QMessageBox,
    QTabWidget, QGroupBox, QFrame, QSplitter, QHeaderView, QAbstractItemView,
    QFileDialog, QProgressBar, QStatusBar, QMenuBar, QMenu, QDialog,
    QDialogButtonBox, QFormLayout, QCheckBox, QScrollArea, QToolButton,
    QRadioButton
)
from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal, QThread, QSize, QSettings, QDateTime
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QAction, QPixmap

# ---------------------- Modern Renk Paleti ----------------------
# Ana renkler
PRIMARY_BG = "#1a1a1a"          # En koyu arka plan
SECONDARY_BG = "#2c2c2c"        # Orta koyu arka plan  
TERTIARY_BG = "#3a3a3a"         # Açık koyu arka plan
ACCENT_BG = "#4a4a4a"           # Vurgu arka planı

# Metin renkleri
PRIMARY_TEXT = "#ffffff"        # Ana metin
SECONDARY_TEXT = "#e0e0e0"      # İkincil metin
MUTED_TEXT = "#b0b0b0"          # Soluk metin

# Vurgu renkleri (koyu tema uyumlu, yumuşak tonlar)
PRIMARY_ACCENT = "#5a6c7d"      # Yumuşak mavi-gri
SUCCESS_ACCENT = "#6b8e6b"      # Yumuşak yeşil-gri
WARNING_ACCENT = "#b8860b"       # Yumuşak altın
ERROR_ACCENT = "#8b5a5a"        # Yumuşak kırmızı-gri
INFO_ACCENT = "#5a7a8a"         # Yumuşak cyan-gri

# Border renkleri (koyu tema uyumlu)
BORDER_PRIMARY = "#404040"      # Ana border
BORDER_ACCENT = "#5a6c7d"       # Vurgu border
BORDER_SUCCESS = "#6b8e6b"     # Başarı border
BORDER_WARNING = "#b8860b"     # Uyarı border
BORDER_ERROR = "#8b5a5a"      # Hata border

# ---------------------- Yardımcı: Excel Sütun Normalizasyonu ----------------------
TURKISH_MAP = {
    'İ': 'I', 'I': 'I', 'ı': 'i', 'Ş': 'S', 'ş': 's', 'Ğ': 'G', 'ğ': 'g',
    'Ü': 'U', 'ü': 'u', 'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c'
}

def normalize_text(value: str) -> str:
    if value is None:
        return ''
    text = str(value).strip()
    # Türkçe karakterleri dönüştür
    text = ''.join(TURKISH_MAP.get(ch, ch) for ch in text)
    # Nokta, boşluk ve alt çizgileri tek biçime getir
    text = text.replace('.', ' ').replace('_', ' ')
    # Birden fazla boşluğu teke indir
    text = ' '.join(text.split())
    return text.upper()

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Excel'den gelen sütun adlarını esnek eşleştirme ile normalize eder."""
    # Desteklenen hedef adlar
    TARGETS = {
        'S.NO': { 'S NO', 'S.NO', 'SNO', 'SAYI', 'SIRA', 'SIRA NO', 'S_NO' },
        'PLAKA': { 'PLAKA', 'ARAC PLAKA', 'ARAC', 'ARAC NO' },
        'BÖLGE': { 'BOLGE', 'BÖLGE', 'BOLGE ADI' },
        'TARİH': { 'TARIH', 'TARİH', 'TARIHİ', 'BAKIM TARIHI' },
        'BAKIM ESNASINDA KM': { 'BAKIM ESNASINDA KM', 'BAKIM KM', 'KM', 'BAKIMDA KM' },
        'BİR SONRAKİ BAKIM KM': { 'BIR SONRAKI BAKIM KM', 'SONRAKI BAKIM KM', 'SONRAKI KM', 'BIR SONRAKI KM' },
        'YAPILAN İŞLEM': { 'YAPILAN ISLEM', 'YAPILAN İŞLEM', 'ISLEM', 'YAPILANLAR', 'YAPILAN' },
        'DİĞER': { 'DIGER', 'DİGER', 'DİĞER', 'NOT', 'NOTLAR', 'ACIKLAMA', 'AÇIKLAMA' },
        'BAKIMI YAPAN': { 'BAKIMI YAPAN', 'BAKIM YAPAN', 'UYGULAYAN', 'TEKNISYEN', 'TEKNISYEN ADI' }
    }
    # Normalize edilmiş ad -> orijinal ad eşlemesi
    normalized_to_original = { normalize_text(c): c for c in df.columns }
    rename_map = {}
    for target, variants in TARGETS.items():
        for variant in variants:
            key = normalize_text(variant)
            if key in normalized_to_original:
                rename_map[normalized_to_original[key]] = target
                break
    # Yeniden adlandır
    return df.rename(columns=rename_map)

def normalize_vehicle_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Araç Excel sütunlarını normalize eder."""
    # Araç sütunları için hedef adlar
    VEHICLE_TARGETS = {
        'ARAC_MAKINE_ADI': { 'ARAC MAKINE ADI', 'ARAC_MAKINE_ADI', 'ARAC MAKINE', 'ARAC ADI', 'MAKINE ADI', 'ARAC TIPI', 'TIP', 'Araç / Makine Adı', 'Araç Makine Adı', 'Araç-Makine Adı' },
        'PLAKA': { 'PLAKA', 'PLAKASI', 'ARAC PLAKA', 'ARAC', 'ARAC NO', 'PLAKA NO' },
        'MAKINE_NO': { 'MAKINE NO', 'MAKINE_NO', 'MAKINE NUMARASI', 'MAKINE NUMARASI', 'MAKINE KODU' },
        'MARKA': { 'MARKA', 'MARKASI', 'ARAC MARKASI', 'MARKA ADI' },
        'MODEL': { 'MODEL', 'ARAC MODELI', 'MODEL ADI' },
        'MODEL_YILI': { 'MODEL YILI', 'MODEL_YILI', 'YIL', 'YAPIM YILI', 'MODEL YILI' },
        'HESAP_ADI': { 'HESAP ADI', 'HESAP_ADI', 'HESAP', 'SAHIBI', 'SAHIP', 'FIRMA', 'SIRKET' },
        'DURUM': { 'DURUM', 'STATUS', 'DURUMU', 'ARIZA DURUMU', 'ARIZA DURUM' }
    }
    # Normalize edilmiş ad -> orijinal ad eşlemesi
    normalized_to_original = { normalize_text(c): c for c in df.columns }
    rename_map = {}
    for target, variants in VEHICLE_TARGETS.items():
        for variant in variants:
            key = normalize_text(variant)
            if key in normalized_to_original:
                rename_map[normalized_to_original[key]] = target
                break
    # Yeniden adlandır
    return df.rename(columns=rename_map)

def parse_km(value):
    """Excel'den gelen KM alanlarını güvenli biçimde sayıya çevirir."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, (int, float)):
            return int(value)
        # string; nokta/virgül/boşluk temizle
        s = str(value).strip().replace(" ", "").replace(".", "").replace(",", "")
        return int(s) if s else None
    except Exception:
        return None

def format_thousands_dot(number: int) -> str:
    """Sayıyı binlik ayıracı nokta olacak şekilde biçimlendirir."""
    try:
        return f"{number:,}".replace(",", ".")
    except Exception:
        return str(number)

def normalize_date_display(value):
    """Tarihi ekranda dd.MM.yyyy göster ve doğru sıralama anahtarı döndür.
    Girdi dd.MM.yyyy veya yyyymmdd olabilir.
    Dönen: (display_str, sort_key_int)
    """
    if value in (None, ""):
        return "-", 99999999
    try:
        s = str(value).strip()
        # yyyymmdd (8 hane, sadece rakam)
        if len(s) == 8 and s.isdigit():
            y, m, d = s[0:4], s[4:6], s[6:8]
            return f"{d}.{m}.{y}", int(f"{y}{m}{d}")
        # dd.MM.yyyy
        if len(s) >= 10 and s[2] == '.' and s[5] == '.':
            d, m, y = s[0:2], s[3:5], s[6:10]
            # doğrulamayı hafifçe yap
            if d.isdigit() and m.isdigit() and y.isdigit():
                return f"{d}.{m}.{y}", int(f"{y}{m}{d}")
        # Fallback: mümkünse pandas ile
        try:
            ts = pd.to_datetime(s, dayfirst=True, errors='coerce')
            if pd.notna(ts):
                return ts.strftime('%d.%m.%Y'), int(ts.strftime('%Y%m%d'))
        except Exception:
            pass
        return s, 99999999
    except Exception:
        return str(value), 99999999

def ensure_ddmmyyyy(value):
    """Excel'den gelen tarih değerini kesin olarak dd.MM.yyyy formatına dönüştürür.
    Geçersizse None döner.
    """
    if value in (None, ""):
        return None
    try:
        s = str(value).strip()
        # Zaten dd.MM.yyyy ise hafif doğrulayıp döndür
        if len(s) >= 10 and len(s) <= 19 and s[2:3] == '.' and s[5:6] == '.':
            d, m, y = s[0:2], s[3:5], s[6:10]
            if d.isdigit() and m.isdigit() and y.isdigit():
                # Tarihi doğrula
                ts = pd.to_datetime(f"{d}.{m}.{y}", dayfirst=True, errors='coerce')
                if pd.notna(ts):
                    return ts.strftime('%d.%m.%Y')
        # 8 haneli yyyymmdd
        if len(s) == 8 and s.isdigit():
            y, m, d = s[0:4], s[4:6], s[6:8]
            ts = pd.to_datetime(f"{d}.{m}.{y}", dayfirst=True, errors='coerce')
            if pd.notna(ts):
                return ts.strftime('%d.%m.%Y')
        # Genel dönüştürme (ör. 2025-10-07, 07/10/2025, Excel datetime)
        ts = pd.to_datetime(value, dayfirst=True, errors='coerce')
        if pd.notna(ts):
            return ts.strftime('%d.%m.%Y')
        return None
    except Exception:
        return None

class DatabaseManager:
    """Veritabanı yönetim sınıfı"""
    
    def __init__(self, db_name="bakim_kayitlari.db"):
        self.db_name = db_name
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat ve tabloyu oluştur"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            cursor = self.conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bakimlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    s_no INTEGER,
                    plaka TEXT NOT NULL,
                    kapi_no TEXT,
                    bolge TEXT,
                    tarih TEXT,
                    bakim_km INTEGER,
                    sonraki_bakim_km INTEGER,
                    yapilan_islem TEXT,
                    diger TEXT,
                    bakim_yapan TEXT,
                    kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Şantiye tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS santiyeler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    santiye_adi TEXT NOT NULL UNIQUE,
                    lokasyon TEXT,
                    sorumlu TEXT,
                    durum TEXT DEFAULT 'Aktif',
                    olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Araclar tablosu - mevcut verileri koru
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS araclar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arac_makine_adi TEXT,
                    plaka TEXT NOT NULL UNIQUE,
                    makine_no TEXT,
                    marka TEXT,
                    model TEXT,
                    model_yili INTEGER,
                    hesap_adi TEXT,
                    santiye_id INTEGER,
                    durum TEXT DEFAULT 'Sağlam',
                    ariza_durumu TEXT DEFAULT 'Aktif',
                    olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (santiye_id) REFERENCES santiyeler (id)
                )
            ''')
            
            # Mevcut verileri yeni şemaya uyarla
            try:
                cursor.execute("PRAGMA table_info(araclar)")
                existing_cols = [r[1] for r in cursor.fetchall()]
                
                # Eski sütunları yeni şemaya uyarla
                if 'cins' in existing_cols:
                    # cins sütununu arac_makine_adi olarak güncelle
                    cursor.execute('UPDATE araclar SET arac_makine_adi = cins WHERE arac_makine_adi IS NULL')
                
                if 'yakit_orani' in existing_cols:
                    # yakit_orani sütununu makine_no olarak güncelle (geçici)
                    cursor.execute('UPDATE araclar SET makine_no = yakit_orani WHERE makine_no IS NULL')
                
                # Durum sütunlarını güncelle
                cursor.execute("UPDATE araclar SET durum = 'Sağlam' WHERE durum IS NULL OR durum = ''")
                cursor.execute("UPDATE araclar SET ariza_durumu = 'Aktif' WHERE ariza_durumu IS NULL OR ariza_durumu = ''")
                
            except Exception as e:
                print(f"Veri uyarlama hatası: {e}")
                pass
            
            # Eski tablolar için eksikse kapi_no sütununu ekle
            try:
                cursor.execute("PRAGMA table_info(bakimlar)")
                cols = [r[1] for r in cursor.fetchall()]
                if 'kapi_no' not in cols:
                    cursor.execute("ALTER TABLE bakimlar ADD COLUMN kapi_no TEXT")
            except Exception:
                pass

            self.conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Veritabanı hatası: {e}")
            return False
    
    def get_all_records(self):
        """Tüm kayıtları getir"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, s_no, plaka, kapi_no, bolge, tarih, bakim_km, sonraki_bakim_km,
                       yapilan_islem, diger, bakim_yapan, kayit_tarihi
                FROM bakimlar
                ORDER BY
                    CASE WHEN tarih IS NULL OR tarih = '' THEN 1 ELSE 0 END ASC,
                    CASE
                        WHEN length(tarih) = 8 AND tarih GLOB '[0-9]*' THEN tarih
                        ELSE substr(tarih, 7, 4) || substr(tarih, 4, 2) || substr(tarih, 1, 2)
                    END ASC,
                    id ASC
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Kayıt getirme hatası: {e}")
            return []
    
    def add_record(self, data):
        """Yeni kayıt ekle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO bakimlar (s_no, plaka, kapi_no, bolge, tarih, bakim_km, sonraki_bakim_km, 
                                    yapilan_islem, diger, bakim_yapan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Kayıt ekleme hatası: {e}")
            return None
    
    def update_record(self, record_id, data):
        """Kayıt güncelle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE bakimlar 
                SET s_no = ?, plaka = ?, kapi_no = ?, bolge = ?, tarih = ?, bakim_km = ?, 
                    sonraki_bakim_km = ?, yapilan_islem = ?, diger = ?, bakim_yapan = ?
                WHERE id = ?
            ''', data + (record_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Kayıt güncelleme hatası: {e}")
            return False
    
    def delete_record(self, record_id):
        """Kayıt sil"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM bakimlar WHERE id = ?", (record_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Kayıt silme hatası: {e}")
            return False
    
    def delete_all(self):
        """Tüm kayıtları sil"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM bakimlar")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Toplu silme hatası: {e}")
            return False
    
    def search_records(self, plaka):
        """Plaka ile ara"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, s_no, plaka, kapi_no, bolge, tarih, bakim_km, sonraki_bakim_km,
                       yapilan_islem, diger, bakim_yapan, kayit_tarihi
                FROM bakimlar
                WHERE plaka LIKE ?
                ORDER BY
                    CASE WHEN tarih IS NULL OR tarih = '' THEN 1 ELSE 0 END ASC,
                    CASE
                        WHEN length(tarih) = 8 AND tarih GLOB '[0-9]*' THEN tarih
                        ELSE substr(tarih, 7, 4) || substr(tarih, 4, 2) || substr(tarih, 1, 2)
                    END ASC,
                    id ASC
            ''', (f'%{plaka}%',))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Arama hatası: {e}")
            return []
    
    def get_vehicle_maintenance_records(self, plaka):
        """Belirli bir araç için bakım kayıtlarını getir"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, s_no, plaka, kapi_no, bolge, tarih, bakim_km, sonraki_bakim_km,
                       yapilan_islem, diger, bakim_yapan, kayit_tarihi
                FROM bakimlar
                WHERE plaka = ?
                ORDER BY
                    CASE WHEN tarih IS NULL OR tarih = '' THEN 1 ELSE 0 END ASC,
                    CASE
                        WHEN length(tarih) = 8 AND tarih GLOB '[0-9]*' THEN tarih
                        ELSE substr(tarih, 7, 4) || substr(tarih, 4, 2) || substr(tarih, 1, 2)
                    END DESC,
                    id DESC
            ''', (plaka,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Araç bakım kayıtları getirme hatası: {e}")
            return []

    def get_statistics(self):
        """İstatistikleri getir"""
        try:
            cursor = self.conn.cursor()
            
            # Toplam kayıt sayısı
            cursor.execute("SELECT COUNT(*) FROM bakimlar")
            toplam_kayit = cursor.fetchone()[0]
            
            # Toplam araç sayısı
            cursor.execute("SELECT COUNT(DISTINCT plaka) FROM bakimlar")
            toplam_arac = cursor.fetchone()[0]
            
            # En çok bakım yapılan araç
            cursor.execute('''
                SELECT plaka, COUNT(*) as bakim_sayisi 
                FROM bakimlar 
                GROUP BY plaka 
                ORDER BY bakim_sayisi DESC 
                LIMIT 1
            ''')
            en_cok_bakim = cursor.fetchone()
            
            # En son bakım tarihi - tarih formatını düzelt
            cursor.execute("""
                SELECT tarih FROM bakimlar 
                WHERE tarih IS NOT NULL AND tarih != ''
                ORDER BY 
                    CASE 
                        WHEN length(tarih) = 8 AND tarih GLOB '[0-9]*' THEN 
                            substr(tarih, 5, 4) || '-' || substr(tarih, 3, 2) || '-' || substr(tarih, 1, 2)
                        WHEN length(tarih) = 10 AND tarih LIKE '%.%.%' THEN
                            substr(tarih, 7, 4) || '-' || substr(tarih, 4, 2) || '-' || substr(tarih, 1, 2)
                        ELSE tarih
                    END DESC
                LIMIT 1
            """)
            son_bakim = cursor.fetchone()
            son_bakim = son_bakim[0] if son_bakim else None
            
            return {
                'toplam_kayit': toplam_kayit,
                'toplam_arac': toplam_arac,
                'en_cok_bakim': en_cok_bakim,
                'son_bakim': son_bakim
            }
        except sqlite3.Error as e:
            print(f"İstatistik hatası: {e}")
            return {}
    
    # Şantiye yönetimi metodları
    def get_all_santiyeler(self):
        """Tüm şantiyeleri getir"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM santiyeler ORDER BY santiye_adi")
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Şantiye getirme hatası: {e}")
            return []
    
    def add_santiye(self, santiye_adi, lokasyon=None, sorumlu=None):
        """Yeni şantiye ekle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO santiyeler (santiye_adi, lokasyon, sorumlu)
                VALUES (?, ?, ?)
            ''', (santiye_adi, lokasyon, sorumlu))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Şantiye ekleme hatası: {e}")
            return None
    
    def update_santiye(self, santiye_id, santiye_adi, lokasyon=None, sorumlu=None):
        """Şantiye güncelle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE santiyeler 
                SET santiye_adi = ?, lokasyon = ?, sorumlu = ?
                WHERE id = ?
            ''', (santiye_adi, lokasyon, sorumlu, santiye_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Şantiye güncelleme hatası: {e}")
            return False
    
    def delete_santiye(self, santiye_id):
        """Şantiye sil"""
        try:
            cursor = self.conn.cursor()
            # Önce şantiyedeki araçları kontrol et
            cursor.execute("SELECT COUNT(*) FROM araclar WHERE santiye_id = ?", (santiye_id,))
            arac_sayisi = cursor.fetchone()[0]
            
            if arac_sayisi > 0:
                return False, f"Bu şantiyede {arac_sayisi} araç bulunuyor. Önce araçları silin veya başka şantiyeye taşıyın."
            
            cursor.execute("DELETE FROM santiyeler WHERE id = ?", (santiye_id,))
            self.conn.commit()
            return True, "Şantiye başarıyla silindi."
        except sqlite3.Error as e:
            print(f"Şantiye silme hatası: {e}")
            return False, f"Şantiye silinirken hata oluştu: {e}"
    
    # Araç yönetimi metodları
    def get_araclar_by_santiye(self, santiye_id):
        """Belirli şantiyedeki araçları getir"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM araclar 
                WHERE santiye_id = ? 
                ORDER BY plaka
            ''', (santiye_id,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Araç getirme hatası: {e}")
            return []
    
    def add_arac(self, arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id):
        """Yeni araç ekle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO araclar (arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum, ariza_durumu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sağlam', 'Aktif')
            ''', (arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Araç ekleme hatası: {e}")
            return None
    
    def add_arac_with_status(self, arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum):
        """Yeni araç ekle (durum ile birlikte)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO araclar (arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum, ariza_durumu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Aktif')
            ''', (arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Araç ekleme hatası: {e}")
            return None
    
    def update_arac_durum(self, arac_id, durum, ariza_durumu=None):
        """Araç durumunu güncelle"""
        try:
            cursor = self.conn.cursor()
            if ariza_durumu:
                cursor.execute('''
                    UPDATE araclar 
                    SET durum = ?, ariza_durumu = ?
                    WHERE id = ?
                ''', (durum, ariza_durumu, arac_id))
            else:
                cursor.execute('''
                    UPDATE araclar 
                    SET durum = ?
                    WHERE id = ?
                ''', (durum, arac_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Araç güncelleme hatası: {e}")
            return False
    
    def fix_all_vehicle_status(self, santiye_id=None):
        """Tüm araçların durumunu düzelt (Aktif ve Sağlam yap)"""
        try:
            cursor = self.conn.cursor()
            if santiye_id:
                # Seçili şantiyedeki tüm araçları sağlam yap
                cursor.execute('''
                    UPDATE araclar 
                    SET durum = 'Sağlam', ariza_durumu = 'Aktif'
                    WHERE santiye_id = ?
                ''', (santiye_id,))
            else:
                # Tüm araçları sağlam yap
                cursor.execute('''
                    UPDATE araclar 
                    SET durum = 'Sağlam', ariza_durumu = 'Aktif'
                ''')
            self.conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            print(f"Araç durum düzeltme hatası: {e}")
            return 0

    def get_all_araclar(self):
        """Tüm araçları getir"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM araclar 
                ORDER BY olusturma_tarihi DESC
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Araç listesi getirme hatası: {e}")
            return []

class ModernTableWidget(QTableWidget):
    """Modern tablo widget'ı"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Tablo arayüzünü ayarla"""
        # Modern tema tablo
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SECONDARY_BG};
                color: {PRIMARY_TEXT};
                border: 1px solid {BORDER_ACCENT};
                border-radius: 6px;
                gridline-color: {BORDER_PRIMARY};
                selection-background-color: {PRIMARY_ACCENT};
                selection-color: {PRIMARY_TEXT};
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {BORDER_PRIMARY};
                border-right: 1px solid {BORDER_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
            }}
            QTableWidget::item:alternate {{
                background-color: {TERTIARY_BG};
            }}
            QHeaderView::section {{
                background: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
                padding: 12px 8px;
                border: 1px solid {BORDER_ACCENT};
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
            QHeaderView::section:hover {{
                background: {SUCCESS_ACCENT};
            }}
            QScrollBar:vertical {{
                background: {SECONDARY_BG};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {TERTIARY_BG};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ACCENT_BG};
            }}
        """)
        
        # Tablo ayarları
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        
        # Sütun başlıkları
        headers = [
            "Sıra", "ID", "PLAKA", "KAPI NO", "BÖLGE", "TARİH", 
            "BAKIM KM", "SONRAKI KM", "YAPILAN İŞLEM", "DİĞER", "BAKIMI YAPAN"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Sütun genişlikleri
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Sıra
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # PLAKA
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # KAPI NO
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # BÖLGE
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # TARİH
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # BAKIM KM
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # SONRAKI KM
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)           # YAPILAN İŞLEM
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # DİĞER
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)  # BAKIMI YAPAN
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setColumnWidth(0, 50)   # Sıra
        self.setColumnWidth(1, 50)    # ID
        self.setColumnWidth(2, 120)  # PLAKA minimum
        self.setColumnWidth(3, 100)  # KAPI NO
        self.setColumnWidth(4, 110)  # BÖLGE minimum
        self.setColumnWidth(5, 120)  # TARİH minimum
        self.setColumnWidth(6, 110)  # BAKIM KM min
        self.setColumnWidth(7, 120)  # SONRAKI KM min
        
        # Satır yüksekliği
        self.verticalHeader().setDefaultSectionSize(35)
        # Otomatik satır numaralarını gizle
        self.verticalHeader().setVisible(False)
        # ID sütununu gizle (tabloya yine yazacağız, seçimlerde kullanacağız)
        self.setColumnHidden(1, True)
        
        # Modern tema tablo
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SECONDARY_BG};
                color: {PRIMARY_TEXT};
                border: 1px solid {BORDER_ACCENT};
                border-radius: 6px;
                gridline-color: {BORDER_PRIMARY};
                selection-background-color: {PRIMARY_ACCENT};
                selection-color: {PRIMARY_TEXT};
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {BORDER_PRIMARY};
                border-right: 1px solid {BORDER_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
            }}
            QTableWidget::item:alternate {{
                background-color: {TERTIARY_BG};
            }}
            QHeaderView::section {{
                background: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
                padding: 12px 8px;
                border: 1px solid {BORDER_ACCENT};
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
            QHeaderView::section:hover {{
                background: {SUCCESS_ACCENT};
            }}
            QScrollBar:vertical {{
                background: {SECONDARY_BG};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {TERTIARY_BG};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ACCENT_BG};
            }}
        """)

class RecordDialog(QDialog):
    """Kayıt ekleme/düzenleme dialog'u"""
    
    def __init__(self, parent=None, record_data=None):
        super().__init__(parent)
        self.record_data = record_data
        self.original_s_no = record_data[1] if record_data else None
        self.setup_ui()
        
        if record_data:
            self.load_data()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle("Kayıt Ekle/Düzenle" if not self.record_data else "Kayıt Düzenle")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Plaka
        self.plaka_edit = QLineEdit()
        self.plaka_edit.setPlaceholderText("Örn: 06 ABC 123")
        form_layout.addRow("Plaka *:", self.plaka_edit)
        
        # Kapı No
        self.kapi_no_edit = QLineEdit()
        self.kapi_no_edit.setPlaceholderText("Örn: 25-123")
        form_layout.addRow("Kapı No:", self.kapi_no_edit)
        
        # Bölge
        self.bolge_edit = QLineEdit()
        self.bolge_edit.setPlaceholderText("Örn: KARAKÖY")
        form_layout.addRow("Bölge:", self.bolge_edit)
        
        # Tarih
        self.tarih_edit = QDateEdit()
        self.tarih_edit.setDate(QDate.currentDate())
        self.tarih_edit.setCalendarPopup(True)
        self.tarih_edit.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Tarih:", self.tarih_edit)
        
        # Bakım KM
        self.bakim_km_spin = QSpinBox()
        self.bakim_km_spin.setRange(0, 9999999)
        self.bakim_km_spin.setValue(0)
        form_layout.addRow("Bakım Esnasında KM:", self.bakim_km_spin)
        
        # Sonraki Bakım KM
        self.sonraki_km_spin = QSpinBox()
        self.sonraki_km_spin.setRange(0, 9999999)
        self.sonraki_km_spin.setValue(0)
        form_layout.addRow("Bir Sonraki Bakım KM:", self.sonraki_km_spin)
        
        # Yapılan İşlem
        self.yapilan_islem_edit = QTextEdit()
        self.yapilan_islem_edit.setMaximumHeight(100)
        self.yapilan_islem_edit.setPlaceholderText("Yapılan işlemleri yazın...")
        form_layout.addRow("Yapılan İşlem:", self.yapilan_islem_edit)
        
        # Diğer
        self.diger_edit = QLineEdit()
        self.diger_edit.setPlaceholderText("Diğer notlar...")
        form_layout.addRow("Diğer:", self.diger_edit)
        
        # Bakım Yapan
        self.bakim_yapan_edit = QLineEdit()
        self.bakim_yapan_edit.setPlaceholderText("Örn: YUNUS AFŞİN")
        form_layout.addRow("Bakımı Yapan:", self.bakim_yapan_edit)
        
        layout.addLayout(form_layout)
        
        # Butonlar
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Stil
        self.setStyleSheet("""
            QDialog {
                background-color: #2c2c2c;
                color: #ffffff;
            }
            QLineEdit, QSpinBox, QDateEdit, QTextEdit {
                background-color: #2c2c2c;
                color: #ffffff;
                padding: 1px;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                font-size: 11px;
            }
            QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #6b8e6b;
            }
            QLabel {
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton {
                background-color: #5a6c7d;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6b8e6b;
                border-color: #6b8e6b;
            }
            QPushButton:pressed {
                background-color: #4a5c6d;
                border-color: #4a5c6d;
            }
        """)
    
    def load_data(self):
        """Mevcut veriyi yükle"""
        if not self.record_data:
            return
        
        data = self.record_data
        self.plaka_edit.setText(data[2] or "")
        self.bolge_edit.setText(data[4] or "")
        # Kapi No (DB index 3)
        self.kapi_no_edit.setText(data[3] or "")
        
        if data[5]:
            try:
                date = QDate.fromString(data[5], "dd.MM.yyyy")
                self.tarih_edit.setDate(date)
            except:
                pass
        
        self.bakim_km_spin.setValue(data[6] or 0)
        self.sonraki_km_spin.setValue(data[7] or 0)
        self.yapilan_islem_edit.setPlainText(data[8] or "")
        self.diger_edit.setText(data[9] or "")
        self.bakim_yapan_edit.setText(data[10] or "")
    
    def get_data(self):
        """Form verilerini al"""
        tarih = self.tarih_edit.date().toString("dd.MM.yyyy")
        
        return (
            self.original_s_no if self.original_s_no is not None else None,
            self.plaka_edit.text().strip(),
            self.kapi_no_edit.text().strip() or None,
            self.bolge_edit.text().strip() or None,
            tarih,
            self.bakim_km_spin.value() if self.bakim_km_spin.value() > 0 else None,
            self.sonraki_km_spin.value() if self.sonraki_km_spin.value() > 0 else None,
            self.yapilan_islem_edit.toPlainText().strip() or None,
            self.diger_edit.text().strip() or None,
            self.bakim_yapan_edit.text().strip() or None
        )

class MainWindow(QMainWindow):
    """Ana pencere"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.update_manager = UpdateManager()  # Güncelleme yöneticisi
        self.settings = QSettings("OztacPetrol", "SantiyeYonetim") # Ayarlar objesi
        self.setup_ui()
        self.load_data()
        # Şantiyeleri yükle
        self.load_santiyeler()
        # Açılışta güncelleme kontrolü (arka planda)
        self.check_updates_on_startup()
        
        # Pencereyi tam ekran yap (monitör çözünürlüğüne göre)
        self.setup_fullscreen()
    
    def setup_fullscreen(self):
        """Monitör çözünürlüğünü algıla ve tam ekran ayarla"""
        # Pencereyi tam ekran yap
        self.showMaximized()
        self.raise_()
        self.activateWindow()
    
    def apply_dark_theme_to_messagebox(self, msgbox):
        """QMessageBox'a koyu tema uygula"""
        msgbox.setStyleSheet("""
            QMessageBox {
                background-color: #2c2c2c;
                color: #ffffff;
            }
            QMessageBox QLabel {
                background-color: #2c2c2c;
                color: #ffffff;
                padding: 1px;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #5a6c7d;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #6b8e6b;
                border-color: #6b8e6b;
            }
            QMessageBox QPushButton:pressed {
                background-color: #4a5c6d;
            }
        """)
    
    def show_warning(self, title, message):
        """Koyu tema uyumlu uyarı mesajı göster"""
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle(title)
        msgbox.setText(message)
        msgbox.setIcon(QMessageBox.Icon.Warning)
        msgbox.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.apply_dark_theme_to_messagebox(msgbox)
        return msgbox.exec()
    
    def show_information(self, title, message):
        """Koyu tema uyumlu bilgi mesajı göster"""
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle(title)
        msgbox.setText(message)
        msgbox.setIcon(QMessageBox.Icon.Information)
        msgbox.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.apply_dark_theme_to_messagebox(msgbox)
        return msgbox.exec()
    
    def show_critical(self, title, message):
        """Koyu tema uyumlu hata mesajı göster"""
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle(title)
        msgbox.setText(message)
        msgbox.setIcon(QMessageBox.Icon.Critical)
        msgbox.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.apply_dark_theme_to_messagebox(msgbox)
        return msgbox.exec()
    
    def show_question(self, title, message):
        """Koyu tema uyumlu soru mesajı göster"""
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle(title)
        msgbox.setText(message)
        msgbox.setIcon(QMessageBox.Icon.Question)
        msgbox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.apply_dark_theme_to_messagebox(msgbox)
        return msgbox.exec()
    
    def setup_ui(self):
        """Ana pencere arayüzünü ayarla"""
        self.setWindowTitle("Şantiye Yönetim Sistemi")
        # Pencere göster - setup_fullscreen'de gösterilecek
        
        # Modern tema ana pencere
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {PRIMARY_BG};
                color: {PRIMARY_TEXT};
            }}
            QWidget {{
                background-color: {PRIMARY_BG};
                color: {PRIMARY_TEXT};
            }}
            QDialog {{
                background-color: {PRIMARY_BG};
                color: {PRIMARY_TEXT};
            }}
            QMessageBox {{
                background-color: #2c2c2c;
                color: #ffffff;
            }}
            QMessageBox QLabel {{
                background-color: #2c2c2c;
                color: #ffffff;
                padding: 1px;
                font-size: 13px;
            }}
            QMessageBox QPushButton {{
                background-color: #5a6c7d;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: #6b8e6b;
                border-color: #6b8e6b;
            }}
            QMessageBox QPushButton:pressed {{
                background-color: #4a5c6d;
            }}
            QFileDialog {{
                background-color: {PRIMARY_BG};
                color: {PRIMARY_TEXT};
            }}
            QFileDialog QLabel {{
                background-color: {PRIMARY_BG};
                color: {PRIMARY_TEXT};
            }}
            QFileDialog QPushButton {{
                background-color: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
                border: 1px solid {BORDER_ACCENT};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QFileDialog QPushButton:hover {{
                background-color: {SUCCESS_ACCENT};
            }}
        """)
        
        # Merkez widget
        central_widget = QWidget()
        central_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {PRIMARY_BG};
                color: {PRIMARY_TEXT};
            }}
        """)
        self.setCentralWidget(central_widget)
        
        # Ana layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Üst toolbar
        self.create_toolbar(main_layout)
        
        # Ana içerik - Sadece sağ panel (tab'lar)
        content_layout = QHBoxLayout()
        
        # Sağ panel - Sekmeler (Kayıtlar + Dashboard)
        right_tabs = QTabWidget()
        right_tabs.setTabPosition(QTabWidget.TabPosition.North)
        right_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 1px solid {BORDER_ACCENT}; 
                background-color: {SECONDARY_BG};
                border-radius: 6px;
            }} 
            QTabBar::tab {{ 
                background: {SECONDARY_BG}; 
                color: {PRIMARY_TEXT}; 
                padding: 12px 20px; 
                margin-right: 2px; 
                border-radius: 8px 8px 0 0;
                border: 1px solid {BORDER_PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:selected {{ 
                background: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
                border-bottom: 3px solid {SUCCESS_ACCENT};
                font-weight: 500;
            }}
            QTabBar::tab:hover {{
                background: {TERTIARY_BG};
                border-color: {BORDER_ACCENT};
            }}
        """)
        # Kayıtlar sekmesi
        records_panel = self.create_right_panel()
        right_tabs.addTab(records_panel, "Kayıtlar")
        # Araçlar sekmesi
        vehicles_panel = self.create_vehicles_panel()
        right_tabs.addTab(vehicles_panel, "Araçlar")
        content_layout.addWidget(right_tabs)  # Tam genişlik
        
        main_layout.addLayout(content_layout)
        
        # Status bar en altta; footer içeriklerini status bar'a taşı
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet('''
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-top: 1px solid #5a6c7d;
                color: #ffffff;
                padding: 2px 4px;
                font-size: 11px;
            } 
            QStatusBar::item {
                border: none;
            }
        ''')
        self.setStatusBar(self.status_bar)
        # Sol tarafa durum etiketi (mesaj)
        self.status_msg = QLabel("Hazır")
        chip_style = '''
            QLabel {
                padding: 3px 8px;
                color: #ffffff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6c7d, stop:1 #5a6c7d);
                border: 1px solid #5a6c7d;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }
        '''
        self.status_msg.setStyleSheet(chip_style)
        self.status_bar.addWidget(self.status_msg, 1)
        
        # Şantiye seçimi dropdown'ı
        self.santiye_combo = QComboBox()
        self.santiye_combo.setMinimumWidth(200)
        self.santiye_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                color: #ffffff;
                background: #2c2c2c;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                font-weight: 500;
            }
            QComboBox:hover {
                border-color: #5a6c7d;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #5a6c7d;
                margin-right: 5px;
            }
        """)
        # Sağ tarafa kalıcı widget'lar ekle (toplam kayıt ve link)
        self.footer_total = QLabel("Toplam kayıt: 0")
        self.footer_total.setStyleSheet('''
            QLabel {
                padding: 3px 8px;
                color: #ffffff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b8e6b, stop:1 #6b8e6b);
                border: 1px solid #6b8e6b;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }
        ''')
        self.status_bar.addPermanentWidget(self.footer_total)
        link = QLabel(
            '<a style="text-decoration:none;color:#4a9eff;" '
            'href="https://wa.me/905439761400?text=merhaba%20%C5%9Fantiye%20takip%20program%C4%B1ndan%20geliyorum%20bir!">'
            'Coded By Yunus AÇIKGÖZ</a>'
        )
        link.setOpenExternalLinks(True)
        link.setStyleSheet('''
            QLabel {
                padding: 2px 6px;
                color: #4a9eff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a3a4a, stop:1 #1a2a3a);
                border: 1px solid #3a5a7a;
                border-radius: 4px;
                margin-left: 6px;
                font-size: 9px;
                font-weight: 500;
            }
            QLabel:hover {
                color: #6bb6ff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a4a5a, stop:1 #2a3a4a);
                border-color: #4a7a9a;
            }
        ''')
        self.status_bar.addPermanentWidget(link)
        
        # Stil
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #5a6c7d;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6c7d;
            }
            QPushButton:pressed {
                background-color: #5a6c7d;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit {
                padding: 1px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #5a6c7d;
            }
        """)
        
        # Varsayılan: Karanlık tema uygula
        self.apply_dark_theme()
        
        # Sidebar'ı modernleştir: kart benzeri görünüm
        self.sidebar_style = """
            QGroupBox#Kontroller {
                background: white;
                border: none;
            }
        """
    
    def create_toolbar(self, layout):
        """Üst toolbar oluştur"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.Shape.Box)
        # Koyu tema toolbar
        toolbar_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c2c2c, stop:0.3 #2c2c2c, stop:0.7 #2c2c2c, stop:1 #2c2c2c);
                border: none;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(20)  # Butonlar arası boşluk
        toolbar_layout.setContentsMargins(20, 8, 20, 8)  # İç boşluklar
        toolbar_frame.setLayout(toolbar_layout)
        
        # Logo ve başlık container
        title_container = QHBoxLayout()
        
        # Basit emoji logo
        logo_label = QLabel("🏗️")
        logo_label.setFixedSize(48, 48)
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #5a6c7d;
                background: transparent;
                border: none;
                text-align: center;
            }
        """)
        
        title_container.addWidget(logo_label)
        
        # Başlık - Uzun ve modern
        title_label = QLabel("ÖZTAÇ PETROL A.Ş. ŞANTİYE YÖNETİM SİSTEMİ")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 800;
                color: #ffffff;
                padding: 8px 20px;
                line-height: 1.3;
                letter-spacing: 1px;
            }
        """)
        title_container.addStretch()
        title_container.addWidget(title_label)
        title_container.addStretch()
        
        toolbar_layout.addLayout(title_container)
        
        
        # Karanlık mod: varsayılan uygulanacak, buton kaldırıldı
        
        # Modern buton stilleri - gelişmiş tasarım
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                color: #ffffff;
                border: 2px solid #e1e8ed;
                padding: 14px 24px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                min-width: 180px;
                min-height: 28px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-color: #5a6c7d;
                color: #5a6c7d;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-color: #5a6c7d;
                color: #5a6c7d;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #bdbdbd;
                border-color: #e0e0e0;
            }
        """
        
        # Modern ToolButton stilleri - gelişmiş tasarım
        toolbutton_style = """
            QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                color: #ffffff;
                border: 2px solid #e1e8ed;
                padding: 14px 24px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                min-width: 200px;
                min-height: 28px;
                text-align: center;
            }
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-color: #5a6c7d;
                color: #5a6c7d;
            }
            QToolButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-color: #5a6c7d;
                color: #5a6c7d;
            }
            QToolButton:disabled {
                background: #f5f5f5;
                color: #bdbdbd;
                border-color: #e0e0e0;
            }
        """
        
        
        
        layout.addWidget(toolbar_frame)
        
    def create_footer(self):
        """Sağ altta tıklanabilir footer"""
        frame = QFrame()
        h = QHBoxLayout()
        h.addStretch()
        # Toplam kayıt rozeti
        self.footer_total = QLabel("Toplam kayıt: 0")
        self.footer_total.setStyleSheet('QLabel{padding:6px 10px;color:#1a2b49;background:#ffffff;border:1px solid #cfd8e3;border-radius:6px;}')
        h.addWidget(self.footer_total)
        # Coded by
        label = QLabel(
            '<a style="text-decoration:none;color:#4a9eff;" '
            'href="https://wa.me/905439761400?text=merhaba%20%C5%9Fantiye%20takip%20program%C4%B1ndan%20geliyorum%20bir!">'
            'Coded By Yunus AÇIKGÖZ</a>'
        )
        label.setOpenExternalLinks(True)
        label.setStyleSheet('''
            QLabel {
                padding: 2px 6px;
                color: #4a9eff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a3a4a, stop:1 #1a2a3a);
                border: 1px solid #3a5a7a;
                border-radius: 4px;
                margin-left: 6px;
                font-size: 9px;
                font-weight: 500;
            }
            QLabel:hover {
                color: #6bb6ff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a4a5a, stop:1 #2a3a4a);
                border-color: #4a7a9a;
            }
        ''')
        h.addWidget(label)
        frame.setLayout(h)
        frame.setStyleSheet('QFrame{background:transparent;}')
        return frame
    
    def create_left_panel(self):
        """Sol panel oluştur"""
        panel = QGroupBox("Kontroller")
        panel.setObjectName("Kontroller")
        panel.setFixedWidth(300)  # Sol panel genişliği
        panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a6c7d;
                border-radius: 10px;
                margin: 1px;
                padding-top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 11px;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Modern arama grubu
        search_group = QGroupBox("🔍 Arama ve İşlemler")
        search_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a6c7d;
                border-radius: 10px;
                margin: 1px;
                padding-top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 11px;
            }
        """)
        search_layout = QVBoxLayout()
        search_layout.setSpacing(12)
        
        # Modern arama kutusu
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Plaka ile ara...")
        self.search_edit.textChanged.connect(self.search_records)
        self.search_edit.setFixedHeight(32)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                font-size: 11px;
                font-weight: 500;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #6b8e6b;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QLineEdit:hover {
                border-color: #5a6c7d;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
        """)
        search_layout.addWidget(self.search_edit)
        
        # Banner'dan taşınan butonlar
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Yeni Kayıt butonu - banner'dan taşındı
        new_record_btn = QPushButton("✨ Yeni Kayıt")
        new_record_btn.clicked.connect(self.add_record)
        new_record_btn.setFixedHeight(32)
        new_record_btn.setMinimumWidth(120)
        new_record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a6a5a, stop:1 #3a5a4a);
                color: #ffffff;
                border: 2px solid #4a6a5a;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a7a5a, stop:1 #4a6a5a);
                border-color: #5a7a5a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a6b4a, stop:1 #3a5b3a);
                border-color: #3a5b3a;
            }
        """)
        buttons_layout.addWidget(new_record_btn)
        
        # Diğer İşlemler butonu - banner'dan taşındı
        more_menu = QMenu(self)
        more_menu.setStyleSheet("""
            QMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border: 2px solid #e1f5fe;
                border-radius: 12px;
                padding: 1px;
            }
            QMenu::item {
                background: transparent;
                padding: 12px 20px;
                border-radius: 6px;
                margin: 1px;
                font-weight: 500;
                color: #ffffff;
            }
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                color: #5a6c7d;
            }
            QMenu::separator {
                height: 1px;
                background: #e1f5fe;
                margin: 8px 0;
            }
        """)
        
        act_refresh = QAction("🔄 Yenile", self)
        act_refresh.triggered.connect(self.load_data)
        act_import = QAction("📥 Excel İçe Aktar", self)
        act_import.triggered.connect(self.import_excel)
        act_export = QAction("📤 Excel Dışa Aktar", self)
        act_export.triggered.connect(self.export_excel)
        act_wipe = QAction("🗑️ Tümünü Sil", self)
        act_wipe.triggered.connect(self.delete_all_records)
        act_update = QAction("⚡ Güncelleme Kontrolü", self)
        act_update.triggered.connect(self.manual_check_updates)
        
        more_menu.addAction(act_refresh)
        more_menu.addAction(act_import)
        more_menu.addAction(act_export)
        more_menu.addSeparator()
        more_menu.addAction(act_update)
        more_menu.addSeparator()
        more_menu.addAction(act_wipe)

        more_btn = QToolButton()
        more_btn.setText("🔧 Diğer ▼")
        more_btn.setMenu(more_menu)
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_btn.setFixedHeight(32)
        more_btn.setMinimumWidth(120)
        more_btn.setStyleSheet("""
            QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5a623, stop:1 #b8860b);
                color: #ffffff;
                border: 2px solid #b8860b;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                text-align: center;
            }
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffb74d, stop:1 #f5a623);
                border-color: #f5a623;
            }
            QToolButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b8860b, stop:1 #9c6b08);
                border-color: #9c6b08;
            }
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
                height: 0px;
            }
            QToolButton::drop-down {
                border: none;
                width: 0px;
            }
        """)
        buttons_layout.addWidget(more_btn)
        
        search_layout.addLayout(buttons_layout)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # İşlemler grubu
        actions_group = QGroupBox("İşlemler")
        actions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a6c7d;
                border-radius: 10px;
                margin: 1px;
                padding-top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 11px;
            }
        """)
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        # Yeni kayıt butonu
        add_btn = QPushButton("➕ Yeni Kayıt Ekle")
        add_btn.clicked.connect(self.add_record)
        add_btn.setFixedHeight(30)
        add_btn.setMinimumWidth(140)
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a7c59, stop:1 #3a6b49);
                color: #ffffff;
                border: 1px solid #4a7c59;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7ed321, stop:1 #6b8e6b);
                border-color: #7ed321;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #388e3c);
                border-color: #388e3c;
            }
        """)
        actions_layout.addWidget(add_btn)
        
        # Tümünü sil butonu (sidebar)
        wipe_btn_side = QPushButton("🗑️ Tüm Kayıtları Sil")
        wipe_btn_side.clicked.connect(self.delete_all_records)
        wipe_btn_side.setFixedHeight(30)
        wipe_btn_side.setMinimumWidth(140)
        wipe_btn_side.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #a93226);
                color: #ffffff;
                border: 1px solid #c0392b;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff4444, stop:1 #d0021b);
                border-color: #ff4444;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8b5a5a, stop:1 #6b3a3a);
                border-color: #6b3a3a;
            }
        """)
        actions_layout.addWidget(wipe_btn_side)
        
        # Düzenle butonu
        edit_btn = QPushButton("✏️ Kayıt Düzenle")
        edit_btn.clicked.connect(self.edit_record)
        edit_btn.setFixedHeight(30)
        edit_btn.setMinimumWidth(140)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: #ffffff;
                border: 1px solid #3498db;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ba0f2, stop:1 #4a90e2);
                border-color: #5ba0f2;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196f3, stop:1 #1976d2);
                border-color: #1976d2;
            }
        """)
        actions_layout.addWidget(edit_btn)
        
        # Sil butonu
        delete_btn = QPushButton("🗑️ Kayıt Sil")
        delete_btn.clicked.connect(self.delete_record)
        delete_btn.setFixedHeight(30)
        delete_btn.setMinimumWidth(140)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: #ffffff;
                border: 1px solid #e74c3c;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff8a8a, stop:1 #ff6b6b);
                border-color: #ff8a8a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                border-color: #c0392b;
            }
        """)
        actions_layout.addWidget(delete_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # İstatistikler grubu
        stats_group = QGroupBox("İstatistikler")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a6c7d;
                border-radius: 10px;
                margin: 1px;
                padding-top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 11px;
            }
        """)
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(8)
        
        self.stats_label = QLabel("İstatistikler yükleniyor...")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("""
            QLabel {
                padding: 1px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-radius: 8px;
                font-size: 12px;
                color: #ffffff;
                border: 1px solid #404040;
                line-height: 1.5;
                min-height: 80px;
            }
        """)
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        # Sidebar koyu stil
        panel.setStyleSheet("""
            QGroupBox { color: #ffffff; border: 1px solid #333; border-radius: 8px; background:#1f1f1f; }
            QLineEdit { background: #2b2b2b; color: #ffffff; border: 1px solid #2c2c2c; }
            QPushButton { background: #6b8e6b; color: #ffffff; border: none; padding: 10px; border-radius: 6px; font-weight:600; }
            QPushButton:hover { background: #6b8e6b; }
            QPushButton#danger { background:#8b5a5a; }
            QPushButton#danger:hover { background:#8b5a5a; }
            QLabel { color: #ffffff; }
        """)
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """Kayıtlar sekmesi - Sol panel + Sağ panel"""
        panel = QWidget()
        main_layout = QHBoxLayout()
        
        # Sol panel - Arama ve İşlemler
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)  # Sol panel 1/4 genişlik
        
        # Sağ panel - Tablo ve filtreler
        right_panel = QWidget()
        layout = QVBoxLayout()
        
        # Filtre barı
        filter_bar = QHBoxLayout()
        self.filter_use_date = QCheckBox("Tarih filtresi")
        self.filter_use_date.setChecked(False)
        self.filter_use_date.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-weight: 600;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #5a6c7d;
                border-radius: 3px;
                background: #2c2c2c;
            }
            QCheckBox::indicator:checked {
                background: #5a6c7d;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
        """)
        
        self.filter_start = QDateEdit()
        self.filter_start.setCalendarPopup(True)
        self.filter_start.setDisplayFormat("dd.MM.yyyy")
        self.filter_start.setDate(QDate.currentDate().addMonths(-6))
        self.filter_start.setStyleSheet("""
            QDateEdit {
                background: #2c2c2c;
                color: #ffffff;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                padding: 6px;
                font-weight: 600;
            }
            QDateEdit:focus {
                border-color: #6b8e6b;
            }
            QDateEdit::drop-down {
                border: none;
                background: #5a6c7d;
                border-radius: 4px;
            }
        """)
        
        self.filter_end = QDateEdit()
        self.filter_end.setCalendarPopup(True)
        self.filter_end.setDisplayFormat("dd.MM.yyyy")
        self.filter_end.setDate(QDate.currentDate())
        self.filter_end.setStyleSheet("""
            QDateEdit {
                background: #2c2c2c;
                color: #ffffff;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                padding: 6px;
                font-weight: 600;
            }
            QDateEdit:focus {
                border-color: #6b8e6b;
            }
            QDateEdit::drop-down {
                border: none;
                background: #5a6c7d;
                border-radius: 4px;
            }
        """)
        
        self.filter_bolge = QComboBox()
        self.filter_bolge.setEditable(False)
        self.filter_bolge.addItem("Tümü")
        self.filter_bolge.setStyleSheet("""
            QComboBox {
                background: #2c2c2c;
                color: #ffffff;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                padding: 6px;
                font-weight: 600;
            }
            QComboBox:focus {
                border-color: #6b8e6b;
            }
            QComboBox::drop-down {
                border: none;
                background: #5a6c7d;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background: #2c2c2c;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                selection-background-color: #5a6c7d;
            }
        """)
        
        self.filter_bakim_yapan = QComboBox()
        self.filter_bakim_yapan.addItem("Tümü")
        self.filter_bakim_yapan.setStyleSheet("""
            QComboBox {
                background: #2c2c2c;
                color: #ffffff;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                padding: 6px;
                font-weight: 600;
            }
            QComboBox:focus {
                border-color: #6b8e6b;
            }
            QComboBox::drop-down {
                border: none;
                background: #5a6c7d;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background: #2c2c2c;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                selection-background-color: #5a6c7d;
            }
        """)
        # Uygula ve Temizle butonları
        btn_apply = QPushButton("Filtrele")
        btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6c7d, stop:1 #5a6c7d);
                color: #ffffff;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b8e6b, stop:1 #6b8e6b);
                border-color: #6b8e6b;
            }
        """)
        
        btn_clear = QPushButton("Temizle")
        btn_clear.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                color: #ffffff;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-color: #6b8e6b;
            }
        """)
        
        for w in [self.filter_start, self.filter_end, self.filter_bolge, self.filter_bakim_yapan]:
            w.setFixedHeight(32)
        btn_apply.setFixedHeight(32)
        btn_clear.setFixedHeight(32)
        btn_clear.setFixedHeight(32)
        filter_bar.addWidget(self.filter_use_date)
        filter_bar.addWidget(QLabel("Başlangıç:"))
        filter_bar.addWidget(self.filter_start)
        filter_bar.addWidget(QLabel("Bitiş:"))
        filter_bar.addWidget(self.filter_end)
        filter_bar.addWidget(QLabel("Bölge:"))
        filter_bar.addWidget(self.filter_bolge)
        filter_bar.addWidget(QLabel("Bakım Yapan:"))
        filter_bar.addWidget(self.filter_bakim_yapan)
        filter_bar.addWidget(btn_apply)
        filter_bar.addWidget(btn_clear)
        filter_bar.addStretch()
        
        # Etkileşimler
        btn_apply.clicked.connect(self.apply_filters)
        btn_clear.clicked.connect(self.clear_filters)
        self.filter_start.dateChanged.connect(self.apply_filters)
        self.filter_end.dateChanged.connect(self.apply_filters)
        self.filter_bolge.currentIndexChanged.connect(self.apply_filters)
        self.filter_bakim_yapan.currentIndexChanged.connect(self.apply_filters)
        self.filter_use_date.toggled.connect(self.on_toggle_date_filter)
        
        layout.addLayout(filter_bar)
        self.table = ModernTableWidget()
        # Sağ tık menüsü etkinleştir
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)
        # Çift tıklamada detay göster
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        layout.addWidget(self.table)
        right_panel.setLayout(layout)
        
        # Sağ paneli ana layout'a ekle
        main_layout.addWidget(right_panel, 3)  # Sağ panel 3/4 genişlik
        panel.setLayout(main_layout)
        return panel

    def on_table_context_menu(self, pos):
        """Tabloda sağ tık menüsü"""
        index = self.table.indexAt(pos)
        if index.isValid():
            self.table.selectRow(index.row())
        menu = QMenu(self)
        act_edit = QAction("Düzenle", self)
        act_delete = QAction("Sil", self)
        act_view = QAction("Detayı Göster", self)
        act_edit.triggered.connect(self.edit_record)
        act_delete.triggered.connect(self.delete_record)
        act_view.triggered.connect(self.show_operation_details)
        menu.addAction(act_edit)
        menu.addAction(act_delete)
        menu.addAction(act_view)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def on_cell_double_clicked(self, row, col):
        """Çift tıklamada yapılan işlem/detay göster"""
        # Yalnızca 'YAPILAN İŞLEM' veya 'DİĞER' sütunlarında tetikle
        if col in (8, 9):
            self.show_operation_details()

    def show_operation_details(self):
        """Seçili satırın 'Yapılan İşlem' ve 'Diğer' alanlarını büyük pencerede göster"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        item = self.table.item(current_row, 1)  # ID sütunu artık 1. sütun
        if not item:
            return
        record_id = item.data(Qt.ItemDataRole.UserRole)
        # Kayıt bul
        records = self.db_manager.get_all_records()
        record = None
        for r in records:
            if r[0] == record_id:
                record = r
                break
        if not record:
            return
        
        # Modern modal dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("🔧 Yapılan İşlem Detayı")
        dlg.setModal(True)
        dlg.resize(800, 600)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #2c2c2c;
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Başlık
        title_label = QLabel("🔧 Yapılan İşlem Detayı")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-radius: 10px;
                border: 2px solid #5a6c7d;
            }
        """)
        layout.addWidget(title_label)
        
        # Kayıt bilgileri
        info_group = QGroupBox("📋 Kayıt Bilgileri")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a6c7d;
                border-radius: 10px;
                margin: 1px;
                padding-top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"🚗 Plaka: {record[2] or '-'}"))
        info_layout.addWidget(QLabel(f"🔢 Kapı No: {record[3] or '-'}"))
        info_layout.addWidget(QLabel(f"📅 Tarih: {record[5] or '-'}"))
        info_layout.addWidget(QLabel(f"🏢 Bölge: {record[4] or '-'}"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Yapılan işlem
        operation_group = QGroupBox("⚙️ Yapılan İşlem")
        operation_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #6b8e6b;
                border-radius: 10px;
                margin: 1px;
                padding-top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        operation_layout = QVBoxLayout()
        operation_text = QTextEdit()
        operation_text.setReadOnly(True)
        operation_text.setPlainText(record[8] or "Yapılan işlem bilgisi bulunmuyor.")
        operation_text.setStyleSheet("""
            QTextEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        operation_layout.addWidget(operation_text)
        operation_group.setLayout(operation_layout)
        layout.addWidget(operation_group)
        
        # Diğer bilgiler (varsa)
        if record[9]:
            other_group = QGroupBox("📝 Diğer Bilgiler")
            other_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #ff9800;
                    border-radius: 10px;
                    margin: 1px;
                    padding-top: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2c2c2c, stop:1 #2c2c2c);
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #ffffff;
                    font-size: 12px;
                }
            """)
            other_layout = QVBoxLayout()
            other_text = QTextEdit()
            other_text.setReadOnly(True)
            other_text.setPlainText(record[9])
            other_text.setStyleSheet("""
                QTextEdit {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #5a6c7d;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 12px;
                    line-height: 1.4;
                }
            """)
            other_layout.addWidget(other_text)
            other_group.setLayout(other_layout)
            layout.addWidget(other_group)
        
        # Butonlar
        button_layout = QHBoxLayout()
        close_btn = QPushButton("❌ Kapat")
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: #ffffff;
                border: 2px solid #dc3545;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #dc3545);
            }
        """)
        close_btn.clicked.connect(dlg.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dlg.setLayout(layout)
        dlg.exec()


    
    def load_santiyeler(self):
        """Şantiyeleri yükle"""
        try:
            santiyeler = self.db_manager.get_all_santiyeler()
            self.santiye_combo.clear()
            self.santiye_combo.addItem("Şantiye Seçiniz...")
            
            for santiye in santiyeler:
                self.santiye_combo.addItem(santiye[1], santiye[0])  # santiye_adi, id
            
            # Varsayılan şantiye ekle (test için)
            if not santiyeler:
                self.db_manager.add_santiye("Ana Şantiye", "İstanbul", "Yunus AFŞİN")
                self.load_santiyeler()
                return
            
            # Son seçilen şantiyeyi yükle
            self.load_last_santiye_selection()
            
        except Exception as e:
            print(f"Şantiye yükleme hatası: {e}")
    
    def load_last_santiye_selection(self):
        """Son seçilen şantiyeyi yükle"""
        try:
            # Kayıtlı şantiye seçimini oku
            if hasattr(self, 'current_santiye_id') and self.current_santiye_id:
                # Mevcut şantiye ID'sini combo'da bul
                for i in range(self.santiye_combo.count()):
                    if self.santiye_combo.itemData(i) == self.current_santiye_id:
                        self.santiye_combo.setCurrentIndex(i)
                        self.on_santiye_changed(self.santiye_combo.currentText())
                        break
        except Exception as e:
            print(f"Son şantiye seçimi yükleme hatası: {e}")
    
    def save_santiye_selection(self):
        """Şantiye seçimini kaydet"""
        try:
            # Şu anki seçimi kaydet
            if hasattr(self, 'current_santiye_id') and self.current_santiye_id:
                # Burada bir ayar dosyasına veya veritabanına kaydedebiliriz
                # Şimdilik sadece memory'de tutuyoruz
                pass
        except Exception as e:
            print(f"Şantiye seçimi kaydetme hatası: {e}")
    
    def on_santiye_changed(self, santiye_adi):
        """Şantiye değiştiğinde araç listesini güncelle"""
        if santiye_adi == "Şantiye Seçiniz...":
            return
        
        # Seçili şantiyenin ID'sini al
        santiye_id = self.santiye_combo.currentData()
        if santiye_id:
            self.current_santiye_id = santiye_id
            self.load_vehicles_for_santiye(santiye_id)
            # Şantiye seçimini kaydet
            self.save_santiye_selection()
    
    def create_vehicles_panel(self):
        """Araçlar paneli oluştur"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #2c2c2c;
                color: #ffffff;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Başlık
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🚗 Araç Yönetimi")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-radius: 10px;
                border: 2px solid #5a6c7d;
            }
        """)
        
        # Araç ekleme butonu - küçük ve modern
        add_vehicle_btn = QPushButton("➕ Yeni Araç")
        add_vehicle_btn.setFixedHeight(35)
        add_vehicle_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b8e6b, stop:1 #6b8e6b);
                color: #ffffff;
                border: 2px solid #6b8e6b;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b8e6b, stop:1 #6b8e6b);
            }
        """)
        add_vehicle_btn.clicked.connect(self.add_vehicle)
        
        # Araç Excel import butonu - küçük ve modern
        import_vehicle_btn = QPushButton("📥 Excel İçe Aktar")
        import_vehicle_btn.setFixedHeight(35)
        import_vehicle_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                color: #ffffff;
                border: 2px solid #17a2b8;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20c997, stop:1 #17a2b8);
            }
        """)
        import_vehicle_btn.clicked.connect(self.import_vehicles_excel)
        
        # Araç Excel export butonu - küçük ve modern
        export_vehicle_btn = QPushButton("📤 Excel Dışa Aktar")
        export_vehicle_btn.setFixedHeight(35)
        export_vehicle_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                color: #ffffff;
                border: 2px solid #28a745;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
        """)
        export_vehicle_btn.clicked.connect(self.export_vehicles_excel)
        
        # Tüm araçları sil butonu - kırmızı ve tehlikeli
        delete_all_btn = QPushButton("🗑️ Tüm Araçları Sil")
        delete_all_btn.setFixedHeight(35)
        delete_all_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: #ffffff;
                border: 2px solid #dc3545;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #dc3545);
            }
        """)
        delete_all_btn.clicked.connect(self.delete_all_vehicles)
        
        # Header layout'a ekle - butonları başlığın yanına yerleştir
        header_layout.addWidget(title_label)
        header_layout.addWidget(add_vehicle_btn)
        header_layout.addWidget(import_vehicle_btn)
        header_layout.addWidget(export_vehicle_btn)
        header_layout.addWidget(delete_all_btn)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Araç listeleri için yan yana layout
        vehicles_layout = QHBoxLayout()
        vehicles_layout.setSpacing(20)
        
        # Aktif araçlar bölümü - sol taraf
        active_group = QGroupBox("✅ Aktif Araçlar")
        active_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 2px solid #27ae60;
                border-radius: 10px;
                background: #2c2c2c;
                font-weight: bold;
                font-size: 11px;
                margin-top: 15px;
                padding: 1px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #2c2c2c;
                border-radius: 4px;
            }
        """)
        active_layout = QVBoxLayout()
        
        self.active_vehicles_table = QTableWidget(0, 9)
        self.active_vehicles_table.setHorizontalHeaderLabels([
            "Sıra", "Araç / Makine Adı", "Plakası", "Makine No", "Markası", "Model", "Model Yılı", "Hesap Adı", "Durum"
        ])
        self.active_vehicles_table.setAlternatingRowColors(True)
        self.active_vehicles_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.active_vehicles_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.active_vehicles_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.active_vehicles_table.customContextMenuRequested.connect(self.show_vehicle_context_menu)
        self.active_vehicles_table.cellDoubleClicked.connect(self.show_vehicle_details)
        # Otomatik satır numaralarını gizle
        self.active_vehicles_table.verticalHeader().setVisible(False)
        
        # Esnek sütun genişlikleri
        header = self.active_vehicles_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Sıra - sabit genişlik
        self.active_vehicles_table.setColumnWidth(0, 50)  # Sıra sütunu genişliği
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Araç / Makine Adı
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Plakası
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Makine No
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Markası
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Model
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Model Yılı
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Hesap Adı
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # Durum - esnek
        
        # Tablo minimum genişliği
        self.active_vehicles_table.setMinimumWidth(600)
        
        self.active_vehicles_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SECONDARY_BG};
                color: {PRIMARY_TEXT};
                border: 1px solid {BORDER_SUCCESS};
                border-radius: 6px;
                gridline-color: {BORDER_PRIMARY};
                selection-background-color: {SUCCESS_ACCENT};
                selection-color: {PRIMARY_TEXT};
                font-size: 11px;
                margin: 1px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {BORDER_PRIMARY};
                border-right: 1px solid {BORDER_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {SUCCESS_ACCENT};
                color: {PRIMARY_TEXT};
            }}
            QTableWidget::item:alternate {{
                background-color: {TERTIARY_BG};
            }}
            QHeaderView::section {{
                background: {SUCCESS_ACCENT};
                color: {PRIMARY_TEXT};
                padding: 12px 8px;
                border: 1px solid {BORDER_SUCCESS};
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
        """)
        active_layout.addWidget(self.active_vehicles_table)
        active_group.setLayout(active_layout)
        vehicles_layout.addWidget(active_group)
        
        # Arızalı araçlar bölümü - sağ taraf
        faulty_group = QGroupBox("⚠️ Arızalı Araçlar")
        faulty_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 2px solid #e74c3c;
                border-radius: 10px;
                background: #2c2c2c;
                font-weight: bold;
                font-size: 11px;
                margin-top: 15px;
                padding: 1px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #2c2c2c;
                border-radius: 4px;
            }
        """)
        faulty_layout = QVBoxLayout()
        
        self.faulty_vehicles_table = QTableWidget(0, 9)
        self.faulty_vehicles_table.setHorizontalHeaderLabels([
            "Sıra", "Araç / Makine Adı", "Plakası", "Makine No", "Markası", "Model", "Model Yılı", "Hesap Adı", "Arıza Durumu"
        ])
        self.faulty_vehicles_table.setAlternatingRowColors(True)
        self.faulty_vehicles_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.faulty_vehicles_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.faulty_vehicles_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.faulty_vehicles_table.customContextMenuRequested.connect(self.show_vehicle_context_menu)
        self.faulty_vehicles_table.cellDoubleClicked.connect(self.show_vehicle_details)
        # Otomatik satır numaralarını gizle
        self.faulty_vehicles_table.verticalHeader().setVisible(False)
        
        # Esnek sütun genişlikleri
        header = self.faulty_vehicles_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Sıra - sabit genişlik
        self.faulty_vehicles_table.setColumnWidth(0, 50)  # Sıra sütunu genişliği
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Araç / Makine Adı
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Plakası
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Makine No
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Markası
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Model
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Model Yılı
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Hesap Adı
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # Arıza Durumu - esnek
        
        # Tablo minimum genişliği
        self.faulty_vehicles_table.setMinimumWidth(600)
        
        self.faulty_vehicles_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SECONDARY_BG};
                color: {PRIMARY_TEXT};
                border: 1px solid {BORDER_ERROR};
                border-radius: 6px;
                gridline-color: {BORDER_PRIMARY};
                selection-background-color: {ERROR_ACCENT};
                selection-color: {PRIMARY_TEXT};
                font-size: 11px;
                margin: 1px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {BORDER_PRIMARY};
                border-right: 1px solid {BORDER_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {ERROR_ACCENT};
                color: {PRIMARY_TEXT};
            }}
            QTableWidget::item:alternate {{
                background-color: {TERTIARY_BG};
            }}
            QHeaderView::section {{
                background: {ERROR_ACCENT};
                color: {PRIMARY_TEXT};
                padding: 12px 8px;
                border: 1px solid {BORDER_ERROR};
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
        """)
        faulty_layout.addWidget(self.faulty_vehicles_table)
        faulty_group.setLayout(faulty_layout)
        vehicles_layout.addWidget(faulty_group)
        
        layout.addLayout(vehicles_layout)
        
        # Araçları yükle
        self.load_vehicles_for_santiye()
        
        panel.setLayout(layout)
        return panel
    
    def load_data(self):
        """Verileri yükle"""
        records = self.db_manager.get_all_records()
        self.all_records_cache = records
        self.refresh_filters_data(records)
        # Açılışta tarih filtresi kapalı, tüm kayıtlar gösterilsin
        self.apply_filters()
        self.update_statistics()
        
        # Toplam araç sayısını al
        total_vehicles = len(self.db_manager.get_all_araclar())
        
        self.status_bar.showMessage(f"Toplam {len(records)} kayıt, {total_vehicles} araç yüklendi")
        if hasattr(self, 'footer_total'):
            self.footer_total.setText(f"Toplam kayıt: {len(records)} | Toplam araç: {total_vehicles}")

    def refresh_filters_data(self, records):
        """Filtre seçeneklerini kayıtlarla senkronize et"""
        try:
            current_bolge = self.filter_bolge.currentText() if hasattr(self, 'filter_bolge') else None
            current_bakim_yapan = self.filter_bakim_yapan.currentText() if hasattr(self, 'filter_bakim_yapan') else None
            if hasattr(self, 'filter_bolge'):
                bolgeler = sorted({ r[4] for r in records if r[4] not in (None, '') })
                self.filter_bolge.blockSignals(True)
                self.filter_bolge.clear()
                self.filter_bolge.addItem("Tümü")
                for b in bolgeler:
                    self.filter_bolge.addItem(b)
                if current_bolge and current_bolge in ["Tümü"] + bolgeler:
                    self.filter_bolge.setCurrentText(current_bolge)
                self.filter_bolge.blockSignals(False)
            if hasattr(self, 'filter_bakim_yapan'):
                yapanlar = sorted({ r[10] for r in records if r[10] not in (None, '') })
                self.filter_bakim_yapan.blockSignals(True)
                self.filter_bakim_yapan.clear()
                self.filter_bakim_yapan.addItem("Tümü")
                for y in yapanlar:
                    self.filter_bakim_yapan.addItem(y)
                if current_bakim_yapan and current_bakim_yapan in ["Tümü"] + yapanlar:
                    self.filter_bakim_yapan.setCurrentText(current_bakim_yapan)
                self.filter_bakim_yapan.blockSignals(False)
        except Exception:
            pass

    def apply_filters(self):
        """Filtreleri uygulayıp tabloyu güncelle"""
        records = getattr(self, 'all_records_cache', self.db_manager.get_all_records())
        # Tarih aralığı filtresi
        def in_date_range(tarih_str):
            # Tarih filtresi devre dışı ise her kayıt geçer
            if not getattr(self, 'filter_use_date', None) or not self.filter_use_date.isChecked():
                return True
            if not tarih_str:
                return True
            disp, key = normalize_date_display(tarih_str)
            if key == 99999999:
                return True
            start_key = int(self.filter_start.date().toString('yyyyMMdd')) if hasattr(self, 'filter_start') else 0
            end_key = int(self.filter_end.date().toString('yyyyMMdd')) if hasattr(self, 'filter_end') else 99999999
            return start_key <= key <= end_key
        # Bölge ve bakım yapan
        sel_bolge = self.filter_bolge.currentText() if hasattr(self, 'filter_bolge') else 'Tümü'
        sel_yapan = self.filter_bakim_yapan.currentText() if hasattr(self, 'filter_bakim_yapan') else 'Tümü'
        filtered = []
        for r in records:
            if not in_date_range(r[5]):
                continue
            if sel_bolge != 'Tümü' and (r[4] or '') != sel_bolge:
                continue
            if sel_yapan != 'Tümü' and (r[10] or '') != sel_yapan:
                continue
            filtered.append(r)
        self.populate_table(filtered)

    def clear_filters(self):
        if hasattr(self, 'filter_bolge'):
            self.filter_bolge.setCurrentIndex(0)
        if hasattr(self, 'filter_bakim_yapan'):
            self.filter_bakim_yapan.setCurrentIndex(0)
        if hasattr(self, 'filter_start') and hasattr(self, 'filter_end'):
            self.filter_start.setDate(QDate.currentDate().addMonths(-6))
            self.filter_end.setDate(QDate.currentDate())
        if hasattr(self, 'filter_use_date'):
            self.filter_use_date.setChecked(False)
        self.apply_filters()

    def on_toggle_date_filter(self, checked):
        # Tarih alanlarını aktif/pasif göster
        enabled = bool(checked)
        if hasattr(self, 'filter_start'):
            self.filter_start.setEnabled(enabled)
        if hasattr(self, 'filter_end'):
            self.filter_end.setEnabled(enabled)
        self.apply_filters()
    
    def populate_table(self, records):
        """Tabloyu doldur"""
        # Sıralamayı geçici olarak kapat ve içerikleri temizle
        sorting_prev = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(records))
        # Map: veritabanı kolon indeksleri -> tablo kolon indeksleri
        # DB: (0)id,(1)s_no,(2)plaka,(3)kapi_no,(4)bolge,(5)tarih,(6)bakim_km,(7)sonraki_km,(8)yapilan,(9)diger,(10)bakim_yapan,(11)kayit_tarihi
        # UI: [Sıra], [ID gizli], PLAKA, KAPI NO, BÖLGE, TARİH, BAKIM KM, SONRAKI KM, YAPILAN İŞLEM, DİĞER, BAKIMI YAPAN
        db_to_ui = {2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10}
        for row, record in enumerate(records):
            # Sıra numarası sütunu
            sira_item = QTableWidgetItem(str(row + 1))
            sira_item.setFlags(sira_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, sira_item)
            
            # Gizli ID sütununu doldur (seçim ve işlemler için gerekli)
            id_item = QTableWidgetItem(str(record[0]))
            id_item.setData(Qt.ItemDataRole.UserRole, record[0])
            # ID hücresi düzenlenebilir olmasın
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, id_item)
            for db_index, ui_col in db_to_ui.items():
                value = record[db_index]
                # KM kolonları: 6 ve 7 (UI)
                if ui_col in (6, 7):
                    numeric = None
                    if isinstance(value, (int, float)):
                        numeric = int(value)
                    else:
                        try:
                            numeric = int(str(value).replace(" ", "").replace(".", "").replace(",", "")) if value not in (None, "", "-") else None
                        except Exception:
                            numeric = None
                    # Boş, 0 veya negatif ise '-' göster; sıralama değeri 0
                    if numeric is None or numeric <= 0:
                        display_value = "-"
                        sort_role_value = 0
                    else:
                        display_value = format_thousands_dot(numeric)
                        sort_role_value = numeric
                    # Sıralama için sayısal rol ata
                else:
                    display_value = str(value) if value not in (None, "") else "-"
                    sort_role_value = display_value
                    # Tarih kolonunda (UI 4) doğru sıralama için yyyymmdd anahtarı ata
                    if ui_col == 4:
                        disp, key = normalize_date_display(value)
                        display_value = disp
                        sort_role_value = key
                item = QTableWidgetItem()
                # Görüntüyü açıkça string olarak ayarla (dd.MM.yyyy ve noktalı binlik)
                item.setText(display_value)
                item.setData(Qt.ItemDataRole.DisplayRole, display_value)
                item.setData(Qt.ItemDataRole.UserRole, record[0])
                # EditRole'ü görüntü metniyle aynı tutarak ham sayıların görünmesini engelle
                item.setData(Qt.ItemDataRole.EditRole, display_value)
                # Görüntüleme tutarlılığı için hücreleri düzenlenemez yap
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Sütun hizalamaları
                if ui_col in (2, 3, 4, 5):
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter))
                elif ui_col in (6, 7):
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
                else:
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
                # Uzun metinler için tooltip
                if ui_col in (8, 9) and display_value not in (None, "-"):
                    item.setToolTip(str(display_value))
                # Sonraki bakım KM yaklaşınca satır renklendir (ör. fark <= 1000 km)
                if ui_col == 7:
                    try:
                        current_km = int(str(self.table.item(row, 6).text()).replace('.', '')) if self.table.item(row, 6) else None
                        next_km = int(str(item.text()).replace('.', '')) if item.text() not in ('-', '') else None
                        if current_km and next_km and next_km - current_km <= 1000:
                            for c in range(self.table.columnCount()):
                                if self.table.item(row, c):
                                    self.table.item(row, c).setBackground(QColor('#fff3cd'))  # soft yellow
                    except Exception:
                        pass
                self.table.setItem(row, ui_col, item)
        # Önceki sıralama durumunu geri yükle
        self.table.setSortingEnabled(sorting_prev)
    
    def update_statistics(self):
        """İstatistikleri güncelle"""
        stats = self.db_manager.get_statistics()
        
        stats_text = f"""
        📊 Toplam Kayıt: {stats.get('toplam_kayit', 0)}
        🚗 Toplam Araç: {stats.get('toplam_arac', 0)}
        """
        
        if stats.get('en_cok_bakim'):
            stats_text += f"\n🏆 En Çok Bakım: {stats['en_cok_bakim'][0]} ({stats['en_cok_bakim'][1]} bakım)"
        
        if stats.get('son_bakim'):
            stats_text += f"\n📅 Son Bakım: {stats['son_bakim']}"
        
        if hasattr(self, 'stats_label') and self.stats_label is not None:
            self.stats_label.setText(stats_text)
    
    def search_records(self, text=None):
        """Kayıt ara"""
        search_text = (text if isinstance(text, str) else self.search_edit.text()).strip()
        
        if not search_text:
            self.load_data()
            return
        
        records = self.db_manager.search_records(search_text)
        self.populate_table(records)
        self.status_bar.showMessage(f"'{search_text}' için {len(records)} kayıt bulundu")
    
    def add_record(self):
        """Yeni kayıt ekle"""
        dialog = RecordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data[1]:  # Plaka boşsa
                self.show_warning("Uyarı", "Plaka alanı zorunludur!")
                return
            
            # s_no None ise otomatik sırayı ata (mevcut max + 1)
            if data[0] is None:
                try:
                    cursor = self.db_manager.conn.cursor()
                    cursor.execute("SELECT COALESCE(MAX(s_no), 0) + 1 FROM bakimlar")
                    next_no = cursor.fetchone()[0]
                    data = (next_no,) + data[1:]
                except Exception:
                    data = (None,) + data[1:]

            record_id = self.db_manager.add_record(data)
            if record_id:
                self.show_information("Başarılı", "Kayıt başarıyla eklendi!")
                self.load_data()
            else:
                self.show_critical("Hata", "Kayıt eklenirken hata oluştu!")
    
    def edit_record(self):
        """Kayıt düzenle"""
        current_row = self.table.currentRow()
        if current_row < 0:
            self.show_warning("Uyarı", "Lütfen düzenlenecek kaydı seçin!")
            return
        
        # Seçili kaydın ID'sini al (ID sütunu index 1'de)
        item = self.table.item(current_row, 1)
        if not item:
            return
        
        record_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Kaydı veritabanından getir
        records = self.db_manager.get_all_records()
        record_data = None
        for record in records:
            if record[0] == record_id:
                record_data = record
                break
        
        if not record_data:
            self.show_critical("Hata", "Kayıt bulunamadı!")
            return
        
        dialog = RecordDialog(self, record_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data[1]:  # Plaka boşsa
                self.show_warning("Uyarı", "Plaka alanı zorunludur!")
                return
            
            if self.db_manager.update_record(record_id, data):
                self.show_information("Başarılı", "Kayıt başarıyla güncellendi!")
                self.load_data()
            else:
                self.show_critical("Hata", "Kayıt güncellenirken hata oluştu!")
    
    def delete_record(self):
        """Kayıt sil"""
        current_row = self.table.currentRow()
        if current_row < 0:
            self.show_warning("Uyarı", "Lütfen silinecek kaydı seçin!")
            return
        
        # Seçili kaydın ID'sini al (ID sütunu index 1'de)
        item = self.table.item(current_row, 1)
        if not item:
            return
        
        record_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Onay al
        reply = self.show_question("Onay", "Bu kaydı silmek istediğinizden emin misiniz?")
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_record(record_id):
                self.show_information("Başarılı", "Kayıt başarıyla silindi!")
                self.load_data()
            else:
                self.show_critical("Hata", "Kayıt silinirken hata oluştu!")
    
    def delete_all_records(self):
        """Tüm kayıtları sil"""
        reply = self.show_question("Onay", "Tüm kayıtları silmek üzeresiniz. Bu işlem geri alınamaz. Devam edilsin mi?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if self.db_manager.delete_all():
            self.show_information("Başarılı", "Tüm kayıtlar silindi!")
            self.load_data()
        else:
            self.show_critical("Hata", "Toplu silme sırasında hata oluştu!")
    
    def import_excel(self):
        """Excel dosyasından veri aktar"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)"
        )
        
        if not file_path:
            return
        
        try:
            # Excel dosyasını oku (engine otomatik)
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception:
                # openpyxl başarısız olursa varsayılan engine ile dene
                df = pd.read_excel(file_path)
            # Sütunları normalize et ve olabildiğince eşleştir
            df = normalize_columns(df)
            
            # Zorunlu sütunlar (minimum)
            required_min = ['PLAKA']
            missing_min = [col for col in required_min if col not in df.columns]
            if missing_min:
                QMessageBox.critical(
                    self, "Hata",
                    "Excel dosyasında zorunlu sütun bulunamadı: PLAKA\n"
                    "Lütfen dosya başlıklarını kontrol edin."
                )
                return
            
            # Opsiyonel sütunlar için yoksa oluştur
            optional_cols = ['S.NO','KAPI NUMARASI','BÖLGE','TARİH','BAKIM ESNASINDA KM','BİR SONRAKİ BAKIM KM',
                             'YAPILAN İŞLEM','DİĞER','BAKIMI YAPAN']
            for col in optional_cols:
                if col not in df.columns:
                    df[col] = None
            
            # Verileri aktar
            success_count = 0
            for index, row in df.iterrows():
                if pd.isna(row['PLAKA']):
                    continue
                
                # Tarih formatını kesin olarak dd.MM.yyyy'ye çevir
                tarih_raw = row['TARİH'] if 'TARİH' in df.columns else None
                tarih = ensure_ddmmyyyy(tarih_raw)
                
                # KM değerlerini temizle (dayanıklı parser)
                bakim_km = parse_km(row['BAKIM ESNASINDA KM']) if 'BAKIM ESNASINDA KM' in df.columns else None
                sonraki_bakim_km = parse_km(row['BİR SONRAKİ BAKIM KM']) if 'BİR SONRAKİ BAKIM KM' in df.columns else None
                
                # Veritabanına ekle
                data = (
                    None,  # S.NO
                    str(row['PLAKA']),
                    str(row['KAPI NUMARASI']) if 'KAPI NUMARASI' in df.columns and pd.notna(row['KAPI NUMARASI']) else None,
                    str(row['BÖLGE']) if 'BÖLGE' in df.columns and pd.notna(row['BÖLGE']) else None,
                    tarih,
                    bakim_km,
                    sonraki_bakim_km,
                    str(row['YAPILAN İŞLEM']) if 'YAPILAN İŞLEM' in df.columns and pd.notna(row['YAPILAN İŞLEM']) else None,
                    str(row['DİĞER']) if 'DİĞER' in df.columns and pd.notna(row['DİĞER']) else None,
                    str(row['BAKIMI YAPAN']) if 'BAKIMI YAPAN' in df.columns and pd.notna(row['BAKIMI YAPAN']) else None
                )
                
                if self.db_manager.add_record(data):
                    success_count += 1
            
            QMessageBox.information(
                self, "Başarılı", 
                f"{success_count} kayıt başarıyla aktarıldı!"
            )
            self.load_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel aktarım hatası: {str(e)}\n\n"
                                         "Lütfen dosyada hücre birleştirmesi/özel biçim olup olmadığını kontrol edin.")

    def export_excel(self):
        """Mevcut tabloyu Excel dosyasına aktar"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyası Kaydet", "", "Excel Dosyaları (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            # Mevcut filtrelenmiş kayıtları al
            records = getattr(self, 'all_records_cache', self.db_manager.get_all_records())
            if hasattr(self, 'apply_filters'):
                # Filtreleri uygula ve sonucu al
                filtered_records = []
                for r in records:
                    # Tarih filtresi kontrolü
                    if hasattr(self, 'filter_use_date') and self.filter_use_date.isChecked():
                        if not r[5]:  # tarih yoksa geç
                            continue
                        disp, key = normalize_date_display(r[5])
                        if key == 99999999:
                            continue
                        start_key = int(self.filter_start.date().toString('yyyyMMdd'))
                        end_key = int(self.filter_end.date().toString('yyyyMMdd'))
                        if not (start_key <= key <= end_key):
                            continue
                    
                    # Bölge filtresi
                    sel_bolge = self.filter_bolge.currentText() if hasattr(self, 'filter_bolge') else 'Tümü'
                    if sel_bolge != 'Tümü' and (r[4] or '') != sel_bolge:
                        continue
                    
                    # Bakım yapan filtresi
                    sel_yapan = self.filter_bakim_yapan.currentText() if hasattr(self, 'filter_bakim_yapan') else 'Tümü'
                    if sel_yapan != 'Tümü' and (r[10] or '') != sel_yapan:
                        continue
                    
                    filtered_records.append(r)
                records = filtered_records
            
            # DataFrame oluştur
            df_data = []
            for i, record in enumerate(records, 1):
                # DB: (0)id,(1)s_no,(2)plaka,(3)kapi_no,(4)bolge,(5)tarih,(6)bakim_km,(7)sonraki_km,(8)yapilan,(9)diger,(10)bakim_yapan,(11)kayit_tarihi
                df_data.append({
                    'S.NO': i,  # Otomatik sıra numarası
                    'PLAKA': record[2] or '',
                    'KAPI NUMARASI': record[3] or '',
                    'BÖLGE': record[4] or '',
                    'TARİH': record[5] or '',
                    'BAKIM ESNASINDA KM': record[6] or '',
                    'BİR SONRAKİ BAKIM KM': record[7] or '',
                    'YAPILAN İŞLEM': record[8] or '',
                    'DİĞER': record[9] or '',
                    'BAKIMI YAPAN': record[10] or ''
                })
            
            df = pd.DataFrame(df_data)
            
            # Excel'e yaz
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Bakım Kayıtları', index=False)
                
                # Sütun genişliklerini ayarla
                worksheet = writer.sheets['Bakım Kayıtları']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            QMessageBox.information(
                self, "Başarılı", 
                f"{len(records)} kayıt başarıyla Excel dosyasına aktarıldı!\n\nDosya: {file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel dışa aktarım hatası: {str(e)}")

    def apply_dark_theme(self):
        """Uygulamaya koyu tema uygula (varsayılan)."""
        # Koyu palet
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(30, 30, 30))
        palette.setColor(self.foregroundRole(), QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.Window, QColor(30,30,30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(230,230,230))
        palette.setColor(QPalette.ColorRole.Base, QColor(33,33,33))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(38,38,38))
        palette.setColor(QPalette.ColorRole.Text, QColor(230,230,230))
        palette.setColor(QPalette.ColorRole.Button, QColor(45,45,45))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(230,230,230))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0,120,212))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
        self.setPalette(palette)
        # Koyu QSS
        # Uygulamayı aydınlık temaya döndür (dark kaldırıldı)
        self.setPalette(QApplication.instance().palette())
        self.setStyleSheet("""
            QMainWindow { background: #f6f9ff; }
            QGroupBox { border: 1px solid #cfd8e3; color: #ffffff; background:#ffffff; border-radius:10px; }
            QLabel { color: #ffffff; }
            QLineEdit { background: #2c2c2c; color: #ffffff; border: 1px solid #cfd8e3; border-radius:8px; }
            QLineEdit:focus { border-color: #5a6c7d; }
            QPushButton { background-color: #5a6c7d; color: #ffffff; border-radius: 8px; }
            QPushButton:hover { background-color: #1765c1; }
            QTableWidget { background: #2c2c2c; alternate-background-color: #f9fbff; color: #ffffff; border: 1px solid #cfd8e3; }
            QHeaderView::section { background: #eef3ff; color: #ffffff; border: 1px solid #cfd8e3; }
        """)
    
    def check_updates_on_startup(self):
        """Açılışta güncelleme kontrolü"""
        try:
            # Arka planda güncelleme kontrolü
            import threading
            thread = threading.Thread(target=self._check_updates_background)
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Güncelleme kontrolü başlatılamadı: {e}")
    
    def _check_updates_background(self):
        """Arka planda güncelleme kontrolü"""
        try:
            has_update, version, description, url = self.update_manager.check_for_updates()
            if has_update:
                # UI thread'de dialog göster
                QTimer.singleShot(1000, lambda: self.show_update_dialog(version, description, url))
        except Exception as e:
            print(f"Güncelleme kontrolü hatası: {e}")
    
    def show_update_dialog(self, version, description, url):
        """Güncelleme dialog'unu göster"""
        try:
            dialog = UpdateDialog(self, (version, description, url))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.perform_update(url)
        except Exception as e:
            print(f"Güncelleme dialog hatası: {e}")
    
    def perform_update(self, download_url):
        """Güncellemeyi gerçekleştir"""
        try:
            # İndirme progress dialog'u
            progress = QMessageBox(self)
            progress.setWindowTitle("Güncelleme")
            progress.setText("Güncelleme indiriliyor...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()
            QApplication.processEvents()
            
            # Güncellemeyi indir
            success, exe_path = self.update_manager.download_update(download_url)
            
            if success:
                progress.setText("Güncelleme kuruluyor...")
                QApplication.processEvents()
                
                # Güncellemeyi kur
                if self.update_manager.install_update(exe_path):
                    progress.close()
                    QMessageBox.information(
                        self, "Güncelleme Tamamlandı", 
                        "Güncelleme başarıyla tamamlandı!\nProgram yeniden başlatılacak."
                    )
                    # Programı yeniden başlat
                    QApplication.quit()
                else:
                    progress.close()
                    QMessageBox.warning(self, "Güncelleme Hatası", "Güncelleme kurulamadı!")
            else:
                progress.close()
                QMessageBox.warning(self, "İndirme Hatası", "Güncelleme indirilemedi!")
                
        except Exception as e:
            print(f"Güncelleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Güncelleme sırasında hata: {str(e)}")
    
    def manual_check_updates(self):
        """Manuel güncelleme kontrolü"""
        try:
            has_update, version, description, url = self.update_manager.check_for_updates()
            if has_update:
                self.show_update_dialog(version, description, url)
            else:
                QMessageBox.information(self, "Güncelleme", "Güncel sürümü kullanıyorsunuz!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Güncelleme kontrolü hatası: {str(e)}")
    
    def load_vehicles_for_santiye(self, santiye_id=None):
        """Tüm araçları yükle"""
        try:
            if santiye_id:
                araclar = self.db_manager.get_araclar_by_santiye(santiye_id)
            else:
                araclar = self.db_manager.get_all_araclar()
            
            # Aktif araçları filtrele (durum = 'Sağlam')
            active_vehicles = [arac for arac in araclar if arac[9] == 'Sağlam']
            # Arızalı araçları filtrele (durum != 'Sağlam')
            faulty_vehicles = [arac for arac in araclar if arac[9] != 'Sağlam']
            
            # Aktif araçlar tablosunu doldur
            self.active_vehicles_table.setRowCount(len(active_vehicles))
            for row, arac in enumerate(active_vehicles):
                # arac: (id, arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum, ariza_durumu, olusturma_tarihi)
                self.active_vehicles_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # Sıra
                self.active_vehicles_table.setItem(row, 1, QTableWidgetItem(arac[1] or '-'))  # Araç / Makine Adı
                self.active_vehicles_table.setItem(row, 2, QTableWidgetItem(arac[2] or '-'))  # Plakası
                self.active_vehicles_table.setItem(row, 3, QTableWidgetItem(arac[3] or '-'))  # Makine No
                self.active_vehicles_table.setItem(row, 4, QTableWidgetItem(arac[4] or '-'))  # Markası
                self.active_vehicles_table.setItem(row, 5, QTableWidgetItem(arac[5] or '-'))  # Model
                self.active_vehicles_table.setItem(row, 6, QTableWidgetItem(str(arac[6]) if arac[6] else '-'))  # Model Yılı
                self.active_vehicles_table.setItem(row, 7, QTableWidgetItem(arac[7] or '-'))  # Hesap Adı
                self.active_vehicles_table.setItem(row, 8, QTableWidgetItem(arac[9] or '-'))  # Durum
                
                # Araç ID'sini sakla ve sütunları düzenlenemez yap
                for col in range(9):
                    item = self.active_vehicles_table.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        # Sadece ilk sütuna ID kaydet
                        if col == 0:
                            item.setData(Qt.ItemDataRole.UserRole, arac[0])
                        
                        # Sütun hizalaması
                        if col in (0, 2, 3, 6):  # Sıra, Plaka, Makine No, Model Yılı - orta
                            item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter))
                        elif col in (1, 4, 5, 7, 8):  # Araç Adı, Marka, Model, Hesap Adı, Durum - sol
                            item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
            
            # Arızalı araçlar tablosunu doldur
            self.faulty_vehicles_table.setRowCount(len(faulty_vehicles))
            for row, arac in enumerate(faulty_vehicles):
                self.faulty_vehicles_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # Sıra
                self.faulty_vehicles_table.setItem(row, 1, QTableWidgetItem(arac[1] or '-'))  # Araç / Makine Adı
                self.faulty_vehicles_table.setItem(row, 2, QTableWidgetItem(arac[2] or '-'))  # Plakası
                self.faulty_vehicles_table.setItem(row, 3, QTableWidgetItem(arac[3] or '-'))  # Makine No
                self.faulty_vehicles_table.setItem(row, 4, QTableWidgetItem(arac[4] or '-'))  # Markası
                self.faulty_vehicles_table.setItem(row, 5, QTableWidgetItem(arac[5] or '-'))  # Model
                self.faulty_vehicles_table.setItem(row, 6, QTableWidgetItem(str(arac[6]) if arac[6] else '-'))  # Model Yılı
                self.faulty_vehicles_table.setItem(row, 7, QTableWidgetItem(arac[7] or '-'))  # Hesap Adı
                self.faulty_vehicles_table.setItem(row, 8, QTableWidgetItem(arac[9] or '-'))  # Durum
                
                # Araç ID'sini sakla ve sütunları düzenlenemez yap
                for col in range(9):
                    item = self.faulty_vehicles_table.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        # Sadece ilk sütuna ID kaydet
                        if col == 0:
                            item.setData(Qt.ItemDataRole.UserRole, arac[0])
                        
                        # Sütun hizalaması
                        if col in (0, 2, 3, 6):  # Sıra, Plaka, Makine No, Model Yılı - orta
                            item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter))
                        elif col in (1, 4, 5, 7, 8):  # Araç Adı, Marka, Model, Hesap Adı, Durum - sol
                            item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
                        
        except Exception as e:
            print(f"Araç yükleme hatası: {e}")
    
    
    def add_vehicle(self):
        """Yeni araç ekle"""
        dialog = VehicleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data[0]:  # Plaka boşsa
                QMessageBox.warning(self, "Uyarı", "Plaka alanı zorunludur!")
                return
            
            arac_id = self.db_manager.add_arac(
                data[0], data[1], data[2], data[3], data[4], data[5], data[6], 1  # Varsayılan şantiye ID
            )
            
            if arac_id:
                QMessageBox.information(self, "Başarılı", "Araç başarıyla eklendi!")
                self.load_vehicles_for_santiye()
            else:
                QMessageBox.critical(self, "Hata", "Araç eklenirken hata oluştu!")
    
    def show_vehicle_details(self, row, col):
        """Araç detaylarını göster"""
        # Hangi tablodan geldiğini sender() ile tespit et
        sender = self.sender()
        if sender == self.active_vehicles_table:
            table = self.active_vehicles_table
        elif sender == self.faulty_vehicles_table:
            table = self.faulty_vehicles_table
        else:
            return
        
        # ID'yi herhangi bir sütundan al (tüm sütunlarda ID saklanıyor)
        item = table.item(row, 0)  # İlk sütundan al
        if not item:
            return
        
        arac_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Araç bilgilerini al
        araclar = self.db_manager.get_all_araclar()
        arac_data = None
        for arac in araclar:
            if arac[0] == arac_id:
                arac_data = arac
                break
        
        if not arac_data:
            return
        
        # Araç detay dialog'unu göster
        dialog = VehicleDetailDialog(self, arac_data)
        dialog.exec()
    
    def show_vehicle_context_menu(self, position):
        """Araç tablosu için sağ tık menüsü"""
        # Hangi tablodan geldiğini kontrol et
        sender = self.sender()
        if sender == self.active_vehicles_table:
            table = self.active_vehicles_table
        elif sender == self.faulty_vehicles_table:
            table = self.faulty_vehicles_table
        else:
            return
        
        # Seçili satırı kontrol et
        item = table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        
        # Menü oluştur
        menu = QMenu(self)
        
        # Düzenle
        edit_action = QAction("✏️ Düzenle", self)
        edit_action.triggered.connect(lambda: self.edit_vehicle(table, row))
        menu.addAction(edit_action)
        
        # Sil
        delete_action = QAction("🗑️ Sil", self)
        delete_action.triggered.connect(lambda: self.delete_vehicle(table, row))
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        # Yeni araç ekle
        add_action = QAction("➕ Yeni Araç Ekle", self)
        add_action.triggered.connect(self.add_vehicle)
        menu.addAction(add_action)
        
        # Menüyü göster
        menu.exec(table.mapToGlobal(position))
    
    def edit_vehicle(self, table, row):
        """Araç düzenle"""
        item = table.item(row, 0)
        if not item:
            return
        
        arac_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Araç bilgilerini al
        araclar = self.db_manager.get_all_araclar()
        arac_data = None
        for arac in araclar:
            if arac[0] == arac_id:
                arac_data = arac
                break
        
        if not arac_data:
            return
        
        # Araç düzenleme dialog'unu göster
        dialog = VehicleDialog(self, arac_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_vehicles_for_santiye()
    
    def delete_vehicle(self, table, row):
        """Araç sil"""
        item = table.item(row, 0)
        if not item:
            return
        
        arac_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Araç bilgilerini al
        araclar = self.db_manager.get_all_araclar()
        arac_data = None
        for arac in araclar:
            if arac[0] == arac_id:
                arac_data = arac
                break
        
        if not arac_data:
            return
        
        # Onay al
        reply = QMessageBox.question(
            self, "Onay", 
            f"'{arac_data[1]}' adlı araç silinecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Araç sil
                cursor = self.db_manager.conn.cursor()
                cursor.execute("DELETE FROM araclar WHERE id = ?", (arac_id,))
                self.db_manager.conn.commit()
                
                QMessageBox.information(self, "Başarılı", "Araç başarıyla silindi!")
                self.load_vehicles_for_santiye()
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Araç silinirken hata oluştu: {str(e)}")
    
    def add_vehicle(self):
        """Yeni araç ekle"""
        
        dialog = VehicleDialog(self, None, self.current_santiye_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_vehicles_for_santiye()
    
    def manage_santiyeler(self):
        """Şantiye yönetimi dialog'unu aç"""
        dialog = SantiyeManagementDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_santiyeler()
    
    def import_vehicles_excel(self):
        """Araçları Excel'den içe aktar"""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Araç Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)"
        )
        
        if not file_path:
            return
        
        try:
            # Excel dosyasını oku
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception:
                df = pd.read_excel(file_path)
            
            # Sütunları normalize et
            df = normalize_vehicle_columns(df)
            
            # Zorunlu sütunları kontrol et
            required_cols = ['PLAKA']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                QMessageBox.critical(
                    self, "Hata",
                    f"Excel dosyasında zorunlu sütun bulunamadı: {', '.join(missing_cols)}\n"
                    "Lütfen dosya başlıklarını kontrol edin."
                )
                return
            
            # Opsiyonel sütunlar için yoksa oluştur
            optional_cols = ['CINS', 'MARKA', 'MODEL', 'MODEL_YILI', 'YAKIT_ORANI']
            for col in optional_cols:
                if col not in df.columns:
                    df[col] = None
            
            # Verileri aktar
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                if pd.isna(row['PLAKA']):
                    continue
                
                try:
                    # Yakıt oranını temizle
                    yakit_orani = None
                    if 'YAKIT_ORANI' in df.columns and pd.notna(row['YAKIT_ORANI']):
                        try:
                            yakit_orani = float(row['YAKIT_ORANI'])
                        except:
                            yakit_orani = None
                    
                    # Model yılını temizle
                    model_yili = None
                    if 'MODEL_YILI' in df.columns and pd.notna(row['MODEL_YILI']):
                        try:
                            model_yili = int(row['MODEL_YILI'])
                        except:
                            model_yili = None
                    
                    # Araç ekle
                    # Durum sütununu kontrol et
                    durum = str(row['DURUM']) if 'DURUM' in df.columns and pd.notna(row['DURUM']) else 'Sağlam'
                    
                    arac_id = self.db_manager.add_arac_with_status(
                        str(row['ARAC_MAKINE_ADI']) if 'ARAC_MAKINE_ADI' in df.columns and pd.notna(row['ARAC_MAKINE_ADI']) else None,
                        str(row['PLAKA']),
                        str(row['MAKINE_NO']) if 'MAKINE_NO' in df.columns and pd.notna(row['MAKINE_NO']) else None,
                        str(row['MARKA']) if 'MARKA' in df.columns and pd.notna(row['MARKA']) else None,
                        str(row['MODEL']) if 'MODEL' in df.columns and pd.notna(row['MODEL']) else None,
                        model_yili,
                        str(row['HESAP_ADI']) if 'HESAP_ADI' in df.columns and pd.notna(row['HESAP_ADI']) else None,
                        self.current_santiye_id,
                        durum
                    )
                    
                    if arac_id:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    print(f"Araç ekleme hatası (satır {index}): {e}")
            
            # Sonuç mesajı
            message = f"{success_count} araç başarıyla aktarıldı!"
            if error_count > 0:
                message += f"\n{error_count} araç aktarılamadı."
            
            QMessageBox.information(self, "İçe Aktarım Tamamlandı", message)
            self.load_vehicles_for_santiye()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel aktarım hatası: {str(e)}")
    
    def export_vehicles_excel(self):
        """Araçları Excel'e dışa aktar"""
        
        # Dosya kaydetme dialog'u
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Araçları Excel'e Aktar", 
            f"araclar_{self.current_santiye_id}_{QDate.currentDate().toString('yyyy-MM-dd')}.xlsx",
            "Excel Dosyaları (*.xlsx *.xls)"
        )
        
        if not file_path:
            return
        
        try:
            # Araçları getir
            araclar = self.db_manager.get_all_araclar()
            
            if not araclar:
                QMessageBox.information(self, "Bilgi", "Aktarılacak araç bulunamadı!")
                return
            
            # DataFrame oluştur
            data = []
            for arac in araclar:
                # arac: (id, arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum, ariza_durumu, olusturma_tarihi)
                data.append({
                    'Sıra': len(data) + 1,
                    'Araç / Makine Adı': arac[1] or '',
                    'Plakası': arac[2] or '',
                    'Makine No': arac[3] or '',
                    'Markası': arac[4] or '',
                    'Model': arac[5] or '',
                    'Model Yılı': arac[6] or '',
                    'Hesap Adı': arac[7] or '',
                    'Durum': arac[9] or '',
                    'Arıza Durumu': arac[10] or '',
                    'Oluşturma Tarihi': arac[11] or ''
                })
            
            df = pd.DataFrame(data)
            
            # Excel'e yaz
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Araçlar', index=False)
                
                # Sütun genişliklerini ayarla
                worksheet = writer.sheets['Araçlar']
                column_widths = {
                    'A': 8,   # Sıra
                    'B': 25,  # Araç / Makine Adı
                    'C': 15,  # Plakası
                    'D': 15,  # Makine No
                    'E': 15,  # Markası
                    'F': 15,  # Model
                    'G': 12,  # Model Yılı
                    'H': 20,  # Hesap Adı
                    'I': 12,  # Durum
                    'J': 15,  # Arıza Durumu
                    'K': 20   # Oluşturma Tarihi
                }
                
                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width
            
            QMessageBox.information(
                self, "Başarılı", 
                f"{len(araclar)} araç başarıyla Excel dosyasına aktarıldı!\n\nDosya: {file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel dışa aktarım hatası: {str(e)}")
    
    def delete_all_vehicles(self):
        """Tüm araçları sil"""
        
        # Araç sayısını kontrol et
        araclar = self.db_manager.get_all_araclar()
        if not araclar:
            QMessageBox.information(self, "Bilgi", "Bu şantiyede silinecek araç bulunmuyor!")
            return
        
        # Onay al
        reply = QMessageBox.question(
            self, "Onay", 
            f"Bu şantiyedeki TÜM araçları ({len(araclar)} adet) silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Tüm araçları sil
                cursor = self.db_manager.conn.cursor()
                cursor.execute("DELETE FROM araclar WHERE santiye_id = ?", (self.current_santiye_id,))
                self.db_manager.conn.commit()
                
                QMessageBox.information(self, "Başarılı", f"{len(araclar)} araç başarıyla silindi!")
                self.load_vehicles_for_santiye()
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Araçlar silinirken hata oluştu: {str(e)}")
    
    def fix_vehicle_statuses(self):
        """Tüm araçların durumlarını düzelt"""
        
        # Onay al
        reply = QMessageBox.question(
            self, "Onay", 
            "Bu şantiyedeki tüm araçların durumlarını 'Aktif' ve 'Sağlam' olarak düzeltmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Önce mevcut araç sayısını al
                araclar = self.db_manager.get_all_araclar()
                
                # Durumları düzelt
                fixed_count = self.db_manager.fix_all_vehicle_status(self.current_santiye_id)
                
                QMessageBox.information(self, "Başarılı", f"{fixed_count} araçın durumu düzeltildi!")
                self.load_vehicles_for_santiye()
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Durumlar düzeltilirken hata oluştu: {str(e)}")

    def closeEvent(self, event):
        """Pencere kapanırken temizlik"""
        # Normal kapanış işlemi
        event.accept()

# ---------------------- Otomatik Güncelleme Sistemi ----------------------
class UpdateManager:
    """Otomatik güncelleme yönetim sınıfı"""
    
    def __init__(self):
        # Sürüm bilgisini version.py'den al
        try:
            from version import VERSION
            self.current_version = VERSION
        except ImportError:
            self.current_version = "1.0.0"
        
        self.github_repo = "The-Yunis/arac_bakim"  # GitHub repository
        self.update_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        self.download_url = f"https://github.com/{self.github_repo}/releases/latest"
        
    def check_for_updates(self):
        """Güncelleme kontrolü yap"""
        try:
            response = requests.get(self.update_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data['tag_name'].replace('v', '')
                
                if self.is_newer_version(latest_version, self.current_version):
                    return True, latest_version, data['body'], data['html_url']
                return False, None, None, None
            return False, None, None, None
        except Exception as e:
            print(f"Güncelleme kontrolü hatası: {e}")
            return False, None, None, None
    
    def is_newer_version(self, latest, current):
        """Sürüm karşılaştırması"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            for i in range(max(len(latest_parts), len(current_parts))):
                latest_part = latest_parts[i] if i < len(latest_parts) else 0
                current_part = current_parts[i] if i < len(current_parts) else 0
                
                if latest_part > current_part:
                    return True
                elif latest_part < current_part:
                    return False
            return False
        except:
            return False
    
    def download_update(self, download_url):
        """Güncellemeyi indir"""
        try:
            # GitHub'dan son release'i indir
            response = requests.get(download_url, timeout=30)
            if response.status_code == 200:
                # İndirilen dosyayı geçici klasöre kaydet
                temp_dir = "temp_update"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                
                # EXE dosyasını indir (varsayılan olarak)
                exe_url = f"https://github.com/{self.github_repo}/releases/latest/download/AracBakimYonetim.exe"
                exe_response = requests.get(exe_url, timeout=60)
                
                if exe_response.status_code == 200:
                    exe_path = os.path.join(temp_dir, "AracBakimYonetim.exe")
                    with open(exe_path, 'wb') as f:
                        f.write(exe_response.content)
                    return True, exe_path
                return False, None
            return False, None
        except Exception as e:
            print(f"İndirme hatası: {e}")
            return False, None
    
    def install_update(self, exe_path):
        """Güncellemeyi kur"""
        try:
            # Mevcut veritabanını yedekle
            if os.path.exists("bakim_kayitlari.db"):
                shutil.copy("bakim_kayitlari.db", "bakim_kayitlari.db.backup")
            
            # Yeni EXE'yi mevcut konuma kopyala
            current_exe = sys.executable
            if current_exe.endswith('.exe'):
                shutil.copy(exe_path, current_exe)
                return True
            return False
        except Exception as e:
            print(f"Kurulum hatası: {e}")
            return False

class UpdateDialog(QDialog):
    """Güncelleme dialog'u"""
    
    def __init__(self, parent=None, update_info=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setup_ui()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle("Güncelleme Mevcut")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout()
        
        # Başlık
        title = QLabel("🔄 Yeni Sürüm Mevcut!")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Güncelleme bilgileri
        if self.update_info:
            version, description, url = self.update_info
            info_text = f"""
            <b>Yeni Sürüm:</b> {version}<br>
            <b>Açıklama:</b><br>
            {description}<br><br>
            <b>GitHub:</b> <a href="{url}">{url}</a>
            """
            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            info_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 6px;
                    color: #ffffff;
                }
            """)
            layout.addWidget(info_label)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        update_btn = QPushButton("🔄 Güncelle")
        update_btn.clicked.connect(self.accept)
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        later_btn = QPushButton("⏰ Daha Sonra")
        later_btn.clicked.connect(self.reject)
        later_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addWidget(update_btn)
        button_layout.addWidget(later_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class VehicleDialog(QDialog):
    """Araç ekleme dialog'u"""
    
    def __init__(self, parent=None, vehicle_data=None, santiye_id=None):
        super().__init__(parent)
        self.vehicle_data = vehicle_data
        self.santiye_id = santiye_id
        self.setup_ui()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        if self.vehicle_data:
            self.setWindowTitle("Araç Düzenle")
        else:
            self.setWindowTitle("Yeni Araç Ekle")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Araç / Makine Adı
        self.arac_makine_adi_edit = QLineEdit()
        self.arac_makine_adi_edit.setPlaceholderText("Örn: Binek Araç, Greyder, Tır")
        form_layout.addRow("Araç / Makine Adı:", self.arac_makine_adi_edit)
        
        # Plaka
        self.plaka_edit = QLineEdit()
        self.plaka_edit.setPlaceholderText("Örn: 06 ABC 123")
        form_layout.addRow("Plakası *:", self.plaka_edit)
        
        # Makine No
        self.makine_no_edit = QLineEdit()
        self.makine_no_edit.setPlaceholderText("Örn: A28, KE1, 33207")
        form_layout.addRow("Makine No:", self.makine_no_edit)
        
        # Marka
        self.marka_edit = QLineEdit()
        self.marka_edit.setPlaceholderText("Örn: Mercedes, Volvo, Ford")
        form_layout.addRow("Markası:", self.marka_edit)
        
        # Model
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Örn: Actros, G930, Transit")
        form_layout.addRow("Model:", self.model_edit)
        
        # Model Yılı
        self.model_yili_spin = QSpinBox()
        self.model_yili_spin.setRange(1990, 2030)
        self.model_yili_spin.setValue(2020)
        form_layout.addRow("Model Yılı:", self.model_yili_spin)
        
        # Hesap Adı
        self.hesap_adi_edit = QLineEdit()
        self.hesap_adi_edit.setPlaceholderText("Örn: Öztaç Petrol, Hi-Ka İnşaat")
        form_layout.addRow("Hesap Adı:", self.hesap_adi_edit)
        
        layout.addLayout(form_layout)
        
        # Düzenleme modunda verileri doldur
        if self.vehicle_data:
            self.arac_makine_adi_edit.setText(self.vehicle_data[1] or '')
            self.plaka_edit.setText(self.vehicle_data[2] or '')
            self.makine_no_edit.setText(self.vehicle_data[3] or '')
            self.marka_edit.setText(self.vehicle_data[4] or '')
            self.model_edit.setText(self.vehicle_data[5] or '')
            self.model_yili_spin.setValue(self.vehicle_data[6] or 2020)
            self.hesap_adi_edit.setText(self.vehicle_data[7] or '')
        
        # Butonlar
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Stil
        self.setStyleSheet("""
            QDialog {
                background-color: #2c2c2c;
                color: #ffffff;
            }
            QLineEdit, QSpinBox {
                background-color: #2c2c2c;
                color: #ffffff;
                padding: 1px;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                font-size: 11px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #6b8e6b;
            }
            QLabel {
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton {
                background-color: #5a6c7d;
                color: #ffffff;
                border: 1px solid #5a6c7d;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6b8e6b;
                border-color: #6b8e6b;
            }
            QPushButton:pressed {
                background-color: #4a5c6d;
                border-color: #4a5c6d;
            }
        """)
    
    def get_data(self):
        """Form verilerini al"""
        return (
            self.arac_makine_adi_edit.text().strip() or None,
            self.plaka_edit.text().strip(),
            self.makine_no_edit.text().strip() or None,
            self.marka_edit.text().strip() or None,
            self.model_edit.text().strip() or None,
            self.model_yili_spin.value() if self.model_yili_spin.value() > 0 else None,
            self.hesap_adi_edit.text().strip() or None
        )
    
    def accept(self):
        """Dialog'u kabul et ve verileri kaydet"""
        # Plaka kontrolü
        if not self.plaka_edit.text().strip():
            QMessageBox.warning(self, "Uyarı", "Plaka alanı zorunludur!")
            return
        
        # Ana pencereye veri gönder
        if hasattr(self.parent(), 'db_manager'):
            try:
                if self.vehicle_data:
                    # Düzenleme modu
                    cursor = self.parent().db_manager.conn.cursor()
                    data = self.get_data()
                    cursor.execute('''
                        UPDATE araclar SET 
                        arac_makine_adi = ?, plaka = ?, makine_no = ?, 
                        marka = ?, model = ?, model_yili = ?, hesap_adi = ?
                        WHERE id = ?
                    ''', (*data, self.vehicle_data[0]))
                    self.parent().db_manager.conn.commit()
                    QMessageBox.information(self, "Başarılı", "Araç başarıyla güncellendi!")
                else:
                    # Ekleme modu
                    if not self.santiye_id:
                        QMessageBox.warning(self, "Uyarı", "Şantiye ID bulunamadı!")
                        return
                    
                    cursor = self.parent().db_manager.conn.cursor()
                    data = self.get_data()
                    cursor.execute('''
                        INSERT INTO araclar (arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum, ariza_durumu, olusturma_tarihi)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sağlam', 'Aktif', datetime('now'))
                    ''', (*data, self.santiye_id))
                    self.parent().db_manager.conn.commit()
                    QMessageBox.information(self, "Başarılı", "Araç başarıyla eklendi!")
                
                super().accept()
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Veri kaydedilirken hata oluştu: {str(e)}")
        else:
            super().accept()

class VehicleDetailDialog(QDialog):
    """Araç detay dialog'u"""
    
    def __init__(self, parent=None, arac_data=None):
        super().__init__(parent)
        self.arac_data = arac_data
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle("Araç Detayları")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # Araç bilgileri
        info_group = QGroupBox("🚗 Araç Bilgileri")
        info_layout = QFormLayout()
        
        self.plaka_label = QLabel()
        self.arac_makine_adi_label = QLabel()
        self.makine_no_label = QLabel()
        self.marka_label = QLabel()
        self.model_label = QLabel()
        self.model_yili_label = QLabel()
        self.hesap_adi_label = QLabel()
        self.durum_label = QLabel()
        self.ariza_durumu_label = QLabel()
        
        info_layout.addRow("Plaka:", self.plaka_label)
        info_layout.addRow("Araç/Makine Adı:", self.arac_makine_adi_label)
        info_layout.addRow("Makine No:", self.makine_no_label)
        info_layout.addRow("Marka:", self.marka_label)
        info_layout.addRow("Model:", self.model_label)
        info_layout.addRow("Model Yılı:", self.model_yili_label)
        info_layout.addRow("Hesap Adı:", self.hesap_adi_label)
        info_layout.addRow("Durum:", self.durum_label)
        info_layout.addRow("Arıza Durumu:", self.ariza_durumu_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # İşlem butonları
        buttons_layout = QHBoxLayout()
        
        ariza_btn = QPushButton("⚠️ Arıza Bildir")
        ariza_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: #ffffff;
                border: 2px solid #e74c3c;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ec7063, stop:1 #e74c3c);
            }
        """)
        ariza_btn.clicked.connect(self.report_fault)
        
        malzeme_btn = QPushButton("📦 Malzeme Talep")
        malzeme_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f39c12, stop:1 #e67e22);
                color: #ffffff;
                border: 2px solid #f39c12;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f4d03f, stop:1 #f39c12);
            }
        """)
        malzeme_btn.clicked.connect(self.request_material)
        
        bakim_btn = QPushButton("🔧 Bakım Kaydı")
        bakim_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: #ffffff;
                border: 2px solid #3498db;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5dade2, stop:1 #3498db);
            }
        """)
        bakim_btn.clicked.connect(self.create_maintenance_record)
        
        # Bakım kayıtlarını görüntüle butonu
        kayitlar_btn = QPushButton("📋 Bakım Kayıtları")
        kayitlar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9b59b6, stop:1 #8e44ad);
                color: #ffffff;
                border: 2px solid #9b59b6;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #bb8fce, stop:1 #9b59b6);
            }
        """)
        kayitlar_btn.clicked.connect(self.show_maintenance_records)
        
        # Arıza giderildi butonu
        fix_fault_btn = QPushButton("✅ Arıza Giderildi")
        fix_fault_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                color: #ffffff;
                border: 2px solid #27ae60;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2ecc71, stop:1 #27ae60);
            }
        """)
        fix_fault_btn.clicked.connect(self.fix_fault)
        
        buttons_layout.addWidget(ariza_btn)
        buttons_layout.addWidget(malzeme_btn)
        buttons_layout.addWidget(bakim_btn)
        buttons_layout.addWidget(kayitlar_btn)
        buttons_layout.addWidget(fix_fault_btn)
        
        layout.addLayout(buttons_layout)
        
        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
        # Stil
        self.setStyleSheet("""
            QDialog {
                background-color: #2c2c2c;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a6c7d;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #2c2c2c;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
        """)
    
    def load_data(self):
        """Araç verilerini yükle"""
        if not self.arac_data:
            return
        
        # arac_data: (id, arac_makine_adi, plaka, makine_no, marka, model, model_yili, hesap_adi, santiye_id, durum, ariza_durumu, olusturma_tarihi)
        self.plaka_label.setText(self.arac_data[2] or '-')  # plaka
        self.arac_makine_adi_label.setText(self.arac_data[1] or '-')  # arac_makine_adi
        self.makine_no_label.setText(self.arac_data[3] or '-')  # makine_no
        self.marka_label.setText(self.arac_data[4] or '-')  # marka
        self.model_label.setText(self.arac_data[5] or '-')  # model
        self.model_yili_label.setText(str(self.arac_data[6]) if self.arac_data[6] else '-')  # model_yili
        self.hesap_adi_label.setText(self.arac_data[7] or '-')  # hesap_adi
        self.durum_label.setText(self.arac_data[9] or '-')  # durum
        self.ariza_durumu_label.setText(self.arac_data[10] or '-')  # ariza_durumu
    
    def refresh_data(self):
        """Araç verilerini veritabanından yeniden yükle"""
        if not self.arac_data:
            return
        
        try:
            # Veritabanından güncel veriyi al
            main_window = self.parent()
            if main_window and hasattr(main_window, 'db_manager'):
                araclar = main_window.db_manager.get_all_araclar()
                for arac in araclar:
                    if arac[0] == self.arac_data[0]:  # ID eşleşirse
                        self.arac_data = arac
                        self.load_data()  # Verileri yeniden yükle
                        break
        except Exception as e:
            print(f"Veri yenileme hatası: {e}")
    
    def report_fault(self):
        """Arıza bildir"""
        if not self.arac_data:
            return
        
        # Arıza detayları dialog'u
        dialog = ArizaDialog(self, self.arac_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ariza_data = dialog.get_data()
            
            if ariza_data:
                # Araç durumunu arızalı yap
                arac_id = self.arac_data[0]
                if self.parent().db_manager.update_arac_durum(arac_id, 'Arızalı', ariza_data['ariza_detayi']):
                    QMessageBox.information(self, "Başarılı", "Arıza bildirimi kaydedildi! Araç arızalı listesine taşındı.")
                    self.parent().load_vehicles_for_santiye()  # Listeleri yenile
                    self.close()  # Dialog'u kapat
                else:
                    QMessageBox.critical(self, "Hata", "Arıza bildirimi kaydedilemedi!")
    
    def request_material(self):
        """Malzeme talep et"""
        QMessageBox.information(self, "Malzeme Talebi", "Malzeme talep özelliği yakında eklenecek!")
    
    def create_maintenance_record(self):
        """Bakım kaydı oluştur"""
        if not self.arac_data:
            return
        
        # Bakım kaydı dialog'u
        dialog = RecordDialog(self.parent(), None)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data[1]:  # Plaka boşsa
                QMessageBox.warning(self, "Uyarı", "Plaka alanı zorunludur!")
                return
            
            # Bakım kaydını ekle
            if self.parent().db_manager.add_record(data):
                QMessageBox.information(self, "Başarılı", "Bakım kaydı başarıyla eklendi!")
                self.parent().load_data()  # Ana listeyi yenile
                self.close()  # Dialog'u kapat
            else:
                QMessageBox.critical(self, "Hata", "Bakım kaydı eklenirken hata oluştu!")
    
    def fix_fault(self):
        """Arıza giderildi - aracı aktif yap"""
        try:
            if not self.arac_data:
                return
            
            arac_id = self.arac_data[0]  # Araç ID'si
            
            # Ana pencereye erişim
            main_window = self.parent()
            if main_window and hasattr(main_window, 'db_manager'):
                # Araç durumunu 'Sağlam' yap
                success = main_window.db_manager.update_arac_durum(arac_id, 'Sağlam', 'Aktif')
                
                if success:
                    QMessageBox.information(self, "Başarılı", "Araç durumu güncellendi! Araç artık aktif bölümünde görünecek.")
                    # Ana pencereyi yenile
                    if hasattr(main_window, 'load_vehicles_for_santiye'):
                        main_window.load_vehicles_for_santiye()
                    # Dialog verilerini yenile
                    self.refresh_data()
                    # Dialog'u kapatma, kullanıcı güncel veriyi görebilsin
                    # self.accept()
                else:
                    QMessageBox.warning(self, "Hata", "Araç durumu güncellenemedi!")
            else:
                QMessageBox.warning(self, "Hata", "Ana pencereye erişilemedi!")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Arıza giderme işlemi başarısız: {str(e)}")
    
    def show_maintenance_records(self):
        """Araç için bakım kayıtlarını göster"""
        if not self.arac_data:
            return
        
        plaka = self.arac_data[2]  # Plaka bilgisi
        
        # Ana pencereye erişim
        main_window = self.parent()
        if not main_window or not hasattr(main_window, 'db_manager'):
            QMessageBox.warning(self, "Hata", "Ana pencereye erişilemedi!")
            return
        
        # Bakım kayıtlarını getir
        records = main_window.db_manager.get_vehicle_maintenance_records(plaka)
        
        if not records:
            QMessageBox.information(self, "Bilgi", f"Bu araç ({plaka}) için daha önce bakım kaydı açılmamış.")
            return
        
        # Bakım kayıtları dialog'unu göster
        dialog = MaintenanceRecordsDialog(self, plaka, records)
        dialog.exec()

class MaintenanceRecordsDialog(QDialog):
    """Bakım kayıtları görüntüleme dialog'u"""
    
    def __init__(self, parent=None, plaka="", records=None):
        super().__init__(parent)
        self.plaka = plaka
        self.records = records or []
        self.setup_ui()
        self.load_records()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle(f"Bakım Kayıtları - {self.plaka}")
        self.setModal(True)
        self.resize(1200, 700)
        
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel(f"🚗 {self.plaka} - Bakım Kayıtları")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #ecf0f1;
                padding: 10px;
                background-color: #34495e;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Dışa aktarma butonları
        export_layout = QHBoxLayout()
        
        pdf_btn = QPushButton("📄 PDF Dışa Aktar")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: #ffffff;
                border: 2px solid #e74c3c;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ec7063, stop:1 #e74c3c);
            }
        """)
        pdf_btn.clicked.connect(self.export_to_pdf)
        
        excel_btn = QPushButton("📊 Excel Dışa Aktar")
        excel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                color: #ffffff;
                border: 2px solid #27ae60;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2ecc71, stop:1 #27ae60);
            }
        """)
        excel_btn.clicked.connect(self.export_to_excel)
        
        export_layout.addWidget(pdf_btn)
        export_layout.addWidget(excel_btn)
        export_layout.addStretch()
        
        layout.addLayout(export_layout)
        
        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Sıra", "Tarih", "Bakım KM", "Sonraki Bakım KM", 
            "Yapılan İşlem", "Bölge", "Kapı No", "Bakım Yapan"
        ])
        
        # Tablo stilleri (Dark Mode)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                gridline-color: #34495e;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #34495e;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #34495e;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Sütun genişlikleri
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Sıra
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Tarih
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Bakım KM
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Sonraki Bakım KM
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Yapılan İşlem - Esnek
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Bölge
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Kapı No
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Bakım Yapan
        
        # Yapılan İşlem sütununa minimum genişlik ver
        self.table.setColumnWidth(4, 300)  # Yapılan İşlem sütunu için minimum 300px
        
        layout.addWidget(self.table)
        
        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def load_records(self):
        """Bakım kayıtlarını tabloya yükle"""
        self.table.setRowCount(len(self.records))
        
        for row, record in enumerate(self.records):
            # Sıra numarası
            self.table.setItem(row, 0, QTableWidgetItem(str(record[1] or "")))
            
            # Tarih
            tarih = record[5] if record[5] else ""
            if tarih and len(tarih) == 8 and tarih.isdigit():
                # DDMMYYYY formatını YYYY-MM-DD'ye çevir
                formatted_date = f"{tarih[4:8]}-{tarih[2:4]}-{tarih[0:2]}"
                self.table.setItem(row, 1, QTableWidgetItem(formatted_date))
            else:
                self.table.setItem(row, 1, QTableWidgetItem(tarih))
            
            # Bakım KM
            self.table.setItem(row, 2, QTableWidgetItem(str(record[6] or "")))
            
            # Sonraki Bakım KM
            self.table.setItem(row, 3, QTableWidgetItem(str(record[7] or "")))
            
            # Yapılan İşlem
            self.table.setItem(row, 4, QTableWidgetItem(str(record[8] or "")))
            
            # Bölge
            self.table.setItem(row, 5, QTableWidgetItem(str(record[4] or "")))
            
            # Kapı No
            self.table.setItem(row, 6, QTableWidgetItem(str(record[3] or "")))
            
            # Bakım Yapan
            self.table.setItem(row, 7, QTableWidgetItem(str(record[10] or "")))
            
            # Sütun hizalaması
            for col in range(8):
                item = self.table.item(row, col)
                if item:
                    if col in (0, 1, 2, 3, 6):  # Sıra, Tarih, KM'ler, Kapı No - orta
                        item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter))
                    else:  # Diğerleri - sol
                        item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
    
    def export_to_pdf(self):
        """Bakım kayıtlarını PDF olarak dışa aktar - Modern ve Profesyonel"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            from PyQt6.QtCore import QTextStream, Qt
            from PyQt6.QtGui import QTextDocument, QTextCursor, QTextCharFormat, QFont, QTextTableFormat, QTextLength, QTextFrameFormat, QTextBlockFormat, QPageLayout
            from PyQt6.QtCore import QMarginsF
            
            # Dosya seçimi
            file_path, _ = QFileDialog.getSaveFileName(
                self, "PDF Olarak Kaydet", 
                f"{self.plaka}_bakim_kayitlari.pdf", 
                "PDF Dosyaları (*.pdf)"
            )
            
            if not file_path:
                return
            
            # PDF oluştur
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            # PyQt6'da sayfa boyutu ayarları - basit yaklaşım
            try:
                printer.setPageSize(QPrinter.PageSize.A4)
            except:
                # PyQt6'da farklı kullanım
                pass
            printer.setPageMargins(QMarginsF(1, 1, 1, 1), QPageLayout.Unit.Millimeter)
            
            # Doküman oluştur
            doc = QTextDocument()
            cursor = QTextCursor(doc)
            
            # Ana başlık - Sola dayalı
            title_format = QTextCharFormat()
            title_font = QFont("Arial", 20, QFont.Weight.Bold)
            title_format.setFont(title_font)
            title_format.setForeground(Qt.GlobalColor.darkBlue)
            
            # Sola dayalı blok formatı
            block_format = QTextBlockFormat()
            block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cursor.insertBlock(block_format)
            cursor.insertText("🚗 ARAÇ BAKIM RAPORU\n", title_format)
            
            # Alt başlık - Sola dayalı
            subtitle_format = QTextCharFormat()
            subtitle_font = QFont("Arial", 14, QFont.Weight.Normal)
            subtitle_format.setFont(subtitle_font)
            subtitle_format.setForeground(Qt.GlobalColor.darkGray)
            
            # Sola dayalı blok formatı
            block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cursor.insertBlock(block_format)
            cursor.insertText(f"Plaka: {self.plaka}\n", subtitle_format)
            cursor.insertText(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n", subtitle_format)
            
            # Özet bilgiler - Sola dayalı
            summary_format = QTextCharFormat()
            summary_font = QFont("Arial", 10, QFont.Weight.Normal)
            summary_format.setFont(summary_font)
            summary_format.setForeground(Qt.GlobalColor.black)
            
            # Sola dayalı blok formatı
            block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cursor.insertBlock(block_format)
            cursor.insertText(f"📊 Toplam Bakım Kayıt Sayısı: {len(self.records)}\n", summary_format)
            
            # En son bakım tarihi
            if self.records:
                last_maintenance = self.records[0][5] if self.records[0][5] else "Bilinmiyor"
                if last_maintenance and len(last_maintenance) == 8 and last_maintenance.isdigit():
                    formatted_date = f"{last_maintenance[4:8]}-{last_maintenance[2:4]}-{last_maintenance[0:2]}"
                else:
                    formatted_date = last_maintenance
                cursor.insertText(f"📅 Son Bakım Tarihi: {formatted_date}\n\n", summary_format)
            
            # Tablo oluştur
            table_format = QTextTableFormat()
            table_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
            table_format.setCellPadding(4)
            table_format.setCellSpacing(0)
            table_format.setBorder(1)
            # PyQt6'da BorderStyle farklı kullanım
            try:
                table_format.setBorderStyle(QTextTableFormat.BorderStyle.Solid)
            except:
                # PyQt6'da farklı kullanım
                pass
            
            # Sütun genişlikleri - Sıra sütunu kaldırıldı, A4'e tam sığacak
            column_widths = [
                QTextLength(QTextLength.Type.FixedLength, 100),  # Tarih
                QTextLength(QTextLength.Type.FixedLength, 100), # Bakım KM
                QTextLength(QTextLength.Type.FixedLength, 120), # Sonraki Bakım KM
                QTextLength(QTextLength.Type.FixedLength, 250), # Yapılan İşlem - En geniş
                QTextLength(QTextLength.Type.FixedLength, 100),  # Bölge
                QTextLength(QTextLength.Type.FixedLength, 80),   # Kapı No
                QTextLength(QTextLength.Type.FixedLength, 120)   # Bakım Yapan
            ]
            table_format.setColumnWidthConstraints(column_widths)
            
            table = cursor.insertTable(len(self.records) + 1, 7, table_format)
            
            # Başlık satırı
            header_format = QTextCharFormat()
            header_font = QFont("Arial", 10, QFont.Weight.Bold)
            header_format.setFont(header_font)
            header_format.setForeground(Qt.GlobalColor.white)
            header_format.setBackground(Qt.GlobalColor.darkBlue)
            
            headers = ["Tarih", "Bakım KM", "Sonraki Bakım KM", "Yapılan İşlem", "Bölge", "Kapı No", "Bakım Yapan"]
            for i, header in enumerate(headers):
                cell = table.cellAt(0, i)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(header, header_format)
            
            # Veri satırları
            data_format = QTextCharFormat()
            data_font = QFont("Arial", 9, QFont.Weight.Normal)
            data_format.setFont(data_font)
            data_format.setForeground(Qt.GlobalColor.black)
            
            for row, record in enumerate(self.records, 1):
                # Tarih
                cell = table.cellAt(row, 0)
                cell_cursor = cell.firstCursorPosition()
                tarih = record[5] if record[5] else ""
                if tarih and len(tarih) == 8 and tarih.isdigit():
                    formatted_date = f"{tarih[4:8]}-{tarih[2:4]}-{tarih[0:2]}"
                else:
                    formatted_date = tarih
                cell_cursor.insertText(formatted_date, data_format)
                
                # Bakım KM
                cell = table.cellAt(row, 1)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(str(record[6] or ""), data_format)
                
                # Sonraki Bakım KM
                cell = table.cellAt(row, 2)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(str(record[7] or ""), data_format)
                
                # Yapılan İşlem (tam metin - çok geniş sütun)
                cell = table.cellAt(row, 3)
                cell_cursor = cell.firstCursorPosition()
                islem_text = str(record[8] or "")
                # Metin kaydırma yok - çok geniş sütun
                # 250px genişlikte sütun için metin kaydırma yapmıyoruz
                # Tüm metin tek satırda kalacak
                cell_cursor.insertText(islem_text, data_format)
                
                # Bölge
                cell = table.cellAt(row, 4)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(str(record[4] or ""), data_format)
                
                # Kapı No
                cell = table.cellAt(row, 5)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(str(record[3] or ""), data_format)
                
                # Bakım Yapan
                cell = table.cellAt(row, 6)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(str(record[10] or ""), data_format)
            
            # Alt bilgi - Sola dayalı
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n\n")
            
            footer_format = QTextCharFormat()
            footer_font = QFont("Arial", 8, QFont.Weight.Normal)
            footer_format.setFont(footer_font)
            footer_format.setForeground(Qt.GlobalColor.gray)
            
            # Sola dayalı blok formatı
            block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cursor.insertBlock(block_format)
            cursor.insertText("📋 Bu rapor Araç Bakım Yönetim Sistemi tarafından otomatik olarak oluşturulmuştur.\n", footer_format)
            cursor.insertText(f"🕒 Rapor Oluşturma Zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n", footer_format)
            
            # PDF'e yazdır
            doc.print(printer)
            QMessageBox.information(self, "Başarılı", f"Profesyonel PDF raporu başarıyla oluşturuldu:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulurken hata oluştu:\n{str(e)}")
    
    def export_to_excel(self):
        """Bakım kayıtlarını Excel olarak dışa aktar"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            # Dosya seçimi
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Excel Olarak Kaydet", 
                f"{self.plaka}_bakim_kayitlari.xlsx", 
                "Excel Dosyaları (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # Veri hazırla
            data = []
            for record in self.records:
                # Tarih formatını düzelt
                tarih = record[5] if record[5] else ""
                if tarih and len(tarih) == 8 and tarih.isdigit():
                    formatted_date = f"{tarih[4:8]}-{tarih[2:4]}-{tarih[0:2]}"
                else:
                    formatted_date = tarih
                
                data.append({
                    'Sıra': record[1] or "",
                    'Tarih': formatted_date,
                    'Bakım KM': record[6] or "",
                    'Sonraki Bakım KM': record[7] or "",
                    'Yapılan İşlem': record[8] or "",
                    'Bölge': record[4] or "",
                    'Kapı No': record[3] or "",
                    'Bakım Yapan': record[10] or ""
                })
            
            # DataFrame oluştur ve Excel'e yaz
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            QMessageBox.information(self, "Başarılı", f"Excel dosyası başarıyla oluşturuldu:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel oluşturulurken hata oluştu:\n{str(e)}")

class SantiyeManagementDialog(QDialog):
    """Şantiye yönetimi dialog'u"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.load_santiyeler()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle("Şantiye Yönetimi")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel("🏗️ Şantiye Yönetimi")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c2c2c, stop:1 #2c2c2c);
                border-radius: 10px;
                border: 2px solid #5a6c7d;
            }
        """)
        layout.addWidget(title_label)
        
        # Şantiye ekleme formu
        add_group = QGroupBox("➕ Yeni Şantiye Ekle")
        add_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 2px solid #27ae60;
                border-radius: 10px;
                background: #2c2c2c;
                font-weight: bold;
                font-size: 11px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #2c2c2c;
                border-radius: 4px;
            }
        """)
        add_layout = QFormLayout()
        
        self.santiye_adi_edit = QLineEdit()
        self.santiye_adi_edit.setPlaceholderText("Örn: İstanbul Şantiyesi")
        add_layout.addRow("Şantiye Adı *:", self.santiye_adi_edit)
        
        self.lokasyon_edit = QLineEdit()
        self.lokasyon_edit.setPlaceholderText("Örn: İstanbul, Kadıköy")
        add_layout.addRow("Lokasyon:", self.lokasyon_edit)
        
        self.sorumlu_edit = QLineEdit()
        self.sorumlu_edit.setPlaceholderText("Örn: Yunus AFŞİN")
        add_layout.addRow("Sorumlu:", self.sorumlu_edit)
        
        add_btn = QPushButton("➕ Şantiye Ekle")
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b8e6b, stop:1 #6b8e6b);
                color: #ffffff;
                border: 2px solid #6b8e6b;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b8e6b, stop:1 #6b8e6b);
            }
        """)
        add_btn.clicked.connect(self.add_santiye)
        add_layout.addRow("", add_btn)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # Mevcut şantiyeler listesi
        list_group = QGroupBox("📋 Mevcut Şantiyeler")
        list_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 2px solid #3498db;
                border-radius: 10px;
                background: #2c2c2c;
                font-weight: bold;
                font-size: 11px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #2c2c2c;
                border-radius: 4px;
            }
        """)
        list_layout = QVBoxLayout()
        
        self.santiyeler_table = QTableWidget(0, 4)
        self.santiyeler_table.setHorizontalHeaderLabels(["Şantiye Adı", "Lokasyon", "Sorumlu", "Durum"])
        self.santiyeler_table.setAlternatingRowColors(True)
        self.santiyeler_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.santiyeler_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.santiyeler_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.santiyeler_table.customContextMenuRequested.connect(self.show_context_menu)
        self.santiyeler_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SECONDARY_BG};
                color: {PRIMARY_TEXT};
                border: 1px solid {BORDER_ACCENT};
                border-radius: 6px;
                gridline-color: {BORDER_PRIMARY};
                selection-background-color: {PRIMARY_ACCENT};
                selection-color: {PRIMARY_TEXT};
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {BORDER_PRIMARY};
                border-right: 1px solid {BORDER_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
            }}
            QTableWidget::item:alternate {{
                background-color: {TERTIARY_BG};
            }}
            QHeaderView::section {{
                background: {PRIMARY_ACCENT};
                color: {PRIMARY_TEXT};
                padding: 12px 8px;
                border: 1px solid {BORDER_ACCENT};
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
        """)
        list_layout.addWidget(self.santiyeler_table)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def load_santiyeler(self):
        """Şantiyeleri yükle"""
        try:
            santiyeler = self.parent.db_manager.get_all_santiyeler()
            self.santiyeler_table.setRowCount(len(santiyeler))
            
            for row, santiye in enumerate(santiyeler):
                # santiye: (id, santiye_adi, lokasyon, sorumlu, durum, olusturma_tarihi)
                self.santiyeler_table.setItem(row, 0, QTableWidgetItem(santiye[1] or '-'))
                self.santiyeler_table.setItem(row, 1, QTableWidgetItem(santiye[2] or '-'))
                self.santiyeler_table.setItem(row, 2, QTableWidgetItem(santiye[3] or '-'))
                self.santiyeler_table.setItem(row, 3, QTableWidgetItem(santiye[4] or '-'))
                
                # Şantiye ID'sini sakla
                for col in range(4):
                    item = self.santiyeler_table.item(row, col)
                    if item:
                        item.setData(Qt.ItemDataRole.UserRole, santiye[0])
                        
        except Exception as e:
            print(f"Şantiye yükleme hatası: {e}")
    
    def add_santiye(self):
        """Yeni şantiye ekle"""
        santiye_adi = self.santiye_adi_edit.text().strip()
        if not santiye_adi:
            QMessageBox.warning(self, "Uyarı", "Şantiye adı zorunludur!")
            return
        
        lokasyon = self.lokasyon_edit.text().strip() or None
        sorumlu = self.sorumlu_edit.text().strip() or None
        
        santiye_id = self.parent.db_manager.add_santiye(santiye_adi, lokasyon, sorumlu)
        
        if santiye_id:
            QMessageBox.information(self, "Başarılı", "Şantiye başarıyla eklendi!")
            self.santiye_adi_edit.clear()
            self.lokasyon_edit.clear()
            self.sorumlu_edit.clear()
            self.load_santiyeler()
        else:
            QMessageBox.critical(self, "Hata", "Şantiye eklenirken hata oluştu!")
    
    def show_context_menu(self, pos):
        """Sağ tık menüsü göster"""
        index = self.santiyeler_table.indexAt(pos)
        if not index.isValid():
            return
        
        self.santiyeler_table.selectRow(index.row())
        
        menu = QMenu(self)
        
        edit_action = QAction("✏️ Düzenle", self)
        edit_action.triggered.connect(self.edit_santiye)
        menu.addAction(edit_action)
        
        delete_action = QAction("🗑️ Sil", self)
        delete_action.triggered.connect(self.delete_santiye)
        menu.addAction(delete_action)
        
        menu.exec(self.santiyeler_table.viewport().mapToGlobal(pos))
    
    def edit_santiye(self):
        """Şantiye düzenle"""
        current_row = self.santiyeler_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlenecek şantiyeyi seçin!")
            return
        
        # Seçili şantiyenin bilgilerini al
        santiye_adi = self.santiyeler_table.item(current_row, 0).text()
        lokasyon = self.santiyeler_table.item(current_row, 1).text()
        sorumlu = self.santiyeler_table.item(current_row, 2).text()
        santiye_id = self.santiyeler_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Düzenleme dialog'u
        dialog = SantiyeEditDialog(self, santiye_id, santiye_adi, lokasyon, sorumlu, self.parent.parent.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_santiyeler()
    
    def delete_santiye(self):
        """Şantiye sil"""
        current_row = self.santiyeler_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek şantiyeyi seçin!")
            return
        
        santiye_adi = self.santiyeler_table.item(current_row, 0).text()
        santiye_id = self.santiyeler_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Onay al
        reply = QMessageBox.question(
            self, "Onay", 
            f"'{santiye_adi}' şantiyesini silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.parent.db_manager.delete_santiye(santiye_id)
            if success:
                QMessageBox.information(self, "Başarılı", message)
                self.load_santiyeler()
            else:
                QMessageBox.warning(self, "Uyarı", message)

class SantiyeEditDialog(QDialog):
    """Şantiye düzenleme dialog'u"""
    
    def __init__(self, parent=None, santiye_id=None, santiye_adi="", lokasyon="", sorumlu="", db_manager=None):
        super().__init__(parent)
        self.santiye_id = santiye_id
        self.db_manager = db_manager
        self.setup_ui()
        self.load_data(santiye_adi, lokasyon, sorumlu)
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle("Şantiye Düzenle")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel("✏️ Şantiye Düzenle")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #fff3cd, stop:1 #ffeaa7);
                border-radius: 10px;
                border: 2px solid #ffc107;
            }
        """)
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Şantiye Adı
        self.santiye_adi_edit = QLineEdit()
        self.santiye_adi_edit.setPlaceholderText("Örn: İstanbul Şantiyesi")
        form_layout.addRow("Şantiye Adı *:", self.santiye_adi_edit)
        
        # Lokasyon
        self.lokasyon_edit = QLineEdit()
        self.lokasyon_edit.setPlaceholderText("Örn: İstanbul, Kadıköy")
        form_layout.addRow("Lokasyon:", self.lokasyon_edit)
        
        # Sorumlu
        self.sorumlu_edit = QLineEdit()
        self.sorumlu_edit.setPlaceholderText("Örn: Yunus AFŞİN")
        form_layout.addRow("Sorumlu:", self.sorumlu_edit)
        
        layout.addLayout(form_layout)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Kaydet")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #20c997);
                color: #ffffff;
                border: 2px solid #28a745;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
        """)
        save_btn.clicked.connect(self.save_santiye)
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: #ffffff;
                border: 2px solid #dc3545;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #dc3545);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Stil
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLineEdit {
                padding: 1px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #5a6c7d;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
        """)
    
    def load_data(self, santiye_adi, lokasyon, sorumlu):
        """Mevcut verileri yükle"""
        self.santiye_adi_edit.setText(santiye_adi)
        self.lokasyon_edit.setText(lokasyon)
        self.sorumlu_edit.setText(sorumlu)
    
    def save_santiye(self):
        """Şantiye kaydet"""
        santiye_adi = self.santiye_adi_edit.text().strip()
        if not santiye_adi:
            QMessageBox.warning(self, "Uyarı", "Şantiye adı zorunludur!")
            return
        
        lokasyon = self.lokasyon_edit.text().strip() or None
        sorumlu = self.sorumlu_edit.text().strip() or None
        
        success = self.db_manager.update_santiye(
            self.santiye_id, santiye_adi, lokasyon, sorumlu
        )
        
        if success:
            QMessageBox.information(self, "Başarılı", "Şantiye başarıyla güncellendi!")
            self.accept()
        else:
            QMessageBox.critical(self, "Hata", "Şantiye güncellenirken hata oluştu!")


class ArizaDialog(QDialog):
    """Arıza bildirimi dialog'u"""
    
    def __init__(self, parent=None, arac_data=None):
        super().__init__(parent)
        self.arac_data = arac_data
        self.setup_ui()
    
    def setup_ui(self):
        """Dialog arayüzünü ayarla"""
        self.setWindowTitle("⚠️ Arıza Bildirimi")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Araç bilgisi
        arac_info = QLabel(f"🚗 {self.arac_data[2]} - {self.arac_data[1]}")
        arac_info.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background: #ecf0f1;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(arac_info)
        
        # Arıza türü
        ariza_turu_group = QGroupBox("🔧 Arıza Türü")
        ariza_turu_layout = QVBoxLayout()
        
        self.ariza_turu_combo = QComboBox()
        self.ariza_turu_combo.addItems([
            "Motor Arızası",
            "Fren Sistemi",
            "Elektrik Arızası",
            "Lastik Arızası",
            "Klima Sistemi",
            "Transmisyon",
            "Süspansiyon",
            "Diğer"
        ])
        self.ariza_turu_combo.setStyleSheet("""
            QComboBox {
                padding: 1px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 12px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        ariza_turu_layout.addWidget(self.ariza_turu_combo)
        ariza_turu_group.setLayout(ariza_turu_layout)
        layout.addWidget(ariza_turu_group)
        
        # Arıza detayları
        ariza_detay_group = QGroupBox("📝 Arıza Detayları")
        ariza_detay_layout = QVBoxLayout()
        
        self.ariza_detay_text = QTextEdit()
        self.ariza_detay_text.setPlaceholderText("Arızanın detaylı açıklamasını yazın...")
        self.ariza_detay_text.setStyleSheet("""
            QTextEdit {
                padding: 1px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 12px;
                min-height: 100px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        ariza_detay_layout.addWidget(self.ariza_detay_text)
        ariza_detay_group.setLayout(ariza_detay_layout)
        layout.addWidget(ariza_detay_group)
        
        # Aciliyet
        aciliyet_group = QGroupBox("⚡ Aciliyet Durumu")
        aciliyet_layout = QHBoxLayout()
        
        self.aciliyet_radio1 = QRadioButton("🟢 Düşük")
        self.aciliyet_radio2 = QRadioButton("🟡 Orta")
        self.aciliyet_radio3 = QRadioButton("🔴 Yüksek")
        self.aciliyet_radio2.setChecked(True)  # Varsayılan orta
        
        aciliyet_layout.addWidget(self.aciliyet_radio1)
        aciliyet_layout.addWidget(self.aciliyet_radio2)
        aciliyet_layout.addWidget(self.aciliyet_radio3)
        aciliyet_group.setLayout(aciliyet_layout)
        layout.addWidget(aciliyet_group)
        
        # Butonlar
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #7f8c8d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        submit_btn = QPushButton("✅ Arıza Bildir")
        submit_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        submit_btn.clicked.connect(self.submit_ariza)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(submit_btn)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def get_data(self):
        """Dialog verilerini al"""
        ariza_turu = self.ariza_turu_combo.currentText()
        ariza_detayi = self.ariza_detay_text.toPlainText().strip()
        
        if not ariza_detayi:
            QMessageBox.warning(self, "Uyarı", "Lütfen arıza detaylarını yazın!")
            return None
        
        # Aciliyet seviyesi
        if self.aciliyet_radio1.isChecked():
            aciliyet = "Düşük"
        elif self.aciliyet_radio2.isChecked():
            aciliyet = "Orta"
        else:
            aciliyet = "Yüksek"
        
        return {
            'ariza_turu': ariza_turu,
            'ariza_detayi': ariza_detayi,
            'aciliyet': aciliyet,
            'tarih': QDateTime.currentDateTime().toString('dd.MM.yyyy hh:mm')
        }
    
    def submit_ariza(self):
        """Arıza bildirimini gönder"""
        data = self.get_data()
        if data:
            self.accept()


def main():
    """Ana fonksiyon"""
    app = QApplication(sys.argv)
    
    # Uygulama ayarları
    app.setApplicationName("Araç Bakım Kayıtları Yönetim Sistemi")
    app.setApplicationVersion("1.0")
    
    # Ana pencere
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


