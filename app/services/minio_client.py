import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Optional, BinaryIO
import os
import time

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
            use_ssl=use_ssl,
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3}
            )
        )
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self, max_retries=3):
        """Создать бакет если не существует с retry логикой для ошибок времени"""
        for attempt in range(max_retries):
            try:
                self.client.head_bucket(Bucket=self.bucket_name)
                print(f"[OK] MinIO bucket '{self.bucket_name}' уже существует")
                return
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')

                # Ошибка RequestTimeTooSkewed - проблема с синхронизацией времени
                if error_code == 'RequestTimeTooSkewed':
                    print(f"[WARN] RequestTimeTooSkewed (попытка {attempt + 1}/{max_retries})")
                    print(f"[WARN] Синхронизируйте системное время или проверьте настройки часового пояса")

                    if attempt < max_retries - 1:
                        # Ждём перед повторной попыткой
                        time.sleep(2)
                        continue

                # Бакет не существует - пробуем создать
                if error_code == 'NoSuchBucket':
                    try:
                        self.client.create_bucket(Bucket=self.bucket_name)
                        print(f"[OK] Created MinIO bucket: {self.bucket_name}")
                        return
                    except ClientError as create_err:
                        create_error_code = create_err.response.get('Error', {}).get('Code', '')

                        # Если проблема с временем при создании
                        if create_error_code == 'RequestTimeTooSkewed':
                            print(f"[ERROR] RequestTimeTooSkewed при создании бакета (попытка {attempt + 1}/{max_retries})")
                            if attempt < max_retries - 1:
                                time.sleep(2)
                                continue

                        print(f"[ERROR] Ошибка создания бакета {self.bucket_name}: {create_err}")
                        raise

                # Другая ошибка
                print(f"[ERROR] Ошибка проверки бакета {self.bucket_name}: {e}")
                raise
    
    def upload_file(self, file_content: bytes, file_name: str, project_id: int) -> str:
        """
        Загрузить файл в MinIO и вернуть object_key
        
        Returns:
            object_key - путь к объекту в MinIO (без префикса bucket)
        """
        # Object key начинается с project_id, без "documents/" префикса
        # Bucket имя уже добавляется в URL автоматически
        object_key = f"{project_id}/{file_name}"
        
        print(f"[INFO] Загрузка файла в MinIO:")
        print(f"  Bucket: {self.bucket_name}")
        print(f"  Object Key: {object_key}")
        print(f"  Full path in MinIO: {self.bucket_name}/{object_key}")
        print(f"  File Name: {file_name}")
        print(f"  Size: {len(file_content)} bytes")
        
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType=self._get_content_type(file_name)
            )
            
            print(f"[OK] Файл успешно загружен: {self.bucket_name}/{object_key}")
            return object_key
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            
            print(f"[ERROR] Ошибка загрузки в MinIO:")
            print(f"  Code: {error_code}")
            print(f"  Message: {error_msg}")
            print(f"  Object Key: {object_key}")
            
            if error_code == 'RequestTimeTooSkewed':
                print(f"[ERROR] Проблема с синхронизацией времени!")
                print(f"[ERROR] Синхронизируйте системное время: w32tm /resync")
            
            raise
            
        except Exception as e:
            print(f"[ERROR] Неизвестная ошибка при загрузке: {e}")
            import traceback
            traceback.print_exc()
            raise
    
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
        # Проверяем что endpoint_url корректный
        if not self.client._endpoint.host.startswith(('http://', 'https://')):
            # Принудительно устанавливаем корректный endpoint
            endpoint_url = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
            if not endpoint_url.startswith(('http://', 'https://')):
                endpoint_url = f"http://{endpoint_url}"
            self.client._endpoint.host = endpoint_url
        
        print(f"[INFO] Generating presigned URL:")
        print(f"  Endpoint: {self.client._endpoint.host}")
        print(f"  Bucket: {self.bucket_name}")
        print(f"  Object Key: {object_key}")
        
        url = self.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': object_key
            },
            ExpiresIn=expires_in
        )
        
        print(f"  Generated URL: {url[:100]}...")
        
        # Проверяем что URL корректный
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"Request URL is missing protocol. Generated: {url}")
        
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
