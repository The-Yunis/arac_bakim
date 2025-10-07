# Araç Bakım Kayıtları Yönetim Sistemi 

Modern PyQt6 tabanlı araç bakım takip uygulaması. Araçlarınızın bakım geçmişini, kilometre takibini ve gelecek bakım planlarını yönetmenizi sağlar.

## 🚗 Özellikler

- **Araç Yönetimi**: Araç ekleme, düzenleme ve silme
- **Bakım Kayıtları**: Detaylı bakım geçmişi takibi
- **Kilometre Takibi**: Araç kilometrelerini kaydetme ve analiz
- **Bakım Planlama**: Gelecek bakım tarihlerini planlama
- **Excel İçe/Dışa Aktarma**: Verilerinizi Excel formatında yedekleme
- **GitHub Senkronizasyonu**: Veritabanını GitHub'da otomatik yedekleme
- **Modern Dashboard**: KPI kartları ve analiz grafikleri
- **Modern Arayüz**: Kullanıcı dostu PyQt6 arayüzü
- **Veritabanı**: SQLite ile güvenli veri saklama

## 🚀 Hızlı Başlangıç

### 📦 EXE Dosyası ile (Önerilen)
1. **İndirin**: `dist/AracBakimYonetim.app` dosyasını indirin
2. **Çalıştırın**: Dosyaya çift tıklayın
3. **Kullanın**: Program otomatik olarak GitHub'dan veri indirecek

### 🐍 Python ile
1. Repository'yi klonlayın:
```bash
git clone https://github.com/The-Yunis/arac_bakim.git
cd arac_bakim
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python bakim_gui.py
```

## 📋 Gereksinimler

### EXE Kullanımı
- **macOS**: 10.15+ (Catalina ve üzeri)
- **İnternet**: İlk çalıştırmada GitHub bağlantısı gerekli

### Python Geliştirme
- Python 3.8+
- PyQt6
- pandas
- openpyxl
- requests
- PyGithub

## 📖 Kullanım

### 🏠 Ana Sayfa (Dashboard)
- **KPI Kartları**: Toplam kayıt, araç sayısı, son bakım tarihi
- **Zaman Analizi**: Bu ay, bu hafta, yaklaşan bakımlar
- **En Aktif Araçlar**: En çok bakım yapılan araçlar listesi
- **Bölge Analizi**: Bölge bazında bakım istatistikleri

### 📝 Kayıt Yönetimi
1. **Yeni Kayıt**: "➕ Yeni Kayıt" butonuna tıklayın
2. **Düzenleme**: Kayıt üzerine çift tıklayın
3. **Silme**: Kayıt seçip "🗑️ Kayıt Sil" butonuna tıklayın
4. **Arama**: Plaka ile arama yapın

### 📊 Excel İşlemleri
1. **İçe Aktarma**: "📁 Excel İçe Aktar" menüsünden
2. **Dışa Aktarma**: "📤 Excel Dışa Aktar" menüsünden
3. **Sütun Eşleştirme**: Otomatik sütun tanıma

### ☁️ GitHub Senkronizasyonu
- **Otomatik Yedekleme**: Program kapanırken otomatik yedekleme
- **Otomatik İndirme**: Program açılırken otomatik indirme
- **Manuel İşlemler**: "Diğer İşlemler" menüsünden

## 🗂️ Proje Yapısı

```
arac_bakim/
├── bakim_gui.py              # Ana uygulama dosyası
├── requirements.txt           # Python bağımlılıkları
├── bakim_kayitlari.db         # SQLite veritabanı
├── dist/                      # EXE dosyaları
│   ├── AracBakimYonetim       # macOS executable
│   └── AracBakimYonetim.app/  # macOS app bundle
├── AracBakimYonetim.spec      # PyInstaller konfigürasyonu
└── README.md                  # Bu dosya
```

## 🔧 EXE Oluşturma

Kendi EXE dosyanızı oluşturmak için:

```bash
# PyInstaller yükleyin
pip install pyinstaller

# EXE oluşturun
pyinstaller --onefile --windowed --name=AracBakimYonetim \
  --add-data="bakim_kayitlari.db:." \
  --hidden-import=PyQt6.QtCore \
  --hidden-import=PyQt6.QtWidgets \
  --hidden-import=PyQt6.QtGui \
  --hidden-import=pandas \
  --hidden-import=openpyxl \
  --hidden-import=requests \
  --exclude-module=PyQt5 \
  --exclude-module=PySide6 \
  bakim_gui.py
```

## 🎯 Özellik Detayları

### 📊 Dashboard
- **6 Ana KPI Kartı**: Toplam kayıt, araç, son bakım, bu ay, bu hafta, yaklaşan bakım
- **En Aktif Araçlar**: Top 5 araç listesi
- **Bölge Analizi**: Bölge bazında istatistikler
- **Personel Analizi**: Bakım yapan personel istatistikleri

### 🔄 GitHub Entegrasyonu
- **Otomatik Senkronizasyon**: Git komutları ile
- **Veri Güvenliği**: Tüm veriler GitHub'da yedekli
- **Çoklu Cihaz**: Farklı bilgisayarlarda aynı veri

### 📈 Excel Desteği
- **İçe Aktarma**: Mevcut Excel dosyalarını import
- **Dışa Aktarma**: Verileri Excel formatında export
- **Sütun Eşleştirme**: Otomatik sütun tanıma

## 🚨 Önemli Notlar

- **İlk Çalıştırma**: İnternet bağlantısı gerekli (GitHub'dan veri indirme)
- **Veri Güvenliği**: Tüm veriler GitHub'da otomatik yedeklenir
- **Çoklu Kullanım**: Aynı GitHub repo'sunu kullanan tüm cihazlar senkronize

## 🔧 Geliştirme

Projeyi geliştirmek için:

1. Repository'yi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Push edin (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📞 İletişim

Proje hakkında sorularınız için issue açabilirsiniz.

---

**CODED BY YUNUS AÇIKGÖZ**
