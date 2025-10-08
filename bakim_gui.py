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
# GitHub entegrasyonu kaldırıldı - bağımsız çalışma için
import requests  # Güncelleme sistemi için
import json      # JSON işlemleri için
import shutil    # Dosya kopyalama için
import subprocess # Sistem komutları için
import base64    # GitHub API için base64 encoding
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit, QMessageBox,
    QTabWidget, QGroupBox, QFrame, QSplitter, QHeaderView, QAbstractItemView,
    QFileDialog, QProgressBar, QStatusBar, QMenuBar, QMenu, QDialog,
    QDialogButtonBox, QFormLayout, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QAction, QPixmap

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

class ModernTableWidget(QTableWidget):
    """Modern tablo widget'ı"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Tablo arayüzünü ayarla"""
        # Tablo ayarları
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        
        # Sütun başlıkları
        headers = [
            "ID", "PLAKA", "KAPI NO", "BÖLGE", "TARİH", 
            "BAKIM KM", "SONRAKI KM", "YAPILAN İŞLEM", "DİĞER", "BAKIMI YAPAN"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Sütun genişlikleri
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # PLAKA
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # KAPI NO
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # BÖLGE
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # TARİH
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # BAKIM KM
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # SONRAKI KM
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)           # YAPILAN İŞLEM
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # DİĞER
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # BAKIMI YAPAN
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setColumnWidth(0, 50)   # ID
        self.setColumnWidth(1, 120)  # PLAKA minimum
        self.setColumnWidth(2, 100)  # KAPI NO
        self.setColumnWidth(3, 110)  # BÖLGE minimum
        self.setColumnWidth(4, 120)  # TARİH minimum
        self.setColumnWidth(5, 110)  # BAKIM KM min
        self.setColumnWidth(6, 120)  # SONRAKI KM min
        
        # Satır yüksekliği
        self.verticalHeader().setDefaultSectionSize(35)
        # ID sütununu gizle (tabloya yine yazacağız, seçimlerde kullanacağız)
        self.setColumnHidden(0, True)
        
        # Stil (Excel benzeri, koyu temayla uyumlu)
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #cfcfcf;
                background-color: #ffffff;
                alternate-background-color: #f9f9f9;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
                border: 1px solid #cfcfcf;
                border-radius: 6px;
                color: #222;
            }
            QTableWidget::item { padding: 6px; border: none; }
            QHeaderView::section {
                background-color: #f1f1f1;
                padding: 8px;
                border: 1px solid #d7d7d7;
                font-weight: bold;
                color: #222;
            }
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
                background-color: white;
            }
            QLineEdit, QSpinBox, QDateEdit, QTextEdit {
                padding: 8px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #0078d4;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
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
        self.setup_ui()
        self.load_data()
        # Açılışta güncelleme kontrolü (arka planda)
        self.check_updates_on_startup()
    
    def setup_ui(self):
        """Ana pencere arayüzünü ayarla"""
        self.setWindowTitle("Araç Bakım Yönetim Sistemi")
        self.setGeometry(100, 100, 1400, 800)
        
        # Merkez widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Ana layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Üst toolbar
        self.create_toolbar(main_layout)
        
        # Ana içerik (sidebar kaldırıldı)
        content_layout = QHBoxLayout()
        
        # Sol panel kaldırıldı (eski sidebar)
        
        # Sağ panel - Sekmeler (Kayıtlar + Dashboard)
        right_tabs = QTabWidget()
        right_tabs.setTabPosition(QTabWidget.TabPosition.North)
        right_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; } 
            QTabBar::tab { background: #2b2b2b; color: #e6e6e6; padding: 8px 16px; margin-right: 2px; }
            QTabBar::tab:selected { background: #3a3a3a; }
        """)
        # Kayıtlar sekmesi
        records_panel = self.create_right_panel()
        right_tabs.addTab(records_panel, "Kayıtlar")
        # Dashboard sekmesi
        dashboard_panel = self.create_dashboard_panel()
        right_tabs.addTab(dashboard_panel, "Dashboard")
        content_layout.addWidget(right_tabs, 3)
        
        main_layout.addLayout(content_layout)
        
        # Status bar en altta; footer içeriklerini status bar'a taşı
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet('QStatusBar{background:#ffffff;border-top:1px solid #cfd8e3;} QStatusBar::item{border: none;}')
        self.setStatusBar(self.status_bar)
        # Sol tarafa durum etiketi (mesaj)
        self.status_msg = QLabel("Hazır")
        chip_style = 'QLabel{padding:4px 8px;color:#1a2b49;background:#ffffff;border:1px solid #cfd8e3;border-radius:6px;}'
        self.status_msg.setStyleSheet(chip_style)
        self.status_bar.addWidget(self.status_msg, 1)
        # Sağ tarafa kalıcı widget'lar ekle (toplam kayıt ve link)
        self.footer_total = QLabel("Toplam kayıt: 0")
        self.footer_total.setStyleSheet(chip_style)
        self.status_bar.addPermanentWidget(self.footer_total)
        link = QLabel(
            '<a style="text-decoration:none;color:#1a73e8;" '
            'href="https://wa.me/905439761400?text=merhaba%20%C5%9Fantiye%20takip%20program%C4%B1ndan%20geliyorum%20bir!">'
            'Coded By Yunus AÇIKGÖZ</a>'
        )
        link.setOpenExternalLinks(True)
        link.setStyleSheet(chip_style + ' QLabel{margin-left:8px;}')
        self.status_bar.addPermanentWidget(link)
        
        # Stil
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
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
        # Modern gradient toolbar
        toolbar_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffffff, stop:0.5 #f8f9fa, stop:1 #e3f2fd);
                border: 2px solid #e1f5fe;
                border-radius: 16px;
                margin: 8px;
            }
        """)
        
        toolbar_layout = QHBoxLayout()
        toolbar_frame.setLayout(toolbar_layout)
        
        # Logo ve başlık container
        title_container = QHBoxLayout()
        
        # Basit emoji logo
        logo_label = QLabel("🏗️")
        logo_label.setFixedSize(48, 48)
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #1e40af;
                background: transparent;
                border: none;
                text-align: center;
            }
        """)
        
        title_container.addWidget(logo_label)
        
        # Başlık
        title_label = QLabel("Öztaç Petrol A.Ş\nAraç Bakım Kayıtları Yönetim Sistemi")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 700;
                color: #1a2b49;
                padding: 8px 12px;
                line-height: 1.2;
            }
        """)
        title_container.addWidget(title_label)
        title_container.addStretch()
        
        toolbar_layout.addLayout(title_container)
        
        # Modern arama kutusu
        search_wrap = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Plaka ile ara...")
        self.search_edit.textChanged.connect(self.search_records)
        self.search_edit.setFixedWidth(350)
        self.search_edit.setFixedHeight(40)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 10px 16px;
                border: 2px solid #e1f5fe;
                border-radius: 20px;
                background: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border-color: #2196f3;
                background: #f8f9fa;
            }
            QLineEdit:hover {
                border-color: #bbdefb;
            }
        """)
        search_wrap.addWidget(self.search_edit)
        toolbar_layout.addLayout(search_wrap)
        toolbar_layout.addStretch()
        
        # Karanlık mod: varsayılan uygulanacak, buton kaldırıldı
        
        # Butonlar için ortak stil - basitleştirilmiş
        button_style = """
            QPushButton {
                background-color: #ffffff;
                color: #495057;
                border: 2px solid #dee2e6;
                padding: 12px 20px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                min-width: 140px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #2196f3;
                color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #bbdefb;
                border-color: #1976d2;
            }
        """
        
        # ToolButton için aynı stil
        toolbutton_style = """
            QToolButton {
                background-color: #ffffff;
                color: #495057;
                border: 2px solid #dee2e6;
                padding: 12px 20px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                min-width: 160px;
                min-height: 20px;
            }
            QToolButton:hover {
                background-color: #e3f2fd;
                border-color: #2196f3;
                color: #1976d2;
            }
            QToolButton:pressed {
                background-color: #bbdefb;
                border-color: #1976d2;
            }
        """
        
        # Yeni kayıt butonu
        top_add_btn = QPushButton("➕ Yeni Kayıt")
        top_add_btn.clicked.connect(self.add_record)
        top_add_btn.setStyleSheet(button_style)
        toolbar_layout.addWidget(top_add_btn)
        
        # GitHub entegrasyonu kaldırıldı
        
        # Diğer işlemler açılır menüsü
        more_menu = QMenu(self)
        act_refresh = QAction("🔄 Yenile", self)
        act_refresh.triggered.connect(self.load_data)
        act_import = QAction("📁 Excel İçe Aktar", self)
        act_import.triggered.connect(self.import_excel)
        act_export = QAction("📤 Excel Dışa Aktar", self)
        act_export.triggered.connect(self.export_excel)
        act_wipe = QAction("🗑️ Tümünü Sil", self)
        act_wipe.triggered.connect(self.delete_all_records)
        # Güncelleme kontrolü
        act_update = QAction("🔄 Güncelleme Kontrolü", self)
        act_update.triggered.connect(self.manual_check_updates)
        
        more_menu.addAction(act_refresh)
        more_menu.addAction(act_import)
        more_menu.addAction(act_export)
        more_menu.addSeparator()
        more_menu.addAction(act_update)
        more_menu.addSeparator()
        more_menu.addAction(act_wipe)

        from PyQt6.QtWidgets import QToolButton
        more_btn = QToolButton()
        more_btn.setText("⚙️ Diğer İşlemler ▾")
        more_btn.setMenu(more_menu)
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_btn.setStyleSheet(toolbutton_style)
        toolbar_layout.addWidget(more_btn)

        # Buton stilleri zaten yukarıda tanımlandı
        
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
            '<a style="text-decoration:none;color:#1a73e8;" '
            'href="https://wa.me/905439761400?text=merhaba%20%C5%9Fantiye%20takip%20program%C4%B1ndan%20geliyorum%20bir!">'
            'Coded By Yunus AÇIKGÖZ</a>'
        )
        label.setOpenExternalLinks(True)
        label.setStyleSheet('QLabel{padding:6px 10px;color:#1a73e8;background:#ffffff;border:1px solid #cfd8e3;border-radius:6px; margin-left:8px;}')
        h.addWidget(label)
        frame.setLayout(h)
        frame.setStyleSheet('QFrame{background:transparent;}')
        return frame
    
    def create_left_panel(self):
        """Sol panel oluştur"""
        panel = QGroupBox("Kontroller")
        panel.setObjectName("Kontroller")
        layout = QVBoxLayout()
        
        # Arama grubu
        search_group = QGroupBox("Arama")
        search_layout = QVBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Plaka ile ara...")
        self.search_edit.textChanged.connect(self.search_records)
        search_layout.addWidget(self.search_edit)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # İşlemler grubu
        actions_group = QGroupBox("İşlemler")
        actions_layout = QVBoxLayout()
        
        # Yeni kayıt butonu
        add_btn = QPushButton("➕ Yeni Kayıt Ekle")
        add_btn.clicked.connect(self.add_record)
        actions_layout.addWidget(add_btn)
        
        # Tümünü sil butonu (sidebar)
        wipe_btn_side = QPushButton("🗑️ Tüm Kayıtları Sil")
        wipe_btn_side.clicked.connect(self.delete_all_records)
        wipe_btn_side.setObjectName("danger")
        actions_layout.addWidget(wipe_btn_side)
        
        # Düzenle butonu
        edit_btn = QPushButton("✏️ Kayıt Düzenle")
        edit_btn.clicked.connect(self.edit_record)
        actions_layout.addWidget(edit_btn)
        
        # Sil butonu
        delete_btn = QPushButton("🗑️ Kayıt Sil")
        delete_btn.clicked.connect(self.delete_record)
        actions_layout.addWidget(delete_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # İstatistikler grubu
        stats_group = QGroupBox("İstatistikler")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("İstatistikler yükleniyor...")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
                font-size: 12px;
            }
        """)
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        # Sidebar koyu stil
        panel.setStyleSheet("""
            QGroupBox { color: #e6e6e6; border: 1px solid #333; border-radius: 8px; background:#1f1f1f; }
            QLineEdit { background: #2b2b2b; color: #e6e6e6; border: 1px solid #3a3a3a; }
            QPushButton { background: #2e7d32; color: #ffffff; border: none; padding: 10px; border-radius: 6px; font-weight:600; }
            QPushButton:hover { background: #388e3c; }
            QPushButton#danger { background:#b71c1c; }
            QPushButton#danger:hover { background:#d32f2f; }
            QLabel { color: #e6e6e6; }
        """)
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """Sağ panel oluştur"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Filtre barı
        filter_bar = QHBoxLayout()
        from PyQt6.QtWidgets import QToolButton
        self.filter_use_date = QCheckBox("Tarih filtresi")
        self.filter_use_date.setChecked(False)
        self.filter_start = QDateEdit()
        self.filter_start.setCalendarPopup(True)
        self.filter_start.setDisplayFormat("dd.MM.yyyy")
        self.filter_start.setDate(QDate.currentDate().addMonths(-6))
        self.filter_end = QDateEdit()
        self.filter_end.setCalendarPopup(True)
        self.filter_end.setDisplayFormat("dd.MM.yyyy")
        self.filter_end.setDate(QDate.currentDate())
        self.filter_bolge = QComboBox()
        self.filter_bolge.setEditable(False)
        self.filter_bolge.addItem("Tümü")
        self.filter_bakim_yapan = QComboBox()
        self.filter_bakim_yapan.addItem("Tümü")
        # Uygula ve Temizle butonları
        btn_apply = QPushButton("Filtrele")
        btn_clear = QPushButton("Temizle")
        for w in [self.filter_start, self.filter_end, self.filter_bolge, self.filter_bakim_yapan]:
            w.setFixedHeight(32)
        btn_apply.setFixedHeight(32)
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
        panel.setLayout(layout)
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
        if col in (7, 8):
            self.show_operation_details()

    def show_operation_details(self):
        """Seçili satırın 'Yapılan İşlem' ve 'Diğer' alanlarını büyük pencerede göster"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        item = self.table.item(current_row, 0)
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
        # Dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Yapılan İşlem Detayı")
        dlg.resize(700, 500)
        v = QVBoxLayout()
        header = QLabel(f"Plaka: {record[2]}  |  Kapı No: {record[3] or '-'}  |  Tarih: {record[5] or '-'}")
        header.setStyleSheet("QLabel{font-weight:600;color:#1a2b49}")
        v.addWidget(header)
        info = QTextEdit()
        info.setReadOnly(True)
        parts = []
        if record[8]:
            parts.append(str(record[8]))
        if record[9]:
            parts.append("\n--- Diğer ---\n" + str(record[9]))
        info.setPlainText("\n\n".join(parts) if parts else "-")
        v.addWidget(info)
        dlg.setLayout(v)
        dlg.exec()

    def create_kpi_card(self, icon, title, value, color, bg_color):
        """Modern KPI kartı oluştur - optimize edilmiş boyutlar"""
        card = QLabel()
        card.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.setFixedHeight(90)
        card.setMinimumWidth(180)
        
        # İçerik formatı - daha küçük ve dengeli
        content = f"""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 24px; margin-bottom: 6px;">{icon}</div>
            <div style="font-size: 12px; font-weight: bold; color: {color}; margin-bottom: 3px;">{title}</div>
            <div style="font-size: 18px; font-weight: bold; color: {color};">{value}</div>
        </div>
        """
        card.setText(content)
        
        # Stil
        card.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border: 2px solid {color};
                border-radius: 10px;
                color: {color};
                font-weight: bold;
            }}
        """)
        
        return card

    def update_kpi_card(self, card, icon, title, value):
        """KPI kartını güncelle - optimize edilmiş boyutlar"""
        content = f"""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 24px; margin-bottom: 6px;">{icon}</div>
            <div style="font-size: 12px; font-weight: bold; color: #333; margin-bottom: 3px;">{title}</div>
            <div style="font-size: 18px; font-weight: bold; color: #333;">{value}</div>
        </div>
        """
        card.setText(content)

    def create_dashboard_panel(self):
        """Dashboard paneli - Temiz ve minimalist tasarım"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)  # Daha fazla boşluk
        layout.setContentsMargins(20, 20, 20, 20)  # Daha fazla margin
        
        # Ana KPI kartları - 2 satır halinde
        kpi_layout = QVBoxLayout()
        kpi_layout.setSpacing(15)  # Kartlar arası boşluk artırıldı
        
        # 1. Satır: Ana metrikler
        row1 = QHBoxLayout()
        row1.setSpacing(15)
        
        # Sade ve minimalist renk paleti
        self.kpi_total = self.create_kpi_card("📊", "Toplam Kayıt", "0", "#2c3e50", "#ecf0f1")
        self.kpi_vehicles = self.create_kpi_card("🚗", "Toplam Araç", "0", "#34495e", "#ecf0f1")
        self.kpi_last = self.create_kpi_card("⏰", "Son Bakım", "-", "#7f8c8d", "#ecf0f1")
        
        row1.addWidget(self.kpi_total)
        row1.addWidget(self.kpi_vehicles)
        row1.addWidget(self.kpi_last)
        
        # 2. Satır: Zaman bazlı metrikler
        row2 = QHBoxLayout()
        row2.setSpacing(15)
        
        self.kpi_this_month = self.create_kpi_card("📅", "Bu Ay", "0", "#95a5a6", "#ecf0f1")
        self.kpi_this_week = self.create_kpi_card("📋", "Bu Hafta", "0", "#bdc3c7", "#ecf0f1")
        self.kpi_upcoming = self.create_kpi_card("⚠️", "Yaklaşan Bakım", "0", "#e74c3c", "#fdf2f2")
        
        row2.addWidget(self.kpi_this_month)
        row2.addWidget(self.kpi_this_week)
        row2.addWidget(self.kpi_upcoming)
        
        kpi_layout.addLayout(row1)
        kpi_layout.addLayout(row2)
        
        layout.addLayout(kpi_layout)
        
        # KPI kartları ile tablolar arasında daha fazla boşluk
        spacer = QWidget()
        spacer.setFixedHeight(25)  # Ekstra boşluk
        layout.addWidget(spacer)
        
        # Analiz bölümü - 3 sütun halinde (yan yana)
        analysis_layout = QHBoxLayout()
        analysis_layout.setSpacing(15)  # Panel arası boşluk
        
        # Sol: En çok bakım yapılan araçlar
        vehicles_group = QGroupBox("🏆 En Çok Bakım Yapılan Araçlar")
        vehicles_group.setStyleSheet("""
            QGroupBox {
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background: #ffffff;
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #ffffff;
                border-radius: 4px;
            }
        """)
        vehicles_layout = QVBoxLayout()
        self.top_vehicles_table = QTableWidget(0, 3)
        self.top_vehicles_table.setHorizontalHeaderLabels(["Plaka", "Bakım Sayısı", "Son Bakım"])
        self.top_vehicles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_vehicles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.top_vehicles_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.top_vehicles_table.setAlternatingRowColors(True)
        self.top_vehicles_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                color: #1a2b49;
                alternate-background-color: #f9fbff;
                border: 1px solid #cfd8e3;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background: #e3f2fd;
                color: #1565c0;
                border: 1px solid #bbdefb;
                font-weight: bold;
                padding: 8px;
            }
        """)
        vehicles_layout.addWidget(self.top_vehicles_table)
        vehicles_group.setLayout(vehicles_layout)
        analysis_layout.addWidget(vehicles_group)
        
        # Sağ: Bölge analizi
        regions_group = QGroupBox("🗺️ Bölge Analizi")
        regions_group.setStyleSheet("""
            QGroupBox {
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background: #ffffff;
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #ffffff;
                border-radius: 4px;
            }
        """)
        regions_layout = QVBoxLayout()
        self.regions_table = QTableWidget(0, 2)
        self.regions_table.setHorizontalHeaderLabels(["Bölge", "Bakım Sayısı"])
        self.regions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.regions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.regions_table.setAlternatingRowColors(True)
        self.regions_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                color: #1a2b49;
                alternate-background-color: #f1f8e9;
                border: 1px solid #cfd8e3;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background: #e8f5e8;
                color: #2e7d32;
                border: 1px solid #c8e6c9;
                font-weight: bold;
                padding: 8px;
            }
        """)
        regions_layout.addWidget(self.regions_table)
        regions_group.setLayout(regions_layout)
        analysis_layout.addWidget(regions_group)
        
        # Sağ: Bakımı yapan kişilere dair mini tablo
        person_group = QGroupBox("👥 Bakım Yapan Personel")
        person_group.setStyleSheet("""
            QGroupBox {
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background: #ffffff;
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background: #ffffff;
                border-radius: 4px;
            }
        """)
        person_layout = QVBoxLayout()
        self.person_table = QTableWidget(0, 2)
        self.person_table.setHorizontalHeaderLabels(["Bakım Yapan", "Bakım Sayısı"])
        self.person_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.person_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.person_table.setAlternatingRowColors(True)
        self.person_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                color: #1a2b49;
                alternate-background-color: #fff3e0;
                border: 1px solid #cfd8e3;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background: #fff3e0;
                color: #f57c00;
                border: 1px solid #ffcc02;
                font-weight: bold;
                padding: 8px;
            }
        """)
        person_layout.addWidget(self.person_table)
        person_group.setLayout(person_layout)
        analysis_layout.addWidget(person_group)
        
        layout.addLayout(analysis_layout)
        
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
        self.status_bar.showMessage(f"Toplam {len(records)} kayıt yüklendi")
        if hasattr(self, 'footer_total'):
            self.footer_total.setText(f"Toplam kayıt: {len(records)}")

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
        # UI: [ID gizli], PLAKA, KAPI NO, BÖLGE, TARİH, BAKIM KM, SONRAKI KM, YAPILAN İŞLEM, DİĞER, BAKIMI YAPAN
        db_to_ui = {2:1, 3:2, 4:3, 5:4, 6:5, 7:6, 8:7, 9:8, 10:9}
        for row, record in enumerate(records):
            # Gizli ID sütununu doldur (seçim ve işlemler için gerekli)
            id_item = QTableWidgetItem(str(record[0]))
            id_item.setData(Qt.ItemDataRole.UserRole, record[0])
            # ID hücresi düzenlenebilir olmasın
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, id_item)
            for db_index, ui_col in db_to_ui.items():
                value = record[db_index]
                # KM kolonları: 5 ve 6 (UI)
                if ui_col in (5, 6):
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
                if ui_col in (1, 2, 3, 4):
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter))
                elif ui_col in (5, 6):
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
                else:
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
                # Uzun metinler için tooltip
                if ui_col in (7, 8) and display_value not in (None, "-"):
                    item.setToolTip(str(display_value))
                # Sonraki bakım KM yaklaşınca satır renklendir (ör. fark <= 1000 km)
                if ui_col == 6:
                    try:
                        current_km = int(str(self.table.item(row, 5).text()).replace('.', '')) if self.table.item(row, 5) else None
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
        # Dashboard KPI'ları da güncelle
        if hasattr(self, 'kpi_total'):
            # Ana KPI'lar - yeni format
            self.update_kpi_card(self.kpi_total, "📊", "Toplam Kayıt", str(stats.get('toplam_kayit', 0)))
            self.update_kpi_card(self.kpi_vehicles, "🚗", "Toplam Araç", str(stats.get('toplam_arac', 0)))
            self.update_kpi_card(self.kpi_last, "⏰", "Son Bakım", stats.get('son_bakim') or '-')
            
            # Ek KPI'ları hesapla
            try:
                cursor = self.db_manager.conn.cursor()
                
                # Bu ay bakım sayısı
                cursor.execute("""
                    SELECT COUNT(*) FROM bakimlar 
                    WHERE strftime('%Y-%m', tarih) = strftime('%Y-%m', 'now')
                """)
                this_month = cursor.fetchone()[0]
                self.update_kpi_card(self.kpi_this_month, "📅", "Bu Ay", str(this_month))
                
                # Bu hafta bakım sayısı
                cursor.execute("""
                    SELECT COUNT(*) FROM bakimlar 
                    WHERE date(tarih) >= date('now', '-7 days')
                """)
                this_week = cursor.fetchone()[0]
                self.update_kpi_card(self.kpi_this_week, "📋", "Bu Hafta", str(this_week))
                
                
                # Yaklaşan bakım sayısı (sonraki KM - mevcut KM <= 1000)
                cursor.execute("""
                    SELECT COUNT(*) FROM bakimlar 
                    WHERE sonraki_bakim_km IS NOT NULL 
                    AND bakim_km IS NOT NULL 
                    AND (sonraki_bakim_km - bakim_km) <= 1000
                """)
                upcoming = cursor.fetchone()[0]
                self.update_kpi_card(self.kpi_upcoming, "⚠️", "Yaklaşan Bakım", str(upcoming))
                
                # En çok bakım yapılan araçlar (top 5)
                cursor.execute("""
                    SELECT plaka, COUNT(*) as bakim_sayisi, MAX(tarih) as son_bakim
                    FROM bakimlar
                    WHERE plaka IS NOT NULL AND plaka != ''
                    GROUP BY plaka
                    ORDER BY bakim_sayisi DESC
                    LIMIT 5
                """)
                top_vehicles = cursor.fetchall()
                self.top_vehicles_table.setRowCount(len(top_vehicles))
                for r, (plaka, sayi, son_bakim) in enumerate(top_vehicles):
                    self.top_vehicles_table.setItem(r, 0, QTableWidgetItem(plaka or '-'))
                    self.top_vehicles_table.setItem(r, 1, QTableWidgetItem(str(sayi)))
                    self.top_vehicles_table.setItem(r, 2, QTableWidgetItem(son_bakim or '-'))
                
                # Bölge analizi
                cursor.execute("""
                    SELECT COALESCE(bolge, '-') AS bolge, COUNT(*) as bakim_sayisi
                    FROM bakimlar
                    GROUP BY bolge
                    ORDER BY bakim_sayisi DESC
                """)
                regions = cursor.fetchall()
                self.regions_table.setRowCount(len(regions))
                for r, (bolge, sayi) in enumerate(regions):
                    self.regions_table.setItem(r, 0, QTableWidgetItem(bolge or '-'))
                    self.regions_table.setItem(r, 1, QTableWidgetItem(str(sayi)))
                
                # Personel istatistikleri
                cursor.execute("""
                    SELECT COALESCE(bakim_yapan,'-') AS ad, COUNT(*)
                    FROM bakimlar
                    GROUP BY ad
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                self.person_table.setRowCount(len(rows))
                for r, (ad, sayi) in enumerate(rows):
                    self.person_table.setItem(r, 0, QTableWidgetItem(ad or '-'))
                    self.person_table.setItem(r, 1, QTableWidgetItem(str(sayi)))
            except Exception:
                pass
    
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
                QMessageBox.warning(self, "Uyarı", "Plaka alanı zorunludur!")
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
                QMessageBox.information(self, "Başarılı", "Kayıt başarıyla eklendi!")
                self.load_data()
            else:
                QMessageBox.critical(self, "Hata", "Kayıt eklenirken hata oluştu!")
    
    def edit_record(self):
        """Kayıt düzenle"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlenecek kaydı seçin!")
            return
        
        # Seçili kaydın ID'sini al
        item = self.table.item(current_row, 0)
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
            QMessageBox.critical(self, "Hata", "Kayıt bulunamadı!")
            return
        
        dialog = RecordDialog(self, record_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data[1]:  # Plaka boşsa
                QMessageBox.warning(self, "Uyarı", "Plaka alanı zorunludur!")
                return
            
            if self.db_manager.update_record(record_id, data):
                QMessageBox.information(self, "Başarılı", "Kayıt başarıyla güncellendi!")
                self.load_data()
            else:
                QMessageBox.critical(self, "Hata", "Kayıt güncellenirken hata oluştu!")
    
    def delete_record(self):
        """Kayıt sil"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek kaydı seçin!")
            return
        
        # Seçili kaydın ID'sini al
        item = self.table.item(current_row, 0)
        if not item:
            return
        
        record_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Onay al
        reply = QMessageBox.question(
            self, "Onay", 
            "Bu kaydı silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_record(record_id):
                QMessageBox.information(self, "Başarılı", "Kayıt başarıyla silindi!")
                self.load_data()
            else:
                QMessageBox.critical(self, "Hata", "Kayıt silinirken hata oluştu!")
    
    def delete_all_records(self):
        """Tüm kayıtları sil"""
        reply = QMessageBox.question(
            self, "Onay",
            "Tüm kayıtları silmek üzeresiniz. Bu işlem geri alınamaz. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if self.db_manager.delete_all():
            QMessageBox.information(self, "Başarılı", "Tüm kayıtlar silindi!")
            self.load_data()
        else:
            QMessageBox.critical(self, "Hata", "Toplu silme sırasında hata oluştu!")
    
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
            QGroupBox { border: 1px solid #cfd8e3; color: #1a2b49; background:#ffffff; border-radius:10px; }
            QLabel { color: #1a2b49; }
            QLineEdit { background: #ffffff; color: #1a2b49; border: 1px solid #cfd8e3; border-radius:8px; }
            QLineEdit:focus { border-color: #1a73e8; }
            QPushButton { background-color: #1a73e8; color: #ffffff; border-radius: 8px; }
            QPushButton:hover { background-color: #1765c1; }
            QTableWidget { background: #ffffff; alternate-background-color: #f9fbff; color: #1a2b49; border: 1px solid #cfd8e3; }
            QHeaderView::section { background: #eef3ff; color: #1a2b49; border: 1px solid #cfd8e3; }
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
                color: #2c3e50;
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
                    color: #2c3e50;
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


