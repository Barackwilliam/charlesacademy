from django import template

register = template.Library()

@register.filter
def divide(value, divisor):
    try:
        if divisor == 0:
            return 0
        return value / divisor
    except (ValueError, TypeError):
        return 0