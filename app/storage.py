"""
Модуль для работы с MinIO object storage.
"""
import os
from io import BytesIO
from typing import Optional, Tuple
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, status


class MinIOStorage:
    """Класс для работы с MinIO хранилищем."""

    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_name = os.getenv("MINIO_BUCKET", "documents")
        self.use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        self.public_url = os.getenv("MINIO_PUBLIC_URL", f"http://localhost:9000")

        self._client: Optional[MinIO] = None
        self._ensure_bucket_exists()

    @property
    def client(self) -> Minio:
        """Ленивая инициализация клиента MinIO."""
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.use_ssl
            )
        return self._client

    def _ensure_bucket_exists(self):
        """Создаёт бакет, если он не существует."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Bucket '{self.bucket_name}' created successfully")
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")

    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Загружает файл в MinIO.

        Args:
            file_data: Данные файла в байтах
            object_name: Имя объекта в хранилище
            content_type: MIME-тип файла

        Returns:
            URL для доступа к файлу

        Raises:
            HTTPException: Если загрузка не удалась
        """
        try:
            data_stream = BytesIO(file_data)
            self.client.put_object(
                self.bucket_name,
                object_name,
                data_stream,
                length=len(file_data),
                content_type=content_type
            )
            return self._get_file_url(object_name)
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )

    def download_file(self, object_name: str) -> bytes:
        """
        Скачивает файл из MinIO.

        Args:
            object_name: Имя объекта в хранилище

        Returns:
            Данные файла в байтах

        Raises:
            HTTPException: Если файл не найден или скачивание не удалось
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response.read()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}"
            )

    def delete_file(self, object_name: str) -> bool:
        """
        Удаляет файл из MinIO.

        Args:
            object_name: Имя объекта в хранилище

        Returns:
            True если файл успешно удалён

        Raises:
            HTTPException: Если удаление не удалось
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )

    def file_exists(self, object_name: str) -> bool:
        """
        Проверяет существование файла в MinIO.

        Args:
            object_name: Имя объекта в хранилище

        Returns:
            True если файл существует
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def _get_file_url(self, object_name: str) -> str:
        """
        Генерирует presigned URL для доступа к файлу (1 час действия).

        Args:
            object_name: Имя объекта в хранилище

        Returns:
            URL для доступа к файлу
        """
        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=3600  # 1 час
            )
        except S3Error as e:
            print(f"Error generating presigned URL: {e}")
            # Возвращаем базовый URL как fallback
            return f"{self.public_url}/{self.bucket_name}/{object_name}"

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Генерирует временный presigned URL для доступа к файлу.

        Args:
            object_name: Имя объекта в хранилище
            expires: Время действия URL в секундах (по умолчанию 1 час)

        Returns:
            Временный URL для доступа к файлу
        """
        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )


# Глобальный экземпляр хранилища
storage = MinIOStorage()
