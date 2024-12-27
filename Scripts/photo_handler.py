from aiogram import types
from io import BytesIO

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


async def cloudinary_upload(byteio_content, name):
    """
    Uploads an image to Cloudinary.

    Args:
        byteio_content (BytesIO): The image data in BytesIO format.
        name (str): A unique file name for the upload (used as public_id in Cloudinary).

    Returns:
        dict: The upload result, including the URL of the uploaded image, or None in case of an error.
    """
    cloudinary.config(
        cloud_name="********",  # Your Cloudinary account name
        api_key="********",  # Cloudinary API key
        api_secret="********",  # Cloudinary API secret key
        secure=True
    )

    result = cloudinary.uploader.upload(file=byteio_content, public_id=name)
    return result


async def photo_handler(message: types.Message):
    """
    Handles a message containing a photo and uploads it to Cloudinary.

    Args:
        message (types.Message): The message containing the photo.

    Returns:
        str: The URL of the uploaded image if the upload is successful.
        None: If the message does not contain a photo or an upload error occurs.
    """
    if not message.photo:
        return None
    
    # Get the last photo (highest quality)
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path

    # Download the file content
    file_content = await message.bot.download_file(file_path)

    # Convert the file content to BytesIO
    byteio_content = BytesIO(file_content.read())
    
    # Use the user's ID as the file name
    name = message.from_user.id
    telegraph_link = await cloudinary_upload(byteio_content, name)
    if telegraph_link:
        return telegraph_link.get("url")
    else:
        print("Failed to upload to Telegraph.")
