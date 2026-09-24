"""Presentation-only translation; source values, identifiers and saved records stay intact."""
import csv
import io
import re
from html import escape
from html.parser import HTMLParser
from functools import wraps
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as native

EN = json.loads(Path(__file__).with_name("en.json").read_text())
_PHRASES = re.compile("|".join(re.escape(k) for k in sorted(EN, key=len, reverse=True)))


def english():
    return native.session_state.get("language", "中文") == "English"


def tr(value):
    if not english() or not isinstance(value, str):
        return value
    if value in EN:
        return EN[value]
    # Dates are rendered from observation periods, never from the UI locale's timezone.
    value = re.sub(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", lambda m: f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}", value)
    value = re.sub(r"(\d{4})\s*年\s*(\d{1,2})\s*月", lambda m: f"{m[1]}-{int(m[2]):02d}", value)
    value = re.sub(r"(\d{4})年", r"\1", value)
    return _PHRASES.sub(lambda m: EN[m[0]], value)


def frame(data):
    if not english() or not isinstance(data, pd.DataFrame):
        return data
    result = data.copy()
    # Raw provenance references remain verbatim for locating the original source.
    for column in result:
        if column not in ("来源文件", "来源表", "单元格", "source_file", "sheet", "cell"):
            result[column] = result[column].map(tr)
    return result.rename(columns=tr)


def chart_spec(value):
    # Translate field names AND the inline data keys together so encodings still resolve.
    if isinstance(value, dict):
        return {tr(k): chart_spec(v) for k, v in value.items()}
    if isinstance(value, list):
        return [chart_spec(v) for v in value]
    return tr(value)


class _HTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = [(k, tr(v) if k in ("aria-label", "title") else v) for k, v in attrs]
        self.parts.append("<" + tag + "".join(f' {k}="{escape(v, quote=True)}"' if v is not None else f" {k}" for k, v in attrs) + ">")

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")

    def handle_data(self, text):
        self.parts.append(escape(tr(text)))


class LocalizedUI:
    """Small boundary adapter for the Streamlit calls used by this dashboard.

    Internal Chinese option values remain stable. Only their rendered labels change.
    Widget selections are remembered separately because Streamlit may recreate widgets
    when a translated label or formatted option changes.
    """
    TEXT = {"title", "header", "subheader", "caption", "write", "markdown", "info", "warning", "success", "expander", "popover", "button", "metric"}

    def __getattr__(self, name):
        target = getattr(native, name)
        if name not in self.TEXT | {"radio", "selectbox", "number_input", "dataframe", "download_button", "html", "altair_chart", "set_page_config"}:
            return target

        @wraps(target)
        def render(*args, **kwargs):
            args = list(args)
            if name in ("radio", "selectbox", "number_input"):
                original_label = args[0] if args else kwargs["label"]
                key = kwargs.setdefault("key", "ui-" + original_label)
                remembered = native.session_state.setdefault("ui-selections", {})
                selected = native.session_state.get(key, remembered.get(key))
                if name != "number_input":
                    options = list(args[1] if len(args) > 1 else kwargs["options"])
                    formatter = kwargs.get("format_func", str)
                    rendered = {v: tr(formatter(v)) for v in options}
                    kwargs["format_func"] = rendered.get
                    if selected in options:
                        kwargs["index"] = options.index(selected)
                elif selected is not None:
                    # One authority for restored inputs; avoid a default/session-state warning.
                    native.session_state[key] = selected
                    kwargs["value"] = None
                if args:
                    args[0] = tr(original_label)
                else:
                    kwargs["label"] = tr(original_label)
                result = target(*args, **kwargs)
                remembered[key] = result
                return result
            if name in self.TEXT:
                args = [tr(v) for v in args]
                kwargs = {k: tr(v) if k in ("label", "body", "help", "delta") else v for k, v in kwargs.items()}
            elif name == "set_page_config":
                kwargs["page_title"] = tr(kwargs.get("page_title", "GTA Housing Monitor"))
            elif name == "dataframe":
                args[0] = frame(args[0])
                if "column_config" in kwargs:
                    kwargs["column_config"] = {tr(k): v for k, v in kwargs["column_config"].items()}
            elif name == "altair_chart" and english():
                # Use the same Arrow/DataFrame rendering path as Chinese charts.
                # A raw Vega spec can retain rows in the Python protobuf yet lose
                # the named dataset in the browser. Rebind the translated rows
                # before Streamlit installs its own Altair data transformer.
                chart = args[0].copy(deep=True)
                data = frame(chart.data)
                chart.data = alt.InlineData(values=[])
                spec = chart_spec(chart.to_dict())
                spec.pop("datasets", None)
                spec["data"] = {"values": []}
                localized = alt.Chart.from_dict(spec)
                localized.data = data
                return native.altair_chart(localized, **kwargs)
            elif name == "html" and english() and not args[0].lstrip().startswith("<style>"):
                parser = _HTML()
                parser.feed(args[0])
                args[0] = "".join(parser.parts)
            elif name == "download_button":
                args[0] = tr(args[0])
                if english() and len(args) > 3 and args[3] == "text/csv":
                    original = args[1].decode("utf-8-sig") if isinstance(args[1], bytes) else args[1]
                    rows = list(csv.reader(io.StringIO(original)))
                    out = io.StringIO()
                    writer = csv.writer(out)
                    protected = {i for i, header in enumerate(rows[0]) if header in ("来源文件", "来源表", "单元格", "source_file", "sheet", "cell")}
                    writer.writerow([tr(v) for v in rows[0]])
                    writer.writerows([[v if i in protected else tr(v) for i, v in enumerate(row)] for row in rows[1:]])
                    args[1] = out.getvalue().encode("utf-8-sig")
            return target(*args, **kwargs)
        return render


st = LocalizedUI()
