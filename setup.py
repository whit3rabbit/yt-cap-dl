from setuptools import setup, find_packages

setup(
    name='yt-cap-dl',
    version='1.0.0',
    description='A tool to scrape video links, download and clean captions from YouTube channels',
    author='whit3rabbit',
    author_email='whiterabbit@protonmail.com',
    url='https://github.com/whit3rabbit/yt-cap-dl',
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'backoff',
        'requests',
        'undetected-chromedriver',
        'urllib3',
        'webvtt-py',
        'yt-dlp',
        'tqdm',
    ],
    entry_points={
        'console_scripts': [
            'yt-cap-dl=yt-cap-dl.main:main'
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)