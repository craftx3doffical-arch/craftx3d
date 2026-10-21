from django import template

register = template.Library()


@register.filter
def round_int(value):
    """Round a numeric rating to the nearest whole star for template
    comparisons (e.g. {% if forloop.counter <= product.avg_rating|round_int %})."""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0
