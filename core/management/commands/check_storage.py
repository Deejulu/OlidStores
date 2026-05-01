from django.core.management.base import BaseCommand
from django.conf import settings
import logging
import os


class Command(BaseCommand):
    help = 'Run storage checks (S3/Supabase or local MEDIA_ROOT) and print/log results'

    def handle(self, *args, **options):
        logger = logging.getLogger('django.storage_check')
        self.stdout.write('Running storage checks...')
        logger.info('Manual storage check invoked')

        storage_backend = getattr(settings, 'DEFAULT_FILE_STORAGE', '') or ''
        self.stdout.write(f'DEFAULT_FILE_STORAGE={storage_backend}')
        self.stdout.write(f'MEDIA_URL={getattr(settings, "MEDIA_URL", None)}')

        if 's3boto3' in storage_backend.lower():
            try:
                import boto3
                from botocore.exceptions import ClientError

                endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
                aws_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
                aws_secret = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
                bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)

                self.stdout.write(f'Checking S3-compatible bucket: {bucket} (endpoint={endpoint})')
                client = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)

                try:
                    client.head_bucket(Bucket=bucket)
                    self.stdout.write(f'head_bucket succeeded for {bucket}')
                    logger.info('head_bucket succeeded for %s', bucket)
                except ClientError as e:
                    self.stderr.write(f'head_bucket failed: {e}')
                    logger.error('head_bucket failed: %s', e)

                try:
                    resp = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
                    key_count = resp.get('KeyCount', 0)
                    self.stdout.write(f'list_objects_v2 KeyCount={key_count}')
                    logger.info('list_objects_v2 KeyCount=%s', key_count)
                    if key_count > 0:
                        key = resp['Contents'][0]['Key']
                        self.stdout.write(f'Found object sample key={key}')
                        try:
                            client.head_object(Bucket=bucket, Key=key)
                            self.stdout.write(f'head_object succeeded for {key}')
                            logger.info('head_object succeeded for %s', key)
                        except ClientError as e:
                            self.stderr.write(f'head_object failed for {key}: {e}')
                            logger.error('head_object failed for %s: %s', key, e)
                except ClientError as e:
                    self.stderr.write(f'list_objects_v2 failed: {e}')
                    logger.error('list_objects_v2 failed: %s', e)
            except Exception as exc:
                self.stderr.write(f'Error during S3 storage check: {exc}')
                logger.exception('Error during S3 storage check: %s', exc)
        else:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            self.stdout.write(f'Checking local MEDIA_ROOT={media_root}')
            try:
                if media_root and os.path.exists(media_root):
                    files = os.listdir(media_root)[:20]
                    self.stdout.write('MEDIA_ROOT exists; sample files:')
                    for f in files:
                        self.stdout.write('  ' + f)
                    logger.info('MEDIA_ROOT exists; sample files=%s', files)
                else:
                    self.stderr.write(f'MEDIA_ROOT missing or not set: {media_root}')
                    logger.warning('MEDIA_ROOT missing or not set: %s', media_root)
            except Exception as exc:
                self.stderr.write(f'Filesystem media check failed: {exc}')
                logger.exception('Filesystem media check failed: %s', exc)
