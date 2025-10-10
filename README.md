# Şantiye Yönetim Sistemi 

Modern PyQt6 tabanlı şantiye ve araç bakım yönetim uygulaması. Şantiyelerinizi, araçlarınızı ve bakım süreçlerinizi merkezi olarak yönetmenizi sağlar.

## 🏗️ Özellikler

### 🏢 Şantiye Yönetimi
- **Çoklu Şantiye Desteği**: Birden fazla şantiye yönetimi
- **Şantiye Bilgileri**: Lokasyon, sorumlu kişi ve durum takibi
- **Şantiye Bazlı Araç Yönetimi**: Her şantiyeye özel araç listesi
- **Şantiye Değiştirme**: Kolay şantiye geçişi ve veri filtreleme

### 🚗 Araç Yönetimi
- **Araç Kayıtları**: Plaka, kapı no, bölge ve durum bilgileri
- **Araç Durumu**: Aktif/Pasif, Sağlam/Arızalı durum takibi
- **Toplu İşlemler**: Şantiye bazlı toplu araç işlemleri
- **Araç Transferi**: Araçları şantiyeler arası taşıma

### 🔧 Bakım Yönetimi
- **Bakım Kayıtları**: Detaylı bakım geçmişi takibi
- **Kilometre Takibi**: Araç kilometrelerini kaydetme ve analiz
- **Bakım Planlama**: Gelecek bakım tarihlerini planlama
- **Personel Takibi**: Bakım yapan personel kayıtları

### 📊 Analiz ve Raporlama
- **Modern Dashboard**: KPI kartları ve analiz grafikleri
- **Şantiye Bazlı İstatistikler**: Her şantiye için ayrı analiz
- **Excel İçe/Dışa Aktarma**: Verilerinizi Excel formatında yedekleme

### 💻 Teknik Özellikler
- **Modern Arayüz**: Kullanıcı dostu PyQt6 arayüzü
- **Veritabanı**: SQLite ile güvenli veri saklama
- **Çoklu Platform**: Windows, macOS ve Linux desteği

## 🚀 Hızlı Başlangıç

### 📦 EXE Dosyası ile (Önerilen)
1. **İndirin**: `dist/AracBakimYonetim.app` dosyasını indirin
2. **Çalıştırın**: Dosyaya çift tıklayın
3. **Kullanın**: Program yerel veritabanı ile çalışır

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
- **Windows**: Windows 10 ve üzeri
- **Linux**: Ubuntu 18.04+ ve diğer modern dağıtımlar

### Python Geliştirme
- Python 3.8+
- PyQt6
- pandas
- openpyxl

## 📖 Kullanım

### 🏢 Şantiye Yönetimi
1. **Şantiye Ekleme**: "🏗️ Şantiye Yönetimi" menüsünden yeni şantiye ekleyin
2. **Şantiye Seçimi**: Üst menüden aktif şantiyeyi seçin
3. **Şantiye Düzenleme**: Şantiye bilgilerini güncelleyin
4. **Şantiye Silme**: Kullanılmayan şantiyeleri silin

### 🚗 Araç Yönetimi
1. **Araç Ekleme**: "➕ Yeni Araç" butonuna tıklayın
2. **Araç Düzenleme**: Araç üzerine çift tıklayın
3. **Durum Güncelleme**: Araç durumunu aktif/pasif, sağlam/arızalı olarak işaretleyin
4. **Toplu İşlemler**: Şantiye bazlı toplu araç işlemleri yapın

### 🔧 Bakım Kayıtları
1. **Yeni Bakım**: "➕ Yeni Kayıt" butonuna tıklayın
2. **Bakım Düzenleme**: Kayıt üzerine çift tıklayın
3. **Bakım Silme**: Kayıt seçip "🗑️ Kayıt Sil" butonuna tıklayın
4. **Arama**: Plaka ile arama yapın

### 🏠 Dashboard (Ana Sayfa)
- **KPI Kartları**: Toplam kayıt, araç sayısı, son bakım tarihi
- **Şantiye Analizi**: Seçili şantiye bazında istatistikler
- **Zaman Analizi**: Bu ay, bu hafta, yaklaşan bakımlar
- **En Aktif Araçlar**: En çok bakım yapılan araçlar listesi

### 📊 Excel İşlemleri
1. **İçe Aktarma**: "📁 Excel İçe Aktar" menüsünden
2. **Dışa Aktarma**: "📤 Excel Dışa Aktar" menüsünden
3. **Sütun Eşleştirme**: Otomatik sütun tanıma


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

### 📊 Dashboard (Şantiye Bazlı)
- **6 Ana KPI Kartı**: Toplam kayıt, araç, son bakım, bu ay, bu hafta, yaklaşan bakım
- **Şantiye Seçimi**: Aktif şantiye değiştirme dropdown'ı
- **En Aktif Araçlar**: Seçili şantiyedeki en çok bakım yapılan araçlar
- **Şantiye Analizi**: Şantiye bazında bakım istatistikleri
- **Personel Analizi**: Bakım yapan personel istatistikleri
- **Bölge Analizi**: Bölge bazında bakım dağılımı

### 🏢 Şantiye Yönetimi Detayları
- **Çoklu Şantiye**: Sınırsız şantiye ekleme ve yönetimi
- **Şantiye Bilgileri**: Ad, lokasyon, sorumlu kişi bilgileri
- **Şantiye Durumu**: Aktif/Pasif durum takibi
- **Şantiye Bazlı Filtreleme**: Her şantiye için ayrı araç ve bakım listesi
- **Şantiye Geçişi**: Kolay şantiye değiştirme ve veri filtreleme


### 📈 Excel Desteği
- **İçe Aktarma**: Mevcut Excel dosyalarını import
- **Dışa Aktarma**: Verileri Excel formatında export
- **Sütun Eşleştirme**: Otomatik sütun tanıma
- **Şantiye Bazlı Export**: Seçili şantiyenin verilerini ayrı export

## 🚨 Önemli Notlar

- **İlk Çalıştırma**: Program yerel SQLite veritabanı ile çalışır
- **Şantiye Seçimi**: Program açılışında varsayılan şantiye seçilir
- **Veri Güvenliği**: Tüm veriler yerel veritabanında saklanır
- **Şantiye Bağımsızlığı**: Her şantiyenin verisi ayrı ayrı yönetilir
- **Yedekleme**: Düzenli olarak Excel export ile veri yedekleme önerilir

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
