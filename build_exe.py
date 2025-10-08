#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXE oluşturma scripti
"""

import subprocess
import sys
import os
from version import VERSION

def build_exe():
    """EXE dosyasını oluştur"""
    try:
        print(f"🚀 Sürüm {VERSION} için EXE oluşturuluyor...")
        
        # PyInstaller komutu
        cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed",
            f"--name=AracBakimYonetim-v{VERSION}",
            "--add-data=bakim_kayitlari.db;.",
            "--add-data=version.py;.",
            "--hidden-import=PyQt6.QtCore",
            "--hidden-import=PyQt6.QtWidgets", 
            "--hidden-import=PyQt6.QtGui",
            "--hidden-import=pandas",
            "--hidden-import=openpyxl",
            "--hidden-import=requests",
            "--exclude-module=PyQt5",
            "--exclude-module=PySide6",
            "bakim_gui.py"
        ]
        
        # EXE oluştur
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ EXE başarıyla oluşturuldu!")
            print(f"📁 Konum: dist/AracBakimYonetim-v{VERSION}.exe")
            return True
        else:
            print("❌ EXE oluşturma hatası:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

if __name__ == "__main__":
    build_exe()
