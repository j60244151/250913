# streamlit_app.py
import os
import io
import json
import re
import urllib.request
from typing import Dict, Tuple, Optional

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="MBTI × Climate Map",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ MBTI 유형 × 기후(위도) 상관 시각화")
st.caption("같은 폴더의 CSV를 기본으로 읽고, 없으면 업로드로 대체 · Altair 인터랙티브 월드맵 · 별도 라이브러리 설치 불필요")

# -----------------------------
# Constants
# -----------------------------
MBTI_TYPES = [
    "INTJ","INTP","ENTJ","ENTP",
    "INFJ","INFP","ENFJ","ENFP",
    "ISTJ","ISFJ","ESTJ","ESFJ",
    "ISTP","ISFP","ESTP","ESFP"
]
LOCAL_DATA_PATH = "countriesMBTI_16types.csv"

WORLD_TOPOJSON_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
# Columns: CountryName, CapitalName, CapitalLatitude, CapitalLongitude, ContinentName, ...
CAPITALS_CSV_URL = "https://raw.githubusercontent.com/icyrockcom/country-capitals/master/data/country-list.csv"

NAME_FIX: Dict[str, str] = {
    "united states": "united states of america",
    "usa": "united states of america",
    "u s a": "united states of america",
    "russia": "russian federation",
    "south korea": "korea republic of",
    "north korea": "korea democratic people s republic of",
    "czech": "czechia",
    "czech republic": "czechia",
    "swaziland": "eswatini",
    "cape verde": "cabo verde",
    "laos": "lao people s democratic republic",
    "moldova": "moldova republic of",
    "ivory coast": "cote d ivoire",
    "brunei darussalam": "brunei",
    "vatican": "holy see",
}

# -----------------------------
# Utils
# -----------------------------
def norm_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def fix_name_for_join(s: str) -> str:
    s0 = norm_name(s)
    return NAME_FIX.get(s0, s0)

@st.cache_data(show_spinner=False)
def robust_read_csv(source) -> pd.DataFrame:
    """Try multiple encodings for path/UploadedFile/URL."""
    if isinstance(source, str) and os.path.exists(source):
        return pd.read_csv(source)
    if hasattr(source, "read"):  # Streamlit UploadedFile
        raw = source.read()
        for enc in ("utf-8","utf-8-sig","cp949","euc-kr","latin-1"):
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=enc)
            except Exception:
                pass
        return pd.read_csv(io.BytesIO(raw), engine="python")
    return pd.read_csv(source)

@st.cache_data(show_spinner=False)
def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

@st.cache_data(show_spinner=False)
def fetch_csv(url: str) -> pd.DataFrame:
    return pd.read_csv(url)

def auto_detect_country_col(df: pd.DataFrame) -> Optional[str]:
    for cand in ["Country","country","국가","국가명","Nation","Region","Country/Region"]:
        if cand in df.columns:
            return cand
    # fallback: 첫 번째 비수치형 열
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            return c
    return None

def to_wide_by_country(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    CSV를 국가별 가로형 테이블로 변환하고,
    탐지한 국가 열을 항상 'Country'로 강제 통일하여 반환한다.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 1) 국가 열 탐지 + 'Country'로 강
