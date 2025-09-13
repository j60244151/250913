# streamlit_app.py

def to_wide_by_country(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 1) 국가 열 탐지
    def auto_detect_country_col(df_):
        for cand in ["Country","country","국가","국가명","Nation","Region","Country/Region"]:
            if cand in df_.columns:
                return cand
        for c in df_.columns:  # fallback: 첫 번째 문자열 열
            if not pd.api.types.is_numeric_dtype(df_[c]):
                return c
        return None

    country_col = auto_detect_country_col(df)
    if not country_col:
        raise ValueError("국가 열을 찾지 못했습니다. (예: Country)")

    # ✅ 2) 탐지한 국가 열을 'Country'로 강제 통일
    if country_col != "Country":
        df = df.rename(columns={country_col: "Country"})
    country_col = "Country"

    # 3) MBTI 열 찾기
    MBTI_TYPES = [
        "INTJ","INTP","ENTJ","ENTP",
        "INFJ","INFP","ENFJ","ENFP",
        "ISTJ","ISFJ","ESTJ","ESFJ",
        "ISTP","ISFP","ESTP","ESFP"
    ]
    up_map = {c: c.upper().strip() for c in df.columns}
    mbti_cols_present = [orig for orig, up in up_map.items() if up in MBTI_TYPES]

    # 4) 가로형 처리
    if len(mbti_cols_present) >= 4:
        wide = df[[country_col] + mbti_cols_present].copy()
        # MBTI 열만 대문자로 통일
        rename_map = {c: up_map[c] for c in mbti_cols_present}
        wide = wide.rename(columns=rename_map)
        # 16개 모두 보장
        for t in MBTI_TYPES:
            if t not in wide.columns:
                wide[t] = np.nan
        for t in MBTI_TYPES:
            wide[t] = pd.to_numeric(wide[t], errors="coerce")
        wide = wide[[country_col] + MBTI_TYPES]
        return wide, country_col

    # 5) 세로형 처리
    lower = {c.lower(): c for c in df.columns}
    type_col = next((lower[c] for c in ["type","mbti","mbti_type","유형"] if c in lower), None)
    value_col = next((lower[c] for c in ["value","percent","percentage","ratio","비율","퍼센트","값"] if c in lower), None)
    if type_col and value_col:
        long = df[[country_col, type_col, value_col]].copy()
        long.columns = [country_col, "Type", "Value"]
        long["Type"] = long["Type"].astype(str).str.upper().str.strip()
        long = long[long["Type"].isin(MBTI_TYPES)]
        long["Value"] = pd.to_numeric(long["Value"], errors="coerce")
        wide = long.pivot_table(index=country_col, columns="Type", values="Value", aggfunc="mean").reset_index()
        for t in MBTI_TYPES:
            if t not in wide.columns:
                wide[t] = np.nan
        wide = wide[[country_col] + MBTI_TYPES]
        return wide, country_col

    raise ValueError("MBTI 16개 열(가로형) 또는 (Type, Value) 구성(세로형)을 찾지 못했습니다.")



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

# World topojson & capitals dataset (public)
WORLD_TOPOJSON_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
# Columns: CountryName, CapitalName, CapitalLatitude, CapitalLongitude, ContinentName, TwoLetterCountryCode, ThreeLetterCountryCode, CountryNumber
CAPITALS_CSV_URL = "https://raw.githubusercontent.com/icyrockcom/country-capitals/master/data/country-list.csv"

# Name normalization map for joins
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
# Utilities
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
    """Try multiple encodings for path or UploadedFile."""
    if isinstance(source, str) and os.path.exists(source):
        return pd.read_csv(source)
    if hasattr(source, "read"):  # UploadedFile
        raw = source.read()
        for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=enc)
            except Exception:
                pass
        return pd.read_csv(io.BytesIO(raw), engine="python")
    # If it's a URL-like str
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
    for c in df.columns:  # fallback: first non-numeric
        if not pd.api.types.is_numeric_dtype(df[c]):
            return c
    return None

def to_wide_by_country(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    country_col = auto_detect_country_col(df)
    if not country_col:
        raise ValueError("국가 열을 찾지 못했습니다. (예: Country)")

    up_map = {c: c.upper().strip() for c in df.columns}
    mbti_cols_present = [orig for orig, up in up_map.items() if up in MBTI_TYPES]

    if len(mbti_cols_present) >= 4:
        wide = df[[country_col] + mbti_cols_present].copy()
        wide = wide.rename(columns=up_map)
        for t in MBTI_TYPES:
            if t not in wide.columns:
                wide[t] = np.nan
        for t in MBTI_TYPES:
            wide[t] = pd.to_numeric(wide[t], errors="coerce")
        wide = wide[[country_col] + MBTI_TYPES]
        return wide, country_col

    # Long format support
    lower = {c.lower(): c for c in df.columns}
    type_col = next((lower[c] for c in ["type","mbti","mbti_type","유형"] if c in lower), None)
    value_col = next((lower[c] for c in ["value","percent","percentage","ratio","비율","퍼센트","값"] if c in lower), None)
    if type_col and value_col:
        long = df[[country_col, type_col, value_col]].copy()
        long.columns = [country_col, "Type", "Value"]
        long["Type"] = long["Type"].astype(str).str.upper().str.strip()
        long = long[long["Type"].isin(MBTI_TYPES)]
        long["Value"] = pd.to_numeric(long["Value"], errors="coerce")
        wide = long.pivot_table(index=country_col, columns="Type", values="Value", aggfunc="mean").reset_index()
        for t in MBTI_TYPES:
            if t not in wide.columns:
                wide[t] = np.nan
        wide = wide[[country_col] + MBTI_TYPES]
        return wide, country_col

    raise ValueError("MBTI 16개 열(가로형) 또는 (Type, Value) 구성(세로형)을 찾지 못했습니다.")

def normalize_rows_to_100(wide: pd.DataFrame, country_col: str) -> pd.DataFrame:
    out = wide.copy()
    X = out[MBTI_TYPES].astype(float)
    row_sum = X.sum(axis=1, skipna=True).replace(0, np.nan)
    out[MBTI_TYPES] = (X.div(row_sum, axis=0) * 100.0)
    return out

def classify_climate(abs_lat: float) -> str:
    """Very rough climate zone by |latitude|."""
    if pd.isna(abs_lat):
        return "Unknown"
    if abs_lat < 23.5:
        return "Tropical"
    elif abs_lat < 35:
        return "Subtropical"
    elif abs_lat < 60:
        return "Temperate"
    else:
        return "Polar"

# -----------------------------
# 1) Read MBTI data (local-first, then upload)
# -----------------------------
st.sidebar.header("📄 데이터 입력")
mbti_df = None
source_label = None

if os.path.exists(LOCAL_DATA_PATH):
    try:
        mbti_df = robust_read_csv(LOCAL_DATA_PATH)
        source_label = f"로컬 파일 사용: `{LOCAL_DATA_PATH}`"
    except Exception as e:
        st.sidebar.warning(f"로컬 파일 읽기 실패: {e}")

if mbti_df is None:
    up = st.sidebar.file_uploader("MBTI 국가 데이터 CSV 업로드", type=["csv"])
    if up is not None:
        mbti_df = robust_read_csv(up)
        source_label = "업로드 파일 사용"
    else:
        st.info("왼쪽 사이드바에서 CSV를 업로드해 주세요. 예시: countriesMBTI_16types.csv")
        st.stop()

st.sidebar.success(source_label)

# -----------------------------
# 2) Parse MBTI into wide & normalize
# -----------------------------
try:
    wide, country_col = to_wide_by_country(mbti_df)
except Exception as e:
    st.error(f"데이터 구조 해석 실패: {e}")
    st.stop()

wide_norm = normalize_rows_to_100(wide, country_col)

# Keep a normalized long for some charts
long_norm = wide_norm.melt(id_vars=[country_col], value_vars=MBTI_TYPES,
                           var_name="MBTI", value_name="Percent")

# -----------------------------
# 3) Capitals (lat/lon) & Continent fetch (with upload fallback)
# -----------------------------
st.sidebar.subheader("🌍 수도 위도(기후) / 대륙 데이터")
capitals_df = None
cap_up = st.sidebar.file_uploader("수도·위도 CSV(선택) 업로드", type=["csv"], help="열 예시: CountryName, CapitalLatitude, CapitalLongitude, ContinentName")

try:
    if cap_up is not None:
        capitals_df = robust_read_csv(cap_up)
        st.sidebar.success("업로드한 수도·위도 CSV 사용")
    else:
        capitals_df = fetch_csv(CAPITALS_CSV_URL)
        st.sidebar.caption("기본 공개 데이터 소스 사용 중 (country-capitals)")
except Exception as e:
    st.sidebar.warning(f"수도/위도 데이터 불러오기 실패: {e}. 기후 구분은 Unknown으로 표기됩니다.")

# Normalize names for join
wide_norm["_join"] = wide_norm[country_col].apply(fix_name_for_join)

continent_col = None
if capitals_df is not None:
    # Normalize columns
    caps = capitals_df.rename(columns={
        "CountryName":"CountryName",
        "CapitalLatitude":"CapitalLatitude",
        "CapitalLongitude":"CapitalLongitude",
        "ContinentName":"ContinentName"
    })
    # Be lenient with header variants
    for need, alts in {
        "CountryName": ["CountryName","Country","Name","Country Name"],
        "CapitalLatitude": ["CapitalLatitude","Latitude","Capital Latitude"],
        "CapitalLongitude": ["CapitalLongitude","Longitude","Capital Longitude"],
        "ContinentName": ["ContinentName","Continent"]
    }.items():
        if need not in caps.columns:
            for a in alts:
                if a in caps.columns:
                    caps.rename(columns={a: need}, inplace=True)
                    break
    caps["_join"] = caps["CountryName"].apply(fix_name_for_join)
    caps = caps[["_join","CountryName","CapitalLatitude","CapitalLongitude","ContinentName"]]
    continent_col = "ContinentName"
else:
    caps = pd.DataFrame(columns=["_join","CountryName","CapitalLatitude","CapitalLongitude","ContinentName"])

# Merge
geo = wide_norm.merge(caps, on="_join", how="left")
geo["AbsLat"] = geo["CapitalLatitude"].abs()
geo["ClimateZone"] = geo["AbsLat"].apply(classify_climate)
geo["Continent"] = geo.get(continent_col, "Unknown")
geo["Continent"] = geo["Continent"].fillna("Unknown")

# -----------------------------
# 4) Controls
# -----------------------------
st.sidebar.subheader("🧭 시각화 설정")
mbti_sel = st.sidebar.selectbox("MBTI 유형 선택", MBTI_TYPES, index=MBTI_TYPES.index("INFP") if "INFP" in MBTI_TYPES else 0)
size_scale = st.sidebar.slider("버블 크기 배율", 50, 800, 300, step=50)
opacity_fill = st.sidebar.slider("지도 채움 불투명도", 0.2, 1.0, 0.6, step=0.1)

region_filter = st.sidebar.multiselect(
    "대륙(Region) 필터", sorted(geo["Continent"].dropna().unique().tolist()), default=[]
)
climate_filter = st.sidebar.multiselect(
    "기후대(간이) 필터", ["Tropical","Subtropical","Temperate","Polar","Unknown"], default=[]
)

df_view = geo.copy()
if region_filter:
    df_view = df_view[df_view["Continent"].isin(region_filter)]
if climate_filter:
    df_view = df_view[df_view["ClimateZone"].isin(climate_filter)]

# -----------------------------
# 5) World map (geoshape) + bubbles
# -----------------------------
world = fetch_json(WORLD_TOPOJSON_URL)

# Base world map
world_chart = alt.Chart(alt.Data(values=world["objects"]["countries"]["geometries"])).mark_geoshape(
    stroke="#888", strokeWidth=0.25, fill="#d9d9d9", opacity=opacity_fill
).transform_calculate(
    # Reconstruct proper geometry from TopoJSON arcs through vega transform
    # Altair/vega will resolve geoshape if we pass topojson source via "url" style.
    # Here we embed as values + separate geodata layer using vega "feature" isn't available,
    # so we instead pull via url directly below for robustness.
    dummy="0"
)

# Better: use built-in TopoJSON url mapping layer
world_layer = alt.Chart(
    alt.topo_feature(WORLD_TOPOJSON_URL, "countries")
).mark_geoshape(
    fill="#e7e7e7", stroke="#aaaaaa", strokeWidth=0.5
).properties(
    width=980, height=520
)

# Points for capitals
points_df = df_view[[country_col, "CapitalLatitude","CapitalLongitude","ClimateZone","Continent", mbti_sel]].copy()
points_df = points_df.rename(columns={
    "CapitalLatitude":"lat",
    "CapitalLongitude":"lon",
    mbti_sel: "value"
})

# Tooltip
tooltip_cols = [country_col, "Continent","ClimateZone","value"] + MBTI_TYPES
tooltip_cols = [c for c in tooltip_cols if c in df_view.columns or c in ["value"]]
tooltip = [
    alt.Tooltip(country_col, title="Country"),
    alt.Tooltip("Continent:N", title="Region"),
    alt.Tooltip("ClimateZone:N", title="Climate"),
    alt.Tooltip("value:Q", title=f"{mbti_sel} (%)", format=".2f")
]

bubble = alt.Chart(points_df.dropna(subset=["lat","lon"])).encode(
    longitude="lon:Q",
    latitude="lat:Q",
    size=alt.Size("value:Q", title=f"{mbti_sel} (%)", scale=alt.Scale(range=[10, size_scale])),
    color=alt.Color("ClimateZone:N", legend=alt.Legend(title="Climate")),
    tooltip=tooltip
).mark_circle(opacity=0.85).properties(width=980, height=520)

map_chart = (world_layer + bubble).project(type="equalEarth").resolve_scale(size="independent")

st.subheader("🌐 세계 지도 — 선택한 MBTI 비율 버블(수도 좌표) + 기후대 색상")
st.altair_chart(map_chart, use_container_width=True)

# -----------------------------
# 6) Region/Climate comparisons
# -----------------------------
st.subheader("📊 대륙/기후대 × MBTI 분포 비교")

left, right = st.columns(2)

with left:
    region_bar = alt.Chart(long_norm.merge(geo[[country_col,"Continent"]], on=country_col, how="left")).transform_filter(
        alt.FieldOneOfPredicate(field="Continent", oneOf=region_filter) if region_filter else alt.datum.Continent != "___NOFILTER___"
    ).mark_bar().encode(
        x=alt.X("MBTI:N", sort=MBTI_TYPES, title="MBTI"),
        y=alt.Y("mean(Percent):Q", title="평균 비율(%)"),
        color=alt.Color("Continent:N", title="Region"),
        tooltip=[alt.Tooltip("Continent:N","Region"), alt.Tooltip("MBTI:N"), alt.Tooltip("mean(Percent):Q",format=".2f")]
    ).properties(title="Region(대륙)별 MBTI 평균", width=500, height=320)
    st.altair_chart(region_bar, use_container_width=True)

with right:
    climate_bar = alt.Chart(long_norm.merge(geo[[country_col,"ClimateZone"]], on=country_col, how="left")).transform_filter(
        alt.FieldOneOfPredicate(field="ClimateZone", oneOf=climate_filter) if climate_filter else alt.datum.ClimateZone != "___NOFILTER___"
    ).mark_bar().encode(
        x=alt.X("MBTI:N", sort=MBTI_TYPES, title="MBTI"),
        y=alt.Y("mean(Percent):Q", title="평균 비율(%)"),
        color=alt.Color("ClimateZone:N", title="Climate"),
        tooltip=[alt.Tooltip("ClimateZone:N","Climate"), alt.Tooltip("MBTI:N"), alt.Tooltip("mean(Percent):Q",format=".2f")]
    ).properties(title="Climate(간이 기후대)별 MBTI 평균", width=500, height=320)
    st.altair_chart(climate_bar, use_container_width=True)

# -----------------------------
# 7) Correlations with |latitude|
# -----------------------------
st.subheader("📈 위도 절댓값(|lat|)과 MBTI 비율 상관")
corr_df = geo[[country_col,"AbsLat"] + MBTI_TYPES].dropna(subset=["AbsLat"]).copy()

pearson = corr_df[MBTI_TYPES].corrwith(corr_df["AbsLat"], method="pearson").rename("Pearson").to_frame()
spearman = corr_df[MBTI_TYPES].corrwith(corr_df["AbsLat"], method="spearman").rename("Spearman").to_frame()
corr_tbl = pearson.join(spearman).reset_index().rename(columns={"index":"MBTI"})

corr_bar = alt.Chart(corr_tbl.melt("MBTI", var_name="Metric", value_name="Corr")).mark_bar().encode(
    x=alt.X("MBTI:N", sort=MBTI_TYPES),
    y=alt.Y("Corr:Q", scale=alt.Scale(domain=[-1,1])),
    color="Metric:N",
    tooltip=[alt.Tooltip("MBTI:N"), alt.Tooltip("Metric:N"), alt.Tooltip("Corr:Q", format=".3f")]
).properties(width=980, height=280)

st.altair_chart(corr_bar, use_container_width=True)

# -----------------------------
# 8) Top-N table by selected MBTI
# -----------------------------
st.subheader(f"🏅 {mbti_sel} 비율 상위 국가")
top_n = st.slider("상위 N", 5, 30, 10)
top_tbl = df_view[[country_col,"Continent","ClimateZone", mbti_sel]].rename(columns={mbti_sel:"Percent"}).sort_values("Percent", ascending=False).head(top_n)
st.dataframe(top_tbl.reset_index(drop=True))

# -----------------------------
# 9) Data preview (expanders)
# -----------------------------
with st.expander("원본 → 정규화 데이터 미리보기"):
    st.write("원본(상위 5행)")
    st.dataframe(wide.head())
    st.write("정규화(합=100) (상위 5행)")
    st.dataframe(wide_norm.head())

with st.expander("수도/위도/기후 결합 데이터 미리보기"):
    st.dataframe(geo[[country_col,"Continent","ClimateZone","CapitalLatitude","CapitalLongitude"] + MBTI_TYPES].head())
