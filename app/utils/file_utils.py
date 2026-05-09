"""
Утилиты для работы с файлами
"""
import os
import shutil
from pathlib import Path
from typing import Optional, List
import hashlib
from datetime import datetime
import mimetypes


def get_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Вычислить хеш файла
    
    Args:
        file_path: Путь к файлу
        algorithm: Алгоритм хеширования (md5, sha1, sha256)
        
    Returns:
        Хеш файла в шестнадцатеричном формате
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def get_file_info(file_path: Path) -> dict:
    """
    Получить информацию о файле
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Словарь с информацией о файле
    """
    stat = file_path.stat()
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    return {
        "name": file_path.name,
        "stem": file_path.stem,
        "suffix": file_path.suffix,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "mime_type": mime_type,
        "is_file": file_path.is_file(),
        "is_dir": file_path.is_dir()
    }


def ensure_directory(dir_path: Path) -> Path:
    """
    Убедиться, что директория существует
    
    Args:
        dir_path: Путь к директории
        
    Returns:
        Путь к директории
    """
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_delete_file(file_path: Path) -> bool:
    """
    Безопасно удалить файл
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        True если файл успешно удален, иначе False
    """
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"Ошибка удаления файла {file_path}: {e}")
        return False


def safe_delete_directory(dir_path: Path) -> bool:
    """
    Безопасно удалить директорию
    
    Args:
        dir_path: Путь к директории
        
    Returns:
        True если директория успешно удалена, иначе False
    """
    try:
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)
            return True
        return False
    except Exception as e:
        print(f"Ошибка удаления директории {dir_path}: {e}")
        return False


def copy_file_with_hash(source: Path, destination: Path, use_hash: bool = True) -> Path:
    """
    Скопировать файл, используя хеш в имени
    
    Args:
        source: Исходный файл
        destination: Директория назначения
        use_hash: Использовать хеш в имени файла
        
    Returns:
        Путь к скопированному файлу
    """
    ensure_directory(destination)
    
    if use_hash:
        file_hash = get_file_hash(source)
        new_filename = f"{file_hash}{source.suffix}"
    else:
        new_filename = source.name
    
    dest_path = destination / new_filename
    shutil.copy2(source, dest_path)
    
    return dest_path


def move_file(source: Path, destination: Path) -> Path:
    """
    Переместить файл
    
    Args:
        source: Исходный файл
        destination: Путь назначения (файл или директория)
        
    Returns:
        Путь к перемещенному файлу
    """
    if destination.is_dir():
        dest_path = destination / source.name
    else:
        dest_path = destination
    
    shutil.move(str(source), str(dest_path))
    return dest_path


def get_files_by_extension(directory: Path, extensions: List[str]) -> List[Path]:
    """
    Получить список файлов с определенными расширениями
    
    Args:
        directory: Директория для поиска
        extensions: Список расширений (с точкой или без)
        
    Returns:
        Список путей к файлам
    """
    files = []
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
    
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            files.append(file_path)
    
    return sorted(files)


def clean_directory(directory: Path, keep_extensions: Optional[List[str]] = None) -> int:
    """
    Очистить директорию, удалив все файлы (или кроме указанных расширений)
    
    Args:
        directory: Директория для очистки
        keep_extensions: Список расширений, которые не нужно удалять
        
    Returns:
        Количество удаленных файлов
    """
    deleted_count = 0
    
    for file_path in directory.iterdir():
        if file_path.is_file():
            if keep_extensions is None or file_path.suffix.lower() not in keep_extensions:
                if safe_delete_file(file_path):
                    deleted_count += 1
    
    return deleted_count


def get_unique_filename(directory: Path, filename: str) -> str:
    """
    Получить уникальное имя файла в директории
    
    Args:
        directory: Директория
        filename: Имя файла
        
    Returns:
        Уникальное имя файла
    """
    file_path = directory / filename
    counter = 1
    
    while file_path.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        new_filename = f"{stem}_{counter}{suffix}"
        file_path = directory / new_filename
        counter += 1
    
    return file_path.name


def validate_pdf_file(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Валидировать PDF файл
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "File does not exist"
    
    if not file_path.is_file():
        return False, "Path is not a file"
    
    if file_path.suffix.lower() != '.pdf':
        return False, "File is not a PDF"
    
    # Проверяем, что файл не пустой
    if file_path.stat().st_size == 0:
        return False, "File is empty"
    
    # Проверяем, что это действительно PDF (по сигнатуре)
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                return False, "Invalid PDF file signature"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"
    
    return True, None
