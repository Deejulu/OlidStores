import logging

logger = logging.getLogger(__name__)


class MediaLoggingMiddleware:
    """Middleware to log all media file access attempts"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log media file requests
        if request.path.startswith('/media/'):
            logger.info(f"Media file request: {request.path} from {request.META.get('REMOTE_ADDR')}")
        
        response = self.get_response(request)
        
        # Log response status for media files
        if request.path.startswith('/media/'):
            logger.info(f"Media file response: {request.path} -> Status {response.status_code}")
            if response.status_code == 404:
                logger.warning(f"Media file NOT FOUND: {request.path}")
            elif response.status_code >= 400:
                logger.error(f"Media file ERROR: {request.path} -> Status {response.status_code}")
        
        return response
