"""Render a portable compiled manuscript with trusted Live Paper claim marks."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from markupsafe import Markup, escape

COMPILED_PAPER = "manuscript-html.json"
COMPILED_SCHEMA = "scitex-live-paper.manuscript-html/v1"

_ID = re.compile(r"[\w.:-]+\Z")
_IMAGE = re.compile(r"data:image/(?:png|jpeg);base64,[A-Za-z0-9+/]+={0,2}\Z")
_HEADINGS = {f"h{level}" for level in range(1, 7)}
_VOID = {"br", "hr", "img", "col"}
_TAGS = _HEADINGS | _VOID | set("""
a abbr article b blockquote caption cite code colgroup dd del div dl dt em figcaption figure
i li ol p pre s section small span strong sub sup table tbody td th thead tr ul
math semantics annotation mrow mi mo mn mtext mfrac msqrt mroot msub msup msubsup
mover munder munderover mtable mtr mtd
""".split())
_SUPPRESS = {"script", "style", "template", "svg", "iframe", "object"}
_CLAIM = "#lp-claim-"


class _PaperHTML(HTMLParser):
    def __init__(self, marks):
        super().__init__(convert_charrefs=True)
        self.marks = marks
        self.parts = []
        self.stack = []
        self.suppressed = []
        self.headings = []
        self.heading_text = None
        self.heading_id = None
        self.heading_level = 0
        self.seen_claims = set()
        self.seen_ids = set()

    def handle_starttag(self, tag, attrs):
        if tag in _SUPPRESS:
            self.suppressed.append(tag)
        if self.suppressed or tag not in _TAGS:
            return
        attributes = dict(attrs)
        identifier = attributes.get("id") or ""
        out = []
        if _ID.fullmatch(identifier) and identifier not in self.seen_ids:
            self.seen_ids.add(identifier)
            out.append(("id", "manuscript-" + identifier))
        if tag in _HEADINGS:
            self.heading_text = []
            self.heading_id = out[0][1] if out else None
            self.heading_level = int(tag[1])
        end = f"</{tag}>"
        if tag == "a":
            href = attributes.get("href") or ""
            claim = self.marks.get(href.removeprefix(_CLAIM)) if href.startswith(_CLAIM) else None
            if claim and href not in self.seen_claims:
                self.seen_claims.add(href)
                self.parts.append(claim[0])
                self.stack.append((tag, claim[1]))
                return
            if href.startswith("#") and _ID.fullmatch(href[1:]) and not href.startswith(_CLAIM):
                out.append(("href", "#manuscript-" + href[1:]))
            elif href:
                try:
                    link = urlsplit(href)
                    if link.scheme in {"https", "http"} and link.hostname and urlsplit(href.strip()) == link:
                        out.extend((("href", href), ("target", "_blank"), ("rel", "noopener noreferrer")))
                except ValueError:
                    pass
        if tag == "img":
            source = attributes.get("src") or ""
            if not _IMAGE.fullmatch(source):
                return
            out.extend((("src", source), ("alt", attributes.get("alt") or ""), ("loading", "lazy")))
        if tag in {"td", "th"}:
            for name in ("rowspan", "colspan"):
                value = attributes.get(name) or ""
                if re.fullmatch(r"[1-9][0-9]{0,2}", value):
                    out.append((name, value))
        if tag == "math" and attributes.get("display") == "block":
            out.append(("display", "block"))
        attrs_html = "".join(f' {name}="{escape(value)}"' for name, value in out)
        self.parts.append(f"<{tag}{attrs_html}>")
        if tag not in _VOID:
            self.stack.append((tag, end))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.suppressed:
            if self.suppressed[-1] == tag:
                self.suppressed.pop()
            return
        if self.stack and self.stack[-1][0] == tag:
            self.parts.append(self.stack.pop()[1])
        if tag in _HEADINGS and self.heading_text is not None:
            title = " ".join("".join(self.heading_text).split())
            if self.heading_id and title:
                self.headings.append((self.heading_id, title, self.heading_level))
            self.heading_text = None

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(str(escape(data)))
            if self.heading_text is not None:
                self.heading_text.append(data)


def compiled_presentation(html, marks):
    parser = _PaperHTML(marks)
    parser.feed(html)
    parser.close()
    parser.parts.extend(end for _, end in reversed(parser.stack))
    return Markup("".join(parser.parts)), parser.headings
