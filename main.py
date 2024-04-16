import argparse
import asyncio
from youtube_caption_downloader.video_link_grabber import video_link_grabber
from youtube_caption_downloader.proxy_manager import proxy_manager
from youtube_caption_downloader.youtube_downloader import youtube_downloader
from youtube_caption_downloader.database import init_db
import logging

class IgnoreWarningFilter(logging.Filter):
    def filter(self, record):
        # Return False to prevent the message from being logged if it's a warning or the specific OSError
        return not (record.levelno == logging.WARNING or 
                    (record.levelno == logging.ERROR and 
                     "OSError: [WinError 6] The handle is invalid" in record.getMessage()))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().addFilter(IgnoreWarningFilter())

async def main():
    parser = argparse.ArgumentParser(description='YouTube Caption Downloader')
    subparsers = parser.add_subparsers(dest='command', required=True)

    video_links_parser = subparsers.add_parser('video-links', help='Scrape video links from a YouTube channel')
    video_links_parser.add_argument('channel_name', help='YouTube channel name (with or without @)')
    video_links_parser.add_argument("--cookies-file", help="Path to the cookies file, example: cookies.json")

    proxy_manager_parser = subparsers.add_parser('proxy-manager', help='Manage proxies')
    proxy_manager_parser.add_argument('action', choices=['download', 'check', 'recheck', 'update', 'all', 'count', 'delete', 'load'], help='Action to perform')
    proxy_manager_parser.add_argument('--file', help='Path to the text file containing proxies (required for the "load" action)')

    youtube_downloader_parser = subparsers.add_parser('download-captions', help='Download and clean captions for a YouTube channel')
    youtube_downloader_parser.add_argument('channel_name', help='YouTube channel name (with or without @)')
    youtube_downloader_parser.add_argument('-w', '--workers', type=int, default=1, help='Number of worker threads')
    youtube_downloader_parser.add_argument('--no-proxy', action='store_true', help='Disable the use of proxies')
    youtube_downloader_parser.add_argument('--cookies-file', help="Path to the cookies file, example: cookies.json")

    init_db_parser = subparsers.add_parser('init-db', help='Initialize the SQLite database')

    args = parser.parse_args()

    try:
        if args.command == 'video-links':
            video_link_grabber(args.channel_name, args.cookies_file)
        elif args.command == 'proxy-manager':
            await proxy_manager(args.action, args.file)
        elif args.command == 'download-captions':
            use_proxies = not args.no_proxy
            await youtube_downloader(args.channel_name, args.workers, use_proxies, args.cookies_file)
        elif args.command == 'init-db':
            init_db()
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Cancelling tasks...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        await asyncio.gather(*tasks, return_exceptions=True)
        print("Tasks cancelled. Shutting down gracefully.")
    finally:
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
