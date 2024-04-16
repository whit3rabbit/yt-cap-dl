import re

def normalize_channel_name(channel_name):
    if not channel_name.startswith('@'):
        channel_name = '@' + channel_name
    return channel_name

def validate_proxy_format(proxy):
    proxy_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$')
    return proxy_pattern.match(proxy) is not None

def load_proxies_from_file(file_path):
    with open(file_path, 'r') as file:
        proxies = file.read().strip().split('\n')

    valid_proxies = []
    invalid_proxies = []

    for proxy in proxies:
        if validate_proxy_format(proxy):
            valid_proxies.append(proxy)
        else:
            invalid_proxies.append(proxy)

    return valid_proxies, invalid_proxies