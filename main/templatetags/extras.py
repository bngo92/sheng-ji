from django import template

register = template.Library()

@register.filter
def classname(obj, arg=None):
    classname = obj.__class__.__name__
    return classname if arg is None else arg == classname
