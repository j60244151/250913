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
st.set_page_config(page_title="MBTI × Climate Map", page_icon="🗺️", layout="wide")
st.title("🗺️ MBTI 유형 × 기후(위도) 상관 시각화")
st.caption("같은 폴더 CSV 우선 사용 · 없으면 업로드 · Altair 인터랙티브 월드맵(추가 설치 불필요)")

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

WORLD_TOPOJSON_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries
