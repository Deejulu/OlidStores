"""
Custom storage backend for Supabase Storage.
Supabase Storage is not fully S3-compatible, so we use their REST API directly.
"""
import logging
import mimetypes
from io import BytesIO
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


@deconstructible
class SupabaseStorage(Storage):
    """
    Custom Django storage backend for Supabase Storage using their REST API.
    """

    def __init__(self, **kwargs):
        self.supabase_url = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
        self.service_role_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '')
        self.bucket_name = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'media')
        
        if not self.supabase_url or not self.service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in settings"
            )
        
        self.base_url = f"{self.supabase_url}/storage/v1"
        self.public_url = f"{self.base_url}/object/public/{self.bucket_name}"
        
        # Headers for authenticated requests
        self.headers = {
            'Authorization': f'Bearer {self.service_role_key}',
            'apikey': self.service_role_key,
        }
        
        logger.info(
            f"SupabaseStorage initialized: bucket={self.bucket_name}, "
            f"base_url={self.base_url}"
        )

    def _clean_name(self, name):
        """Clean and normalize the file path."""
        # Remove leading slashes
        return name.lstrip('/')

    def _save(self, name, content):
        """
        Save file to Supabase Storage.
        """
        cleaned_name = self._clean_name(name)
        url = f"{self.base_url}/object/{self.bucket_name}/{cleaned_name}"
        
        # Get content type
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Read file content
        if hasattr(content, 'read'):
            file_content = content.read()
            if hasattr(content, 'seek'):
                content.seek(0)  # Reset file pointer
        else:
            file_content = content
        
        # Prepare headers with content type
        upload_headers = self.headers.copy()
        upload_headers['Content-Type'] = content_type
        
        logger.info(f"Uploading file to Supabase: {cleaned_name} ({content_type})")
        
        try:
            # Upload file to Supabase
            response = requests.post(
                url,
                headers=upload_headers,
                data=file_content,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully uploaded: {cleaned_name}")
                return cleaned_name
            else:
                logger.error(
                    f"Failed to upload {cleaned_name}: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                raise IOError(
                    f"Failed to upload file to Supabase: {response.status_code} - {response.text}"
                )
        except requests.RequestException as e:
            logger.error(f"Request error uploading {cleaned_name}: {str(e)}")
            raise IOError(f"Failed to upload file to Supabase: {str(e)}")

    def _open(self, name, mode='rb'):
        """
        Retrieve file from Supabase Storage.
        """
        cleaned_name = self._clean_name(name)
        url = f"{self.public_url}/{cleaned_name}"
        
        logger.debug(f"Opening file from Supabase: {cleaned_name}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                file_content = BytesIO(response.content)
                file_content.name = name
                return File(file_content)
            else:
                logger.error(
                    f"Failed to open {cleaned_name}: Status {response.status_code}"
                )
                raise IOError(f"File not found: {name}")
        except requests.RequestException as e:
            logger.error(f"Request error opening {cleaned_name}: {str(e)}")
            raise IOError(f"Failed to open file from Supabase: {str(e)}")

    def delete(self, name):
        """
        Delete file from Supabase Storage.
        """
        cleaned_name = self._clean_name(name)
        url = f"{self.base_url}/object/{self.bucket_name}/{cleaned_name}"
        
        logger.info(f"Deleting file from Supabase: {cleaned_name}")
        
        try:
            response = requests.delete(url, headers=self.headers, timeout=30)
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted: {cleaned_name}")
            else:
                logger.warning(
                    f"Failed to delete {cleaned_name}: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
        except requests.RequestException as e:
            logger.error(f"Request error deleting {cleaned_name}: {str(e)}")

    def exists(self, name):
        """
        Check if file exists in Supabase Storage.
        """
        cleaned_name = self._clean_name(name)
        url = f"{self.public_url}/{cleaned_name}"
        
        try:
            response = requests.head(url, timeout=10)
            exists = response.status_code == 200
            logger.info(f"File exists check for {cleaned_name}: status={response.status_code}, exists={exists}")
            return exists
        except requests.RequestException as e:
            logger.warning(f"File exists check failed for {cleaned_name}: {e}")
            return False

    def url(self, name):
        """
        Return the public URL for the file.
        """
        cleaned_name = self._clean_name(name)
        url = f"{self.public_url}/{cleaned_name}"
        logger.debug(f"Generated URL for {cleaned_name}: {url}")
        return url

    def size(self, name):
        """
        Return the file size.
        """
        cleaned_name = self._clean_name(name)
        url = f"{self.public_url}/{cleaned_name}"
        
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                size = int(response.headers.get('Content-Length', 0))
                logger.debug(f"File size for {cleaned_name}: {size} bytes")
                return size
        except (requests.RequestException, ValueError):
            pass
        
        logger.debug(f"Could not determine size for {cleaned_name}")
        return 0

    def get_accessed_time(self, name):
        """
        Return the last accessed time (not supported by Supabase).
        """
        return self.get_modified_time(name)

    def get_created_time(self, name):
        """
        Return the creation time (not supported by Supabase).
        """
        return self.get_modified_time(name)

    def get_modified_time(self, name):
        """
        Return the last modified time.
        """
        from django.utils import timezone
        cleaned_name = self._clean_name(name)
        url = f"{self.public_url}/{cleaned_name}"
        
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                last_modified = response.headers.get('Last-Modified')
                if last_modified:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(last_modified)
        except (requests.RequestException, ValueError):
            pass
        
        # Return current time if we can't get the actual modified time
        return timezone.now()

    def listdir(self, path):
        """
        List contents of a directory.
        Note: Supabase Storage list API requires POST with path in body.
        """
        cleaned_path = self._clean_name(path) if path else ''
        url = f"{self.base_url}/object/list/{self.bucket_name}"
        
        try:
            payload = {
                'prefix': cleaned_path,
                'limit': 1000,
            }
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                items = response.json()
                directories = []
                files = []
                
                for item in items:
                    name = item.get('name', '')
                    if item.get('id'):  # It's a file
                        files.append(name)
                    else:  # It's a folder
                        directories.append(name)
                
                logger.debug(
                    f"Listed directory {cleaned_path}: "
                    f"{len(directories)} dirs, {len(files)} files"
                )
                return directories, files
            else:
                logger.error(
                    f"Failed to list directory {cleaned_path}: "
                    f"Status {response.status_code}"
                )
        except requests.RequestException as e:
            logger.error(f"Request error listing directory {cleaned_path}: {str(e)}")
        
        return [], []
