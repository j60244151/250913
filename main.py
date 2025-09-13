import streamlit as st

# ---- 페이지 설정 ----
st.set_page_config(page_title="MBTI 스트레스 해소 팁 💛", page_icon="🍋", layout="centered")

# ---- 귀여운 스타일 CSS ----
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');

    html, body, [class*="css"] {
        font-family: 'Jua', sans-serif;
        background-color: #fff9e6;
        color: #444;
    }
    .stSelectbox label {
        font-size: 20px !important;
        color: #ffb300 !important;
    }
    .stButton>button {
        background-color: #ffeb3b !important;
        color: #444 !important;
        border-radius: 20px !important;
        font-size: 18px !important;
        padding: 10px 20px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #ffd600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---- MBTI별 스트레스 해소 방법 ----
stress_tips = {
    "ISTJ": "📚 책 한 권 딱! 조용히 읽으면서 마음 정리하기 어때? 😌",
    "ISFJ": "🍪 맛있는 간식 잔뜩 먹고 달콤한 낮잠 자버리자~ 💤",
    "INFJ": "🌌 별 보면서 혼자만의 깊은 생각 타임 가져봐 ✨",
    "INTJ": "🧩 퍼즐 맞추기나 전략게임으로 뇌 자극 ㄱㄱ! 🕹️",
    "ISTP": "🚴‍♂️ 자전거 타고 바람 쐬러 나가자! 🌬️",
    "ISFP": "🎨 그림 그리면서 감성 폭발시키기! 🖌️",
    "INFP": "📖 일기 쓰면서 마음 정리하고 노래 틀어두자~ 🎶",
    "INTP": "💻 새로운 흥미로운 자료 파고들면서 두뇌 산책 🌐",
    "ESTP": "🎤 노래방 가서 시원하게 고래고래 불러버리기! 🔥",
    "ESFP": "💃 춤추고 노래하면서 에너지 팡팡 충전하기 🎉",
    "ENFP": "😆 친구 불러서 웃음 폭발 수다 파티 ㄱㄱ 🥤",
    "ENTP": "🤪 이상한 발명 아이디어로 장난쳐보자! ㅋㅋ",
    "ESTJ": "📅 방 싹 정리하고 일정 짜면 개운해질걸? 🧹",
    "ESFJ": "☕ 따뜻한 차 마시면서 좋아하는 사람과 수다 🥰",
    "ENFJ": "🤗 친구들 모아서 같이 게임하거나 영화 보자 🎬",
    "ENTJ": "🏋️‍♀️ 운동하면서 땀 쫙 빼면 완전 상쾌! 💪"
}

# ---- 메인 화면 ----
st.title("🍋 MBTI 스트레스 해소 비법 🍋")
st.write("너의 MBTI를 골라봐 👉 내가 딱 맞는 **스트레스 해소법** 알려줄게! 😎✨")

user_mbti = st.selectbox("👉 MBTI 선택하기", list(stress_tips.keys()))

if st.button("추천 받기 💛"):
    st.subheader(f"너의 스트레스 해소 비법은... ✨")
    st.success(stress_tips[user_mbti])
    st.balloons()
