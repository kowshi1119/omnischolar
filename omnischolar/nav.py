"""Page registry shared by app.py and the mode modules.

st.switch_page needs the StreamlitPage objects that app.py builds, so app.py
registers them here and modules navigate with go("TEST_ME") etc.
"""

import streamlit as st

PAGES: dict = {}


def go(mode: str) -> None:
    """Switch to the page registered for `mode`; no-op if it isn't registered."""
    page = PAGES.get(mode)
    if page is not None:
        st.switch_page(page)
