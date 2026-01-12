from django import template

register = template.Library()

@register.filter(name='split')
def split_string(value, delimiter=','):
    """Split a string by delimiter and return list"""
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter)]

@register.filter(name='contains')
def contains_string(value, substring):
    """Check if string contains substring"""
    return substring in str(value)



from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divisibleby(value, arg):
    """Check if value is divisible by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

from django import template

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter and return list"""
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter)]