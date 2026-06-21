import re
from html import escape
from html.parser import HTMLParser

import markdown as md_lib

_MD_EXTENSIONS = ["tables", "nl2br", "fenced_code", "sane_lists", "attr_list"]

_ALLOWED_TAGS = frozenset({
    "p", "br", "strong", "em", "b", "i",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "hr",
    "pre", "code", "table", "thead", "tbody", "tr", "th", "td",
    "a", "span",
})
_ALLOWED_ATTRS = {
    "a":    frozenset({"href", "title", "rel"}),
    "code": frozenset({"class"}),
    "th":   frozenset({"align"}),
    "td":   frozenset({"align"}),
}
_URL_ATTRS = frozenset({"href", "src"})
_SAFE_URL  = re.compile(r"^(https?://|mailto:|/|#)", re.I)


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._out = []

    def handle_starttag(self, tag, attrs):
        if tag not in _ALLOWED_TAGS:
            return
        allowed = _ALLOWED_ATTRS.get(tag, frozenset())
        safe = []
        for name, val in attrs:
            if name not in allowed:
                continue
            if val is None:
                safe.append(name)
                continue
            if name in _URL_ATTRS and not _SAFE_URL.match(val):
                continue
            safe.append(f'{name}="{escape(val, quote=True)}"')
        attr_str = (" " + " ".join(safe)) if safe else ""
        self._out.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        if tag in _ALLOWED_TAGS:
            self._out.append(f"</{tag}>")

    def handle_data(self, data):
        self._out.append(data)

    def handle_entityref(self, name):
        self._out.append(f"&{name};")

    def handle_charref(self, name):
        self._out.append(f"&#{name};")


def render_md(text: str) -> str:
    """Converts Markdown to sanitized HTML. Returns plain string (not SafeData)."""
    if not text:
        return ""
    raw = md_lib.markdown(str(text), extensions=_MD_EXTENSIONS)
    p = _Sanitizer()
    p.feed(raw)
    return "".join(p._out)
