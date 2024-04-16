import os
import tempfile
from yt_dlp import YoutubeDL
import webvtt
import re
import backoff
import random
import concurrent.futures
from yt_dlp.utils import DownloadError, ExtractorError
from .database import load_video_links, mark_video_downloaded, save_cleaned_subtitles, load_valid_proxies, DatabaseConnection
from .utils import normalize_channel_name
import signal

class GracefulInterruptHandler(object):
    def __init__(self):
        self.interrupted = False
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signal, frame):
        self.interrupted = True
        print("Interrupt received, shutting down...")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

class YouTubeCaptionDownloader:
    def __init__(self, temp_dir, use_proxies=True, cookies_file=None):
        self.temp_dir = temp_dir
        self.proxies = load_valid_proxies() if use_proxies else []
        self.active_proxies = list(self.proxies)
        self.cookies_file = cookies_file

    @backoff.on_exception(backoff.expo, (DownloadError, ExtractorError), max_tries=10, max_time=300, )
    def download_captions(self, video_url, channel_name, video_title, proxy=None, cookies_file=None):
        base_vtt_path = os.path.join(self.temp_dir, f"{video_title}")
        ydl_opts = {
            'outtmpl': base_vtt_path + '.%(ext)s',  # General template for output files
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'skip_download': True,  # Ensure no media is downloaded
            'quiet': False,
            'noprogress': True,
        }
        if proxy:
            ydl_opts['proxy'] = proxy
            
        if self.cookies_file:
            ydl_opts["cookiefile"] = self.cookies_file

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                ydl.download([video_url])  # Ensure subtitles are explicitly downloaded
                subtitle_file = base_vtt_path + '.en.vtt'  # Assume '.en.vtt' extension
                if os.path.exists(subtitle_file):
                    print(f"[+] Captions downloaded: {video_url}")
                    return subtitle_file
                else:
                    generated_files = os.listdir(self.temp_dir)  # Debug: List files to find what was actually saved
                    print("Generated files:", generated_files)  # This will help identify what files were actually created
                    print("[-] Captions file not found after download attempt.")
                    return None
        except (DownloadError, ExtractorError) as e:
            print(f"[-] Download error with proxy {proxy if proxy else 'no proxy'}: {str(e)}")
            if proxy and proxy in self.active_proxies:
                self.active_proxies.remove(proxy)
            raise

    def retry_download(self, video_url, channel_name, video_title):
        if not self.active_proxies and self.proxies:  # Check if proxies are supposed to be used but none are active
            print("No active proxies available.")
            return None  # Optionally, you could return None or try a direct download

        retry_count = 0
        proxy = None  # Default to None, which implies no proxy

        # Use proxies if available, otherwise attempt a direct download
        while retry_count == 0 or self.active_proxies:
            if self.active_proxies:
                proxy = random.choice(self.active_proxies)
            retry_count += 1
            print(f"Retry attempt {retry_count} for: {video_url} using proxy {proxy if proxy else 'no proxy'}")
            
            try:
                temp_vtt_path = self.download_captions(video_url, channel_name, video_title, proxy)
                if temp_vtt_path:
                    return temp_vtt_path  # Successfully downloaded
            except Exception as e:
                print(f"Retry failed due to error: {e}")
                if self.active_proxies and proxy in self.active_proxies:
                    self.active_proxies.remove(proxy)  # Remove failed proxy from the list
                if not self.active_proxies and self.proxies:
                    print("No more proxies available, stopping retry.")
                    break  # Exit the loop if no proxies are left

        # If no proxies were originally provided, the loop runs once with proxy=None
        if not self.proxies:
            print("Direct download attempt failed.")
        return None


    def process_single_link(self, video_url, channel_name, video_title):
        print(f"Processing link: {video_url}")
        try:
            temp_vtt_path = self.retry_download(video_url, channel_name, video_title)
            if temp_vtt_path:
                cleaned_subtitles = self.clean_captions(temp_vtt_path, channel_name, video_title, video_url)
                if cleaned_subtitles:
                    print(f"Cleaned subtitles obtained for: {video_url}")
                    mark_video_downloaded(video_url, channel_name, video_title)
                    os.unlink(temp_vtt_path)
                    return True
                else:
                    print(f"Failed to clean subtitles for: {video_url}")
            else:
                print(f"Failed to download captions for: {video_url}")
        except Exception as e:
            print(f"Error processing link {video_url}: {str(e)}")
        return False

    def clean_captions(self, temp_vtt_path, channel_name, video_title, video_url):
        try:
            if not os.path.exists(temp_vtt_path):
                print(f"File not found: {temp_vtt_path}")
                return None

            print(f"Cleaning captions for: {temp_vtt_path}")

            vtt = webvtt.read(temp_vtt_path)
            all_text = [self.clean_cue(caption.text) for caption in vtt]
            unique_text = list(self.remove_duplicates_keep_longer(all_text))
            cleaned_subtitles = '\n'.join(unique_text)

            # Pass all required parameters to save_cleaned_subtitles
            save_cleaned_subtitles(video_url, channel_name, video_title, cleaned_subtitles)
            return cleaned_subtitles

        except Exception as e:
            print(f"Error cleaning captions: {str(e)}")
        return None


    @staticmethod
    def clean_cue(cue):
        cue = re.sub(r'<[^>]+>', '', cue)
        cue = re.sub(r'\s+', ' ', cue).strip()
        return cue

    @staticmethod
    def remove_duplicates_keep_longer(text_lines):
        previous_line = ""
        for line in text_lines:
            line = line.strip()
            if line.startswith(previous_line):
                previous_line = line
            elif not previous_line.startswith(line):
                if previous_line:
                    yield previous_line
                previous_line = line
        if previous_line:
            yield previous_line


def youtube_downloader(channel_name, num_workers=1, use_proxies=True, cookies_file=None):
    channel_name = normalize_channel_name(channel_name)
    video_links = load_video_links(channel_name)
    if not video_links:
        print(f"No video links found for channel: {channel_name}. Run the video link grabber first.")
        return

    with tempfile.TemporaryDirectory() as temp_dir, \
         DatabaseConnection('youtube_data.db') as cursor, \
         GracefulInterruptHandler() as handler:
        downloader = YouTubeCaptionDownloader(temp_dir, use_proxies=use_proxies, cookies_file=cookies_file)
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for link in video_links:
                cursor.execute("SELECT video_title FROM video_links WHERE video_url = ?", (link,))
                result = cursor.fetchone()
                if result:
                    video_title = result[0]
                    if handler.interrupted:
                        print("Operation interrupted before starting all tasks.")
                        break
                    future = executor.submit(downloader.process_single_link, link, channel_name, video_title)
                    futures.append(future)
                else:
                    print(f"Video title not found for link: {link}")

            for future in concurrent.futures.as_completed(futures):
                if handler.interrupted:
                    print("Operation interrupted during processing.")
                    break
                try:
                    result = future.result()
                    if not result:
                        print("Failed to process link")
                except Exception as e:
                    print(f"Error processing link: {str(e)}")

            if handler.interrupted:
                for future in futures:
                    future.cancel()
                executor.shutdown(wait=False)
                print("Shutdown completed after interrupt.")