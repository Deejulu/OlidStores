"""
Middleware to enforce verification for existing users.
"""
from django.shortcuts import redirect
from django.urls import reverse


class VerificationMiddleware:
    """
    Middleware that redirects unverified users to the verification page.
    Only affects authenticated customer users trying to access protected pages.
    """
    
    # URLs that don't require verification
    EXEMPT_URLS = [
        '/users/verify/',
        '/users/send-',
        '/users/login/',
        '/users/logout/',
        '/users/signup/',
        '/users/password',
        '/admin/',
        '/static/',
        '/media/',
        '/__debug__/',
    ]
    
    # URLs that customers can access without verification (public pages)
    PUBLIC_URLS = [
        '/',
        '/products/',
        '/categories/',
        '/search/',
        '/contact/',
        '/about/',
        '/faq/',
        '/privacy/',
        '/terms/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only check authenticated users
        if request.user.is_authenticated:
            user = request.user
            path = request.path
            
            # Skip for admin users - they're auto-verified
            if getattr(user, 'role', None) == 'admin':
                if not user.email_verified or not user.phone_verified:
                    user.email_verified = True
                    user.phone_verified = True
                    user.save(update_fields=['email_verified', 'phone_verified'])
            
            # Only check customer users
            elif getattr(user, 'role', None) == 'customer':
                # Check if user needs verification
                if hasattr(user, 'needs_verification') and user.needs_verification:
                    # Check if accessing exempt URL
                    is_exempt = any(path.startswith(url) for url in self.EXEMPT_URLS)
                    is_public = any(path.startswith(url) or path == url for url in self.PUBLIC_URLS)
                    
                    # AJAX requests should pass through
                    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    
                    if not is_exempt and not is_public and not is_ajax:
                        # Redirect to verification page
                        return redirect('users:verify_existing_user')
        
        response = self.get_response(request)
        
        # Add cache headers to prevent back button issues
        # Only for HTML pages, not static files
        if not request.path.startswith(('/static/', '/media/')):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
