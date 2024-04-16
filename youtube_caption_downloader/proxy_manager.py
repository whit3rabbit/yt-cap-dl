import asyncio
import aiohttp
import datetime
import logging
from .database import save_checked_proxy, load_unchecked_proxies, load_valid_proxies, count_valid_proxies, load_all_proxies, delete_all_proxies, load_proxies_from_file
from tqdm import tqdm

async def fetch_proxies_from_github():
    url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    proxies = await response.text()
                    return proxies.strip().split('\n')
                else:
                    logging.error(f"Failed to fetch proxies: HTTP {response.status}")
        except aiohttp.ClientError as e:
            logging.error(f"Error during proxy fetch: {e}")
    return []

async def download_latest_proxies():
    logging.info("Fetching proxies from GitHub...")
    proxies = await fetch_proxies_from_github()
    if proxies:
        logging.info(f"Fetched {len(proxies)} proxies from GitHub")
        logging.info("Saving proxies to the database...")
        for proxy in tqdm(proxies, desc="Saving proxies", unit="proxy"):
            save_checked_proxy(proxy, is_valid=None, last_checked_date=None)
        logging.info(f"Saved {len(proxies)} proxies to the database")
    else:
        logging.info("No proxies were fetched from GitHub")

async def validate_proxy(session, proxy, max_retries=2):
    url = 'https://www.youtube.com'
    for attempt in range(max_retries):
        try:
            async with session.get(url, proxy=f'http://{proxy}', timeout=15) as response:
                if response.status == 200:
                    return proxy
        except aiohttp.ClientConnectorError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Connection error: {e}")
        except aiohttp.ClientResponseError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Response error: {e}")
        except aiohttp.ServerDisconnectedError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Server disconnected: {e}")
        except aiohttp.ClientOSError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - OS error: {e}")
        except aiohttp.ClientSSLError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - SSL error: {e}")
        except aiohttp.ClientProxyConnectionError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Proxy connection error: {e}")
        except asyncio.TimeoutError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Timeout error: {e}")
        except ConnectionResetError as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Connection reset error: {e}")
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed for proxy {proxy} - Unexpected error: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(1 ** (attempt + 1))  # Exponential backoff
        else:
            return None
    
    return None

async def validate_proxies_concurrently(proxies, max_workers=20):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for proxy in proxies:
            task = asyncio.create_task(validate_proxy(session, proxy))
            tasks.append(task)
        
        results = []
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Validating proxies", unit="proxy"):
            result = await future
            if result:
                results.append(result)
        
        return results

async def check_proxies():
    unchecked_proxies = load_unchecked_proxies()
    if unchecked_proxies:
        logging.info(f"Found {len(unchecked_proxies)} unchecked proxies")
        valid_proxies = await validate_proxies_concurrently(unchecked_proxies)
        logging.info(f"Found {len(valid_proxies)} valid proxies")
        for proxy in unchecked_proxies:
            is_valid = 1 if proxy in valid_proxies else 0
            save_checked_proxy(proxy, is_valid, datetime.datetime.now())
    else:
        logging.info("No unchecked proxies found")

async def update_proxies():
    await download_latest_proxies()
    await check_proxies()

async def proxy_manager(action, file_path=None):
    if action == 'download':
        await download_latest_proxies()
    elif action == 'check':
        await check_proxies()
    elif action == 'delete':
        delete_all_proxies()
        logging.info("All proxies deleted from the database.")
    elif action == 'load':
        if file_path:
            count = load_proxies_from_file(file_path)
            logging.info(f"Loaded {count} valid proxies from file: {file_path}")
        else:
            logging.error("No file path provided for loading proxies.")
    elif action == 'recheck':
        while True:
            choice = input("Recheck all proxies or only valid proxies? (all/valid/cancel): ")
            if choice.lower() == 'all':
                proxies = load_all_proxies()
                break
            elif choice.lower() == 'valid':
                proxies = load_valid_proxies()
                break
            elif choice.lower() == 'cancel':
                logging.info("Recheck cancelled.")
                return
            else:
                print("Invalid choice. Please enter 'all', 'valid', or 'cancel'.")        
        if proxies:
            logging.info(f"Rechecking {len(proxies)} proxies...")
            valid_proxies = await validate_proxies_concurrently(proxies)
            logging.info(f"Found {len(valid_proxies)} valid proxies")
            for proxy in proxies:
                is_valid = 1 if proxy in valid_proxies else 0
                save_checked_proxy(proxy, is_valid, datetime.datetime.now())
        else:
            logging.info("No proxies found to recheck.")
    elif action == 'count':
        count = count_valid_proxies()
        logging.info(f"Number of valid proxies in the database: {count}")
    elif action == 'all':
        await download_latest_proxies()
        await check_proxies()
    else:
        logging.error(f"Invalid action: {action}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    action = 'all'  # Default action
    asyncio.run(proxy_manager(action))