# In a new file templatetags/custom_filters.py
from django import template
import cyrtranslit

register = template.Library()

@register.filter
def replace(value, arg):
    if len(arg.split('|')) != 2:
        return value
    search, replacement = arg.split('|')
    return value.replace(search, replacement)

def get_item(dictionary, key):
    return dictionary.get(key, 0)


@register.filter(name='cyrillic')
def to_cyrillic(value):
    """Convert Latin text to Cyrillic"""
    try:
        return cyrtranslit.to_cyrillic(value, 'uz')
    except:
        return value

@register.filter(name='latin')
def to_latin(value):
    """Convert Cyrillic text to Latin"""
    try:
        return cyrtranslit.to_latin(value, 'uz')
    except:
        return value