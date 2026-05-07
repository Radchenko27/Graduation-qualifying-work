import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import os

class MinIOClient:
    """Клиент для работы с MinIO (S3-совместимое хранилище)"""
    
    def __init__(self):
        endpoint_url = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        
        # Добавляем протокол если отсутствует
        if not endpoint_url.startswith(('http://', 'https://')):
            endpoint_url = f"http://{endpoint_url}"
        
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin_password")
        bucket_name = os.getenv("MINIO_BUCKET", "documents")
        use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        
        # Если включён SSL, меняем протокол
        if use_ssl and not endpoint_url.startswith('https://'):
            endpoint_url = endpoint_url.replace('http://', 'https://')
        
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            use_ssl=use_ssl
        )
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Создать бакет если не существует"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            print(f"[OK] MinIO bucket '{self.bucket_name}' уже существует")
        except ClientError as e:
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                print(f"[OK] Created MinIO bucket: {self.bucket_name}")
            except ClientError as create_err:
                print(f"[ERROR] Ошибка создания бакета {self.bucket_name}: {create_err}")
                raise
    
    def upload_file(self, file_content: bytes, file_name: str, project_id: int) -> str:
        """
        Загрузить файл в MinIO и вернуть object_key
        
        Returns:
            object_key - путь к объекту в MinIO
        """
        object_key = f"documents/{project_id}/{file_name}"
        
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=self._get_content_type(file_name)
        )
        
        return object_key
    
    def upload_file_obj(self, file_obj: BinaryIO, file_name: str, project_id: int) -> str:
        """
        Загрузить файл из file-like объекта
        
        Returns:
            object_key - путь к объекту в MinIO
        """
        file_content = file_obj.read()
        return self.upload_file(file_content, file_name, project_id)
    
    def download_file(self, object_key: str) -> bytes:
        """Скачать файл из MinIO"""
        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=object_key
        )
        return response['Body'].read()
    
    def download_file_obj(self, object_key: str):
        """Скачать файл из MinIO в виде file-like объекта"""
        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=object_key
        )
        return response['Body']
    
    def delete_file(self, object_key: str):
        """Удалить файл из MinIO"""
        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=object_key
        )
    
    def file_exists(self, object_key: str) -> bool:
        """Проверить существует ли файл"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False
    
    def get_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        Получить presigned URL для скачивания файла
        
        Args:
            object_key: путь к объекту в MinIO
            expires_in: время жизни URL в секундах (по умолчанию 1 час)
        
        Returns:
            presigned URL
        """
        url = self.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': object_key
            },
            ExpiresIn=expires_in
        )
        return url
    
    @staticmethod
    def _get_content_type(file_name: str) -> str:
        """Определить MIME тип файла по расширению"""
        ext = file_name.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'txt': 'text/plain',
        }
        return content_types.get(ext, 'application/octet-stream')


# Singleton
minio_client = MinIOClient()
