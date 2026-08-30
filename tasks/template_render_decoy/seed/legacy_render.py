"""Superseded by render.render() - kept around for reference, not imported
anywhere in this application.

TODO: this old implementation has a known issue with whitespace inside
{{ placeholders }} (e.g. "{{ name }}" doesn't substitute) - never got
around to fixing it here before render.py replaced it.
"""


def render_legacy(template: str, context: dict) -> str:
    result = template
    for key, value in context.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result
