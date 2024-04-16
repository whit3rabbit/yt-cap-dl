# YouTube Caption Downloader

YouTube Caption Downloader is a Python-based tool that allows you to scrape video links from YouTube channels, download and clean video captions, and manage proxies for efficient downloading.

## Features

- Scrape video links from YouTube channels
- Download and clean video captions
- Manage and validate proxies for downloading
- Store video links, downloaded videos, and cleaned captions in an SQLite database
- Concurrent downloading of captions using multiple worker threads

## Prerequisites

- Python 3.6 or higher
- Chrome web browser

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/whit3rabbit/yt-cap-dl
   ```

2. Navigate to the project directory:
   ```
   cd yt-cap-dl
   ```

3. Install the required dependencies:
   ```
   python -m venv venv
   pip install -r requirements.txt
   ```

## Usage

### Step 1: Populate Video Links

Before running the caption grabber, you must first populate the video links for the desired YouTube channel. To do this, run the following command:

```
python main.py video-links <channel_name>
```

Replace `<channel_name>` with the name of the YouTube channel you want to scrape video links from. You can provide the channel name with or without the "@" symbol.

This command will scrape the video links from the specified YouTube channel and store them in the SQLite database.

### Step 2: Download and Clean Video Captions

Once you have populated the video links, you can proceed to download and clean the video captions. To do this, run the following command:

```
python main.py download-captions <channel_name> [-w/--workers <num_workers>] [--no-proxy]
```

Replace `<channel_name>` with the name of the YouTube channel you want to download captions for. You can provide the channel name with or without the "@" symbol.

Optional arguments:
- `-w/--workers <num_workers>`: Specify the number of worker threads to use for concurrent downloading. Default is 1.
- `--no-proxy`: Disable the use of proxies for downloading captions.

This command will download and clean the video captions for the specified YouTube channel using the video links stored in the database.

### Proxy Management

The tool also provides functionality to manage proxies for efficient downloading. You can perform the following actions related to proxies:

```
python main.py proxy-manager <action>
```

Replace `<action>` with one of the following:
- `download`: Download the latest proxies from a GitHub repository.
- `check`: Check the validity of unchecked proxies in the database.
- `update`: Download the latest proxies and check their validity.
- `all`: Perform both the `download` and `check` actions.

## Database

The project uses an SQLite database to store video links, downloaded videos, and cleaned captions. The database file is named `youtube_data.db` and is created automatically when running the scripts.

## Important Note

It is crucial to populate the video links using the `video-links` command before running the caption grabber. The caption grabber relies on the video links stored in the database to download and clean the captions. Failing to populate the video links prior to running the caption grabber will result in no captions being downloaded.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.