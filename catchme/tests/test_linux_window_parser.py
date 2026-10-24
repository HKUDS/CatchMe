from __future__ import annotations

from catchme.recorders.platform.linux import _parse_name_or_title


def test_parse_name_or_title_decodes_xprop_string_escapes():
    xprop_output = r'WM_NAME(STRING) = "Editor: \"draft\\final\""'

    assert _parse_name_or_title(xprop_output) == 'Editor: "draft\\final"'
