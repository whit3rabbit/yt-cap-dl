import json
from pathlib import Path
import undetected_chromedriver as uc_orig
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import random
import logging
from .database import save_video_links_batch, get_video_link_count
from .utils import normalize_channel_name
import datetime

# https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/955
# Make a new class from uc_orig.Chrome and redefine quit() function to suppress OSError
class Chrome(uc_orig.Chrome):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def quit(self):
        try:
            super().quit()
        except OSError:
            pass

def scroll_page(driver):
    # Simulate scrolling to load dynamic content
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    while True:
        logging.info("Scrolling to load more content...")
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(random.uniform(6.0, 10.0))
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            # Scroll again to check if more content was loaded
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(random.uniform(8.0, 10.0))  # Increase the delay to allow more time for loading
            new_height_2 = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height_2 == new_height:
                break
        last_height = new_height

def scrape_videos(driver, channel_url, channel_name, initial_count):
    driver.get(channel_url)
    time.sleep(random.uniform(2.5, 4.9))  # Random sleep to mimic user interaction

    # Accept cookies if the button is present
    try:
        logging.info("Attempting to accept cookies...")
        # Find the button by its text content "Accept all"
        accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept all')]"))
        )
        accept_button.click()
        logging.info("Cookies accepted successfully.")
    except TimeoutException:
        logging.warning("No cookie acceptance button found or clickable within the timeout period.")

    scroll_page(driver)  # Scroll to ensure all videos are loaded
    logging.info("Finished scrolling to load all videos")
    videos_to_save = []
    seen_urls = set()

    try:
        video_elements = WebDriverWait(driver, 30).until(
            lambda driver: [elem for elem in driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']") if elem.get_attribute('title').strip()]
        )
        logging.info(f"Found {len(video_elements)} video elements")
    except TimeoutException:
        logging.error("Failed to load YouTube page content within the timeout period.")
        return

    # Get current datetime
    date_scraped = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for video_link in video_elements:
        try:
            video_url = video_link.get_attribute('href')
            video_title = video_link.get_attribute('title').strip()

            if video_url not in seen_urls and video_title:
                seen_urls.add(video_url)
                videos_to_save.append((video_url, video_title, date_scraped, channel_name))
                print(f"URL: {video_url}, Title: {video_title}, Date Scraped: {date_scraped}")
        except Exception as e:
            logging.error(f"Error processing video element: {e}")

    save_video_links_batch(videos_to_save)
    updated_count = get_video_link_count(channel_name)
    logging.info(f"Already in database for {channel_name}: {initial_count}")
    logging.info(f"New links saved for {channel_name}: {len(videos_to_save)}")
    logging.info(f"Updated total links for {channel_name}: {updated_count}")


def video_link_grabber(channel_name, cookies_file=None):
    channel_name = normalize_channel_name(channel_name)
    channel_url = f"https://www.youtube.com/{channel_name}/videos"
    
    initial_count = get_video_link_count(channel_name)
    print(f"Number of links in the database for {channel_name} before scraping: {initial_count}")
    
    try:
        logging.info("Running Chrome browser in background. Please wait")
        options = uc_orig.ChromeOptions()
        driver = uc_orig.Chrome(options=options, headless=False, use_subprocess=False)

        # Navigate to the YouTube channel's video page
        driver.get(channel_url)
        
        # Wait a short moment to ensure page loads sufficiently to accept cookies
        time.sleep(2)

        # Load cookies from file if provided
        if cookies_file and Path(cookies_file).exists():
            logging.info(f"Loading cookies from file: {cookies_file}")
            cookies = json.loads(Path(cookies_file).read_text())
            for cookie in cookies:
                if 'domain' in cookie and '.youtube.com' in cookie['domain']:  # Check if the cookie domain is correct
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        logging.warning(f"Could not add cookie: {e}")
            # Refresh the page to ensure cookies take effect
            driver.refresh()

        scrape_videos(driver, channel_url, channel_name, initial_count)

        # Save cookies to file after session to ensure they are current
        if cookies_file:
            logging.info(f"Saving cookies to file: {cookies_file}")
            Path(cookies_file).write_text(
                json.dumps(driver.get_cookies(), indent=2)
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        driver.close()
