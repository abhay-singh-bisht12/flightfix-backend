"""
Pagination classes for FlightFix Aircraft and Equipment APIs.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for aircraft and equipment listings:
    Default 10 items per page; client can customize with ?page_size= (max 100).
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
