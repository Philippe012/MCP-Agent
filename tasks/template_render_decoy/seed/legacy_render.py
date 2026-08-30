
def render_legacy(template: str, context: dict) -> str:
    result = template
    for key, value in context.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result
