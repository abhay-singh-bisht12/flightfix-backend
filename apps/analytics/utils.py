"""
Utility functions for FlightFix Analytics & Reporting module.
"""

from datetime import datetime
from rest_framework.exceptions import ValidationError


def parse_date_range(request):
    """
    Parses and validates optional 'start_date' and 'end_date' query parameters.
    Format must be ISO standard YYYY-MM-DD.
    Validates that start_date <= end_date.

    Returns:
        tuple (start_date, end_date) as datetime.date objects or (None, None).

    Raises:
        ValidationError: If format is invalid or start_date > end_date.
    """
    start_str = request.query_params.get('start_date')
    end_str = request.query_params.get('end_date')

    start_date = None
    end_date = None

    if start_str is not None:
        start_str = start_str.strip()
        if start_str:
            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({
                    'start_date': "Invalid date format for 'start_date'. Expected YYYY-MM-DD."
                })

    if end_str is not None:
        end_str = end_str.strip()
        if end_str:
            try:
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({
                    'end_date': "Invalid date format for 'end_date'. Expected YYYY-MM-DD."
                })

    if start_date and end_date and start_date > end_date:
        raise ValidationError({
            'start_date': "start_date cannot be after end_date."
        })

    return start_date, end_date
