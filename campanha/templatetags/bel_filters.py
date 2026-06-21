from django import template
from django.utils.safestring import mark_safe

from campanha.markup import render_md

register = template.Library()


@register.filter(is_safe=True)
def md(value):
    return mark_safe(render_md(value))
