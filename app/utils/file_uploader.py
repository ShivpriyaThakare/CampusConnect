import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
from flask import current_app

def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file, folder_subpath='images', max_size=(1200, 1200), compress_quality=85):
    """
    Saves an uploaded file after sanitizing and processing with Pillow if image.
    Returns relative filename string or None.
    """
    if not file or file.filename == '':
        return None

    if not allowed_file(file.filename):
        raise ValueError('Invalid file format. Allowed formats: PNG, JPG, JPEG, GIF, WEBP, PDF.')

    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_subpath)
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, unique_filename)

    if ext in {'png', 'jpg', 'jpeg', 'webp'}:
        try:
            image = Image.open(file)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert RGBA to RGB if saving as JPEG
            if ext in {'jpg', 'jpeg'} and image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
                
            image.save(file_path, optimize=True, quality=compress_quality)
        except Exception:
            file.seek(0)
            file.save(file_path)
    else:
        file.seek(0)
        file.save(file_path)

    return f"uploads/{folder_subpath}/{unique_filename}"


def try_save_uploaded_file(file, folder_subpath='images', max_size=(1200, 1200), compress_quality=85):
    """
    Wrapper around save_uploaded_file that catches validation errors.
    Returns (saved_path_or_none, error_message_or_none).
    """
    if not file or file.filename == '':
        return None, None
    try:
        return save_uploaded_file(
            file,
            folder_subpath=folder_subpath,
            max_size=max_size,
            compress_quality=compress_quality
        ), None
    except ValueError as exc:
        return None, str(exc)
