from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Allow dict lookup by variable key in templates: {{ mydict|get_item:variable }}"""
    if dictionary is None:
        return None
    return dictionary.get(key)
