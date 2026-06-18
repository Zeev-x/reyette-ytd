from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

import threading
import os
import glob
import yt_dlp
import imageio_ffmpeg
import subprocess


# =========================
# DUMMY LOGGER (FIX ERROR)
# =========================
class DummyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


class MainLayout(BoxLayout):

    # =========================
    # LOG SYSTEM
    # =========================
    def add_log(self, text):
        def update(dt):
            self.ids.log.text += text + "\n"
        Clock.schedule_once(update)

    def clear_log(self):
        self.ids.log.text = ""

    # =========================
    # GET FORMATS (YT-DLP API)
    # =========================
    def get_formats(self):
        threading.Thread(target=self._get_formats, daemon=True).start()

    def _get_formats(self):
        url = self.ids.url.text.strip()

        if not url:
            self.add_log("❌ Masukkan URL terlebih dahulu!")
            return

        self.add_log("=== MENGAMBIL KUALITAS ===")

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'logger': DummyLogger(),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(url, download=False)

            qualities = set()

            for fmt in data.get("formats", []):
                h = fmt.get("height")
                if h:
                    qualities.add(f"{h}p")

            qualities = sorted(qualities, key=lambda x: int(x[:-1]))

            if not qualities:
                self.add_log("❌ Tidak ada kualitas ditemukan")
                return

            def update(dt):
                self.ids.quality.values = qualities
                self.ids.quality.text = qualities[-1]

            Clock.schedule_once(update)

            self.add_log("✅ Kualitas ditemukan:")
            for q in qualities:
                self.add_log(" • " + q)

        except Exception as e:
            self.add_log(f"❌ Error: {e}")

    # =========================
    # MP3 DOWNLOAD
    # =========================
    def download_mp3(self):
        threading.Thread(target=self._download_mp3, daemon=True).start()

    def _download_mp3(self):
        url = self.ids.url.text.strip()

        if not url:
            self.add_log("❌ Masukkan URL terlebih dahulu!")
            return

        os.makedirs("downloads/audio", exist_ok=True)

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        self.add_log("=== DOWNLOAD MP3 ===")

        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'downloads/audio/%(title)s.%(ext)s',
                'ffmpeg_location': ffmpeg_path,
                'logger': DummyLogger(),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.add_log("✅ Download MP3 selesai")

        except Exception as e:
            self.add_log(f"❌ Error: {e}")

    # =========================
    # MP4 DOWNLOAD
    # =========================
    def download_mp4(self):
        threading.Thread(target=self._download_mp4, daemon=True).start()

    def _download_mp4(self):
        url = self.ids.url.text.strip()
        quality = self.ids.quality.text

        if not url:
            self.add_log("❌ Masukkan URL terlebih dahulu!")
            return

        os.makedirs("downloads/video", exist_ok=True)
        os.makedirs("downloads/temp", exist_ok=True)

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        self.add_log("=== DOWNLOAD MP4 ===")

        try:
            if quality.endswith("p"):
                height = quality[:-1]
                fmt = f"bestvideo[height<={height}]+bestaudio/best"
            else:
                fmt = "best"

            temp_path = "downloads/temp/%(title)s.%(ext)s"

            ydl_opts = {
                'format': fmt,
                'outtmpl': temp_path,
                'merge_output_format': 'mp4',
                'ffmpeg_location': ffmpeg_path,
                'logger': DummyLogger(),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            files = glob.glob("downloads/temp/*.mp4")

            if not files:
                self.add_log("❌ File tidak ditemukan")
                return

            source = max(files, key=os.path.getmtime)
            name = os.path.basename(source)
            output = os.path.join("downloads/video", name)

            self.add_log("=== KONVERSI H.264 ===")

            cmd = [
                ffmpeg_path,
                "-y",
                "-i", source,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                output
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",   # ✅ fix encoding
                errors="replace"    # ✅ hindari crash
            )

            for line in process.stdout:
                self.add_log(line.strip())

            process.wait()

            if process.returncode == 0:
                try:
                    os.remove(source)
                except:
                    pass

                self.add_log("✅ Video selesai dikonversi")
                self.add_log(f"📁 File: {output}")
            else:
                self.add_log("❌ Gagal konversi")

        except Exception as e:
            self.add_log(f"❌ Error: {e}")


class ReyetteApp(App):
    def build(self):
        return MainLayout()


if __name__ == "__main__":
    ReyetteApp().run()
