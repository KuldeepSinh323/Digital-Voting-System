import os
import urllib.request

url = ('https://github-production-user-asset-6210df.s3.amazonaws.com/99495469/'
       '326325681-780a5cea-75a6-4990-bf7c-a2018f509ed9.png?'
       'X-Amz-Algorithm=AWS4-HMAC-SHA256&'
       'X-Amz-Credential=AKIAVCODYLSA53PQK4ZA%2F20260415%2Fus-east-1%2Fs3%2Faws4_request&'
       'X-Amz-Date=20260415T145522Z&'
       'X-Amz-Expires=300&'
       'X-Amz-Signature=88854f11fe5d8b89a3c1d6551283163ffc36e3bc8883da9dea846013986c4719&'
       'X-Amz-SignedHeaders=host&'
       'response-content-type=image%2Fpng')

path = os.path.join('vote', 'static', 'images')
os.makedirs(path, exist_ok=True)
file_path = os.path.join(path, 'home-bg.png')
print('Downloading to', file_path)
urllib.request.urlretrieve(url, file_path)
print('Done')
