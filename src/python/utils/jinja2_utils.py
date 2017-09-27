"""Utilities for Jinja2."""
import os
import hashlib
import jinja2


def custom_filter(filt):
    """
    Custom filter decorator.

    Decorator to load a custom filter into Jinja2.

    Args:
        filt (function): A Jinja2 filter function.

    Returns:
        function: The filter function.
    """
    jinja2.filters.FILTERS[filt.__name__] = filt
    return filt

# ##########################################################


basename = custom_filter(os.path.basename)


@custom_filter
def filename(path):
    """
    file name from path.

    Get the name of a file without extension from a path.

    Args:
        path (str): The path

    Returns:
        str: The file name
    """
    return os.path.splitext(os.path.basename(path))[0]


@custom_filter
def gravitar_hash(email_add):
    """
    Hash an email address.

    Generate a gravitar compatible hash from an email address.

    Args:
        email_add (str): The target email address

    Returns:
        str: The hash string
    """
    return hashlib.md5(email_add.strip().lower()).hexdigest()
