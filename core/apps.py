import os
import logging

from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
	name = 'core'
	verbose_name = 'Core'

	def ready(self):
		"""Optional storage checks run at startup when CHECK_STORAGE_ON_STARTUP=true.

		This logs storage backend info and attempts to verify access to the
		configured bucket (S3/Supabase) or the local `MEDIA_ROOT`. Only enable
		temporarily in production to diagnose media issues.
		"""
		do_check = os.environ.get('CHECK_STORAGE_ON_STARTUP', '').lower() in ('1', 'true', 'yes')
		if not do_check:
			return

		logger = logging.getLogger('django.storage_check')
		logger.info('Running startup storage checks')
		logger.info('DEFAULT_FILE_STORAGE=%s MEDIA_URL=%s', getattr(settings, 'DEFAULT_FILE_STORAGE', None), getattr(settings, 'MEDIA_URL', None))

		storage_backend = getattr(settings, 'DEFAULT_FILE_STORAGE', '') or ''
		if 's3boto3' in storage_backend.lower():
			try:
				import boto3
				from botocore.exceptions import ClientError, NoCredentialsError

				endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
				aws_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
				aws_secret = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
				bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)

				logger.info('Checking S3-compatible bucket: %s (endpoint=%s)', bucket, endpoint)
				client = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)

				try:
					client.head_bucket(Bucket=bucket)
					logger.info('head_bucket succeeded for %s', bucket)
				except ClientError as e:
					logger.error('head_bucket failed: %s', e)

				try:
					resp = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
					key_count = resp.get('KeyCount', 0)
					logger.info('list_objects_v2 KeyCount=%s', key_count)
					if key_count > 0:
						key = resp['Contents'][0]['Key']
						logger.info('Found object sample key=%s', key)
						try:
							client.head_object(Bucket=bucket, Key=key)
							logger.info('head_object succeeded for %s', key)
						except ClientError as e:
							logger.error('head_object failed for %s: %s', key, e)
				except ClientError as e:
					logger.error('list_objects_v2 failed: %s', e)
			except Exception as exc:  # broad catch so startup still completes
				logger.exception('Error during S3 storage check: %s', exc)
		else:
			# Local filesystem check
			media_root = getattr(settings, 'MEDIA_ROOT', None)
			logger.info('Checking local MEDIA_ROOT=%s', media_root)
			try:
				if media_root and os.path.exists(media_root):
					files = os.listdir(media_root)[:10]
					logger.info('MEDIA_ROOT exists; sample files=%s', files)
				else:
					logger.warning('MEDIA_ROOT missing or not set: %s', media_root)
			except Exception as exc:
				logger.exception('Filesystem media check failed: %s', exc)

