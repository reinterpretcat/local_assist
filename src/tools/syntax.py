from __future__ import annotations

default_syntax_scheme = {
  "general": {
    "comment": "#a6acb9",
    "error": "#f9ae58",
    "escape": "#d8dee9",
    "keyword": "#c695c6",
    "name": "#f9ae58",
    "string": "#99c794",
    "punctuation": "#5fb4b4"
  },
  "keyword": {
    "constant": "#c695c6",
    "declaration": "#c695c6",
    "namespace": "#c695c6",
    "pseudo": "#c695c6",
    "reserved": "#c695c6",
    "type": "#c695c6"
  },
  "name": {
    "attr": "#c695c6",
    "builtin": "#6699cc",
    "builtin_pseudo": "#ec5f66",
    "class": "#f9ae58",
    "class_variable": "#d8dee9",
    "constant": "#d8dee9",
    "decorator": "#6699cc",
    "entity": "#6699cc",
    "exception": "#6699cc",
    "function": "#5fb4b4",
    "global_variable": "#d8dee9",
    "instance_variable": "#d8dee9",
    "label": "#6699cc",
    "magic_function": "#6699cc",
    "magic_variable": "#d8dee9",
    "namespace": "#d8dee9",
    "tag": "#f97b58",
    "variable": "#5fb4b4"
  },
  "operator": {
    "symbol": "#f97b58",
    "word": "#f97b58"
  },
  "string": {
    "affix": "#99c794",
    "char": "#99c794",
    "delimeter": "#99c794",
    "doc": "#99c794",
    "double": "#99c794",
    "escape": "#99c794",
    "heredoc": "#99c794",
    "interpol": "#99c794",
    "regex": "#99c794",
    "single": "#99c794",
    "symbol": "#99c794"
  },
  "number": {
    "binary": "#f9ae58",
    "float": "#f9ae58",
    "hex": "#f9ae58",
    "integer": "#f9ae58",
    "long": "#f9ae58",
    "octal": "#f9ae58"
  },
  "comment": {
    "hashbang": "#a6acb9",
    "multiline": "#a6acb9",
    "preproc": "#c695c6",
    "preprocfile": "#99c794",
    "single": "#a6acb9",
    "special": "#a6acb9"
  }
}


_editor_keys_map = {
    "background": "bg",
    "foreground": "fg",
    "selectbackground": "select_bg",
    "selectforeground": "select_fg",
    "inactiveselectbackground": "inactive_select_bg",
    "insertbackground": "caret",
    "insertwidth": "caret_width",
    "borderwidth": "border_width",
    "highlightthickness": "focus_border_width",
}

_extras = {
    "Error": "error",
    "Literal.Date": "date",
}

_keywords = {
    "Keyword.Constant": "constant",
    "Keyword.Declaration": "declaration",
    "Keyword.Namespace": "namespace",
    "Keyword.Pseudo": "pseudo",
    "Keyword.Reserved": "reserved",
    "Keyword.Type": "type",
}

_names = {
    "Name.Attribute": "attr",
    "Name.Builtin": "builtin",
    "Name.Builtin.Pseudo": "builtin_pseudo",
    "Name.Class": "class",
    "Name.Constant": "constant",
    "Name.Decorator": "decorator",
    "Name.Entity": "entity",
    "Name.Exception": "exception",
    "Name.Function": "function",
    "Name.Function.Magic": "magic_function",
    "Name.Label": "label",
    "Name.Namespace": "namespace",
    "Name.Tag": "tag",
    "Name.Variable": "variable",
    "Name.Variable.Class": "class_variable",
    "Name.Variable.Global": "global_variable",
    "Name.Variable.Instance": "instance_variable",
    "Name.Variable.Magic": "magic_variable",
}

_strings = {
    "Literal.String.Affix": "affix",
    "Literal.String.Backtick": "backtick",
    "Literal.String.Char": "char",
    "Literal.String.Delimeter": "delimeter",
    "Literal.String.Doc": "doc",
    "Literal.String.Double": "double",
    "Literal.String.Escape": "escape",
    "Literal.String.Heredoc": "heredoc",
    "Literal.String.Interpol": "interpol",
    "Literal.String.Regex": "regex",
    "Literal.String.Single": "single",
    "Literal.String.Symbol": "symbol",
}

_numbers = {
    "Literal.Number.Bin": "binary",
    "Literal.Number.Float": "float",
    "Literal.Number.Hex": "hex",
    "Literal.Number.Integer": "integer",
    "Literal.Number.Integer.Long": "long",
    "Literal.Number.Oct": "octal",
}

_comments = {
    "Comment.Hashbang": "hashbang",
    "Comment.Multiline": "multiline",
    "Comment.Preproc": "preproc",
    "Comment.PreprocFile": "preprocfile",
    "Comment.Single": "single",
    "Comment.Special": "special",
}

_generic = {
    "Generic.Emph": "emphasis",
    "Generic.Error": "error",
    "Generic.Heading": "heading",
    "Generic.Strong": "strong",
    "Generic.Subheading": "subheading",
}


def parse_table(
    source: dict[str, str | int] | None,
    map_: dict[str, str],
    fallback: str | int | None = None,
) -> dict[str, str | int | None]:
    result: dict[str, str | int | None] = {}

    if source is not None:
        for token, key in map_.items():
            value = source.get(key)
            if value is None:
                value = fallback
            result[token] = value
    elif fallback is not None:
        for token in map_:
            result[token] = fallback

    return result


def parse_scheme(color_scheme: dict[str, dict[str, str | int]]) -> dict:
    assert "general" in color_scheme, "General table must present in color scheme"
    general = color_scheme["general"]

    error = general.get("error")
    escape = general.get("escape")
    punctuation = general.get("punctuation")
    general_comment = general.get("comment")
    general_keyword = general.get("keyword")
    general_name = general.get("name")
    general_string = general.get("string")

    tags = {
        "Error": error,
        "Escape": escape,
        "Punctuation": punctuation,
        "Comment": general_comment,
        "Keyword": general_keyword,
        "Keyword.Other": general_keyword,
        "Literal.String": general_string,
        "Literal.String.Other": general_string,
        "Name.Other": general_name,
    }

    tags.update(**parse_table(color_scheme.get("keyword"), _keywords, general_keyword))
    tags.update(**parse_table(color_scheme.get("name"), _names, general_name))
    tags.update(
        **parse_table(
            color_scheme.get("operator"),
            {"Operator": "symbol", "Operator.Word": "word"},
        )
    )
    tags.update(**parse_table(color_scheme.get("string"), _strings, general_string))
    tags.update(**parse_table(color_scheme.get("number"), _numbers))
    tags.update(**parse_table(color_scheme.get("comment"), _comments, general_comment))
    tags.update(**parse_table(color_scheme.get("generic"), _generic))
    tags.update(**parse_table(color_scheme.get("extras"), _extras))

    return tags
