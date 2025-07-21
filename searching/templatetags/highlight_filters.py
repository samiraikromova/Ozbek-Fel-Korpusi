# yourapp/templatetags/highlight_filters.py
import re
from django import template

register = template.Library()

@register.filter(is_safe=True)
def highlight(text, query):
    """Highlight exact word matches (Latin and Cyrillic)."""
    query_l = query.lower()
    # transliterate to Cyrillic on the fly
    import cyrtranslit
    query_c = cyrtranslit.to_cyrillic(query_l, 'uz')
    # wrap both Latin and Cyrillic matches
    text = re.sub(rf'(\b{re.escape(query_l)}\b)',
                  r'<span class="highlight">\1</span>',
                  text, flags=re.IGNORECASE)
    text = re.sub(rf'(\b{re.escape(query_c)}\b)',
                  r'<span class="highlight">\1</span>',
                  text, flags=re.IGNORECASE)
    return text

@register.filter(is_safe=True)
def highlight_suffix(text, query):
    """Highlight word‐parts ending in the query (suffix search)."""
    query_l = query.lower()
    import cyrtranslit
    query_c = cyrtranslit.to_cyrillic(query_l, 'uz')
    # capture word stem + suffix
    pattern = rf'(\w*({re.escape(query_l)}|{re.escape(query_c)})\b)'
    return re.sub(pattern,
                  r'<span class="highlight">\1</span>',
                  text, flags=re.IGNORECASE)
