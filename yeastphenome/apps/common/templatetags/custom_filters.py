from django import template

register = template.Library()

@register.filter
def truncate_middle_words(value, max_words=30):
    if not isinstance(value, str):
        return value

    words = value.split()
    if len(words) <= max_words:
        return value

    half = max_words // 2
    start = words[:half]
    end = words[-half:]
    return f"{' '.join(start)} ... {' '.join(end)}"
