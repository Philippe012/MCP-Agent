def render(template: str, context: dict) -> str:
    """Replace every {{ key }} placeholder with str(context[key]).

    Whitespace around the key inside the braces is allowed and ignored
    (`{{name}}` and `{{ name }}` are equivalent). A placeholder naming a
    key not present in context is left untouched in the output - that is
    documented, intentional behavior, not a bug.
    """
    out = []
    i = 0
    n = len(template)
    while i < n:
        start = template.find("{{", i)
        if start == -1:
            out.append(template[i:])
            break
        out.append(template[i:start])
        end = template.find("}}", start)
        if end == -1:
            out.append(template[start:])
            break
        key = template[start + 2:end].strip()
        if key in context:
            out.append(str(context[key]))
        else:
            out.append(template[start:end + 2])
        i = end + 2
    return "".join(out)
