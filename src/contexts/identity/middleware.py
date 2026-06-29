from django.utils.cache import add_never_cache_headers

class NoCacheAuthenticatedMiddleware:
    """
    Middleware to add 'Cache-Control: no-cache, no-store, must-revalidate'
    and 'Pragma: no-cache' headers to all responses where the user is authenticated.
    This prevents browsers from caching authenticated pages, ensuring that hitting the 
    'Back' button after logging out does not display protected content.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # If the user is authenticated, we never want the browser to cache the response.
        # This protects authenticated routes from being stored in the browser's history cache.
        if hasattr(request, 'user') and request.user.is_authenticated:
            add_never_cache_headers(response)

        return response
