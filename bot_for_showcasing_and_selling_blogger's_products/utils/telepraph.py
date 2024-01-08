# Script for uploading media file to Telegraph servers for Telegram.
# Accepts only photos and returns the file link (or None).

import aiohttp
import json
from aiogram import types
from aiohttp.formdata import FormData
from io import BytesIO


async def telegraph_byteio_upload(byteio_content):
    file_content = byteio_content.getvalue()

    url = 'https://telegra.ph/upload'
    data = FormData()
    data.add_field('file', file_content, filename='file', content_type='image/png')
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            result = await response.text()
            
    response_json = json.loads(result)
    
    if isinstance(response_json, list) and len(response_json) > 0 and 'src' in response_json[0]:
        telegraph_url = response_json[0]['src']
        telegraph_url = f'https://telegra.ph{telegraph_url}'
        return telegraph_url

async def photo_handler(message: types.Message):
    if message.content_type not in "photo":
        return None
    photo = await message.photo[-1].download(BytesIO())
    telegraph_link = await telegraph_byteio_upload(photo)
    
    return telegraph_link
