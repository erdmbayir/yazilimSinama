import tkinter as tk
from tkinter import messagebox
import pyaudio
import wave
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime
import threading
from google.cloud import speech

# Google Cloud API Key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\Admin\Desktop\sinan\dnm2\elite-fabric-446309-v4-684078b78168.json"

# Ses dosyasının kaydedileceği dizin
SAVE_PATH = r"C:\Users\Admin\Desktop\sinan\dnm2\\"

# Küresel değişkenler
recording = False
frames = []

# Tkinter arayüzü
root = tk.Tk()
root.title("Ses Kayıt ve Analiz Uygulaması")
root.geometry("500x500")
root.config(bg="#e6f7ff")

result_label = tk.Label(root, text="Sonuçlar burada görünecek.", bg="#e6f7ff", font=("Helvetica", 12), wraplength=450)
result_label.pack(pady=20)

# Kayıt işlemi için iş parçacığı
def start_recording():
    global recording, frames
    recording = True
    frames = []

    # Benzersiz dosya adı oluştur
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    audio_filename = f"audio_{timestamp}.wav"
    full_audio_path = os.path.join(SAVE_PATH, audio_filename)

    # Ses kaydını başlat
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    def record():
        global recording, frames
        print("Ses kaydediliyor...")
        for _ in range(0, int(44100 / 1024 * 30)):  # Maksimum 30 saniye
            if not recording:
                break
            data = stream.read(1024)
            frames.append(data)
        print("Ses kaydı tamamlandı.")

        # Kaydı durdur
        stream.stop_stream()
        stream.close()
        p.terminate()

        # Ses verisini kaydet
        with wave.open(full_audio_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(frames))

        # GUI güncelleme: Ses kaydı tamamlandığında ana iş parçacığını güncellemek için `root.after` kullanacağız.
        root.after(0, update_result_label, f"Ses kaydedildi: {audio_filename}. Grafikler gösteriliyor...")
        
        # Ses kaydını analiz et
        analyze_audio(full_audio_path)

    # Kayıt işlemini başlatan iş parçacığı
    threading.Thread(target=record).start()

# Kayıt durdurma işlemi
def stop_recording():
    global recording
    recording = False
    result_label.config(text="Kayıt durduruldu, ses işleniyor...")

# Ses dalga formu, histogram ve ısı haritasını çıkarma
def analyze_audio(audio_filename):
    if os.path.exists(audio_filename):
        with wave.open(audio_filename, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)
            sample_rate = wf.getframerate()

        # Grafikler
        plt.figure(figsize=(12, 8))

        # Dalga formu (Waveform)
        plt.subplot(3, 1, 1)
        time = np.linspace(0, len(audio_data) / sample_rate, num=len(audio_data))
        plt.plot(time, audio_data, color='blue')
        plt.title("Ses Dalga Formu")
        plt.xlabel("Zaman (s)")
        plt.ylabel("Genlik")

        # Ses histogramı
        plt.subplot(3, 1, 2)
        plt.hist(audio_data, bins=200, color='green', alpha=0.7)
        plt.title("Ses Histogramı")
        plt.xlabel("Genlik")
        plt.ylabel("Frekans")

        # Isı haritası (Spectrogram)
        plt.subplot(3, 1, 3)
        plt.specgram(audio_data, Fs=sample_rate, NFFT=1024, noverlap=512, cmap="viridis")
        plt.title("Ses Isı Haritası (Spectrogram)")
        plt.xlabel("Zaman (s)")
        plt.ylabel("Frekans (Hz)")

        plt.tight_layout()
        plt.show()

        # Sesin metne dönüştürülmesi ve kelime sayısı analizi
        transcribed_text = transcribe_audio(audio_filename)
        word_count = len(transcribed_text.split())

        # Sesin konusunun analizi
        subject = analyze_text_subject(transcribed_text)

        # Duygu analizi (Öfkeli mi Mutlu mu)
        sentiment = analyze_sentiment(transcribed_text)

        # Analiz sonucunu GUI'ye ilet
        result_text = f"Metin: {transcribed_text}\nKelime Sayısı: {word_count}\nKonusu: {subject}\nDuygu: {sentiment}"
        root.after(0, update_result_label, result_text)

    else:
        messagebox.showerror("Hata", "Ses dosyası bulunamadı. Lütfen önce ses kaydedin.")

# GUI metni güncelleme fonksiyonu
def update_result_label(text):
    result_label.config(text=text)

# Ses kaydını metne dönüştürme
def transcribe_audio(audio_filename):
    client = speech.SpeechClient()

    with open(audio_filename, 'rb') as audio_file:
        audio_content = audio_file.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        language_code="tr-TR",
    )

    response = client.recognize(config=config, audio=audio)
    text = ""
    for result in response.results:
        text += result.alternatives[0].transcript

    return text

# Metnin konusunu analiz etme
def analyze_text_subject(text):
    try:
        # Önceden tanımlanmış konu kategorileri
        topics = {
            "Sanat": ["sanat", "müzik", "resim", "tiyatro", "heykel", "yaratıcılık"],
            "Teknoloji": ["teknoloji", "yazılım", "bilgisayar", "yapay zeka", "internet", "robot", "veri"],
            "Eğitim": ["eğitim", "öğrenme", "okul", "öğrenci", "öğretmen", "ders", "sınav"],
            "Sağlık": ["sağlık", "hastane", "doktor", "tedavi", "ilaç", "hastalık"],
            "Ekonomi": ["ekonomi", "para", "banka", "borsa", "ticaret", "finans", "yatırım"],
            "Spor": ["spor", "futbol", "basketbol", "voleybol", "atletizm", "maç", "oyuncu"],
        }

        # Metni küçük harfe çevir ve kelimelere ayır
        words = text.lower().split()

        # Her kategori için eşleşen kelimeleri say
        topic_scores = {topic: sum(word in words for word in keywords) for topic, keywords in topics.items()}

        # En yüksek skora sahip olan konuyu belirle
        predicted_topic = max(topic_scores, key=topic_scores.get)

        # Eğer hiç eşleşme yoksa
        if topic_scores[predicted_topic] == 0:
            predicted_topic = "Belirtilen bir konu bulunamadı"

        # Sonuç döndür
        return f"Konu: {predicted_topic}"

    except Exception as e:
        return f"Metin analizi sırasında hata oluştu: {e}"

# Duygu analizi (Angry vs Happy)
def analyze_sentiment(text):
    angry_keywords = ["öfke", "sinir", "kızgın", "nefret", "öfkeli"]
    happy_keywords = ["mutlu", "gülmek", "neşeli", "sevinç", "şen"]

    words = text.lower().split()

    # Öfke ve mutluluk kelimelerinin sayısını hesapla
    angry_count = sum(word in angry_keywords for word in words)
    happy_count = sum(word in happy_keywords for word in words)

    # Toplam kelime sayısını hesapla
    total_words = len(words)
    if total_words == 0:
        return "Neutral (No words to analyze)"

    # Yüzdeleri hesapla
    angry_percentage = (angry_count / total_words) * 100
    happy_percentage = (happy_count / total_words) * 100

    # Sonuç olarak yüzdeleri döndür
    return f"Öfkeli: {angry_percentage:.2f}% | Mutlu: {happy_percentage:.2f}%"

# Ses kaydetme butonu
record_button = tk.Button(root, text="Ses Kaydet", bg="#4CAF50", fg="white", font=("Helvetica", 14), command=start_recording)
record_button.pack(pady=10, padx=20, fill="x")

# Kaydı bitirme butonu
stop_button = tk.Button(root, text="Kaydı Bitir", bg="#f44336", fg="white", font=("Helvetica", 14), command=stop_recording)
stop_button.pack(pady=10, padx=20, fill="x")

root.mainloop()
