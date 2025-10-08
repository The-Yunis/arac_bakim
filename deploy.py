#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Release oluşturma scripti
"""

import subprocess
import sys
import os
from version import VERSION

def create_release():
    """GitHub release oluştur"""
    try:
        print(f"🚀 Sürüm {VERSION} için GitHub release oluşturuluyor...")
        
        # Git tag oluştur
        tag_cmd = f"git tag v{VERSION}"
        subprocess.run(tag_cmd, shell=True, check=True)
        
        # Tag'i push et
        push_cmd = f"git push origin v{VERSION}"
        subprocess.run(push_cmd, shell=True, check=True)
        
        print("✅ Git tag oluşturuldu!")
        print(f"🏷️ Tag: v{VERSION}")
        print("📝 GitHub'da Release oluşturmayı unutmayın!")
        print(f"🔗 https://github.com/The-Yunis/arac_bakim/releases/new")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def main():
    """Ana fonksiyon"""
    print("=== GitHub Release Oluşturma ===")
    print(f"Sürüm: {VERSION}")
    print()
    
    # EXE oluştur
    if not os.path.exists(f"dist/AracBakimYonetim-v{VERSION}.exe"):
        print("⚠️ EXE dosyası bulunamadı. Önce build_exe.py çalıştırın.")
        return
    
    # Git durumunu kontrol et
    try:
        result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️ Uncommitted changes var. Önce commit yapın:")
            print("git add .")
            print("git commit -m 'Update to v{VERSION}'")
            return
    except:
        pass
    
    # Release oluştur
    create_release()

if __name__ == "__main__":
    main()
