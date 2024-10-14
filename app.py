import os
import openai
import streamlit as st
import base64
from difflib import SequenceMatcher


from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import numpy as np
import threading
import queue


openai.api_key = st.secrets['API_KEY']


initial_script = [
    "Narrator: It's a beautiful fall morning on the farm.",
    "Narrator: The leaves are turning yellow and red.",
    "Narrator: Fern comes to visit Wilbur, her favorite pig.",
    "Fern: Good morning, Wilbur! How are you today?",
    "Wilbur: Oh, Fern! I'm so happy to see you. I was feeling a little lonely.",
    "Fern: Don't be lonely, Wilbur. You have so many friends here on the farm!",
    "Charlotte: Good morning, Fern. You're right, Wilbur has many friends, including me.",
    "Wilbur: Charlotte! I'm so glad you're here. Fern, isn't Charlotte amazing? She can make the most beautiful webs."
]

if 'current_line' not in st.session_state:
    st.session_state.current_line = 0
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

st.markdown("""
<style>
    .main {
        background-color: #f0f8ff;
        padding: 20px;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
    }
    .stTextInput>div>div>input {
        background-color: #e6f3ff;
        border-radius: 5px;
    }
    h1 {
        color: #2E8B57;
        text-align: center;
    }
    h2 {
        color: #4682B4;
    }
    .script-line {
        background-color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🕷️ 샬롯의 거미줄 인터랙티브 학습 🐷")

def text_to_speech(text):
    
    from gtts import gTTS
    from io import BytesIO

    tts = gTTS(text=text, lang='en')
    audio_bytes = BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)

    st.audio(audio_bytes.read(), format='audio/mp3')

def generate_response(prompt):
    st.session_state.conversation_history.append({"role": "user", "content": prompt})

    try:
        chat_completion = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI tutor helping a student learn English through the story of Charlotte's Web. Provide explanations, answer questions, and engage in dialogue about the story, characters, and language used. Keep your responses appropriate for young learners."},
                *st.session_state.conversation_history
            ]
        )

        ai_response = chat_completion.choices[0].message.content.strip()
        st.session_state.conversation_history.append({"role": "assistant", "content": ai_response})
        return ai_response
    except Exception as e:
        st.error(f"에러가 발생했습니다: {str(e)}")
        return "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."

def recognize_speech():
    
    pass  

def evaluate_speech_accuracy(original_text, recognized_text):
    similarity = SequenceMatcher(None, original_text.lower(), recognized_text.lower()).ratio()
    return similarity * 100

st.sidebar.header("전체 대본")
for i, line in enumerate(initial_script):
    st.sidebar.markdown(f'<div class="script-line">{line}</div>', unsafe_allow_html=True)
    if st.sidebar.button(f"🔊 듣기", key=f"listen_{i}"):
        text_to_speech(line)


st.header("🎧 순차적 듣기")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⏮️ 이전 줄") and st.session_state.current_line > 0:
        st.session_state.current_line -= 1

with col2:
    if st.button("▶️ 현재 줄 듣기"):
        text_to_speech(initial_script[st.session_state.current_line])

with col3:
    if st.button("⏭️ 다음 줄") and st.session_state.current_line < len(initial_script) - 1:
        st.session_state.current_line += 1

st.info(f"현재 줄: {initial_script[st.session_state.current_line]}")


st.header("💬 인터랙티브 학습")
input_method = st.radio("입력 방법 선택:", ("텍스트", "음성"))

if input_method == "텍스트":
    user_input = st.text_input("스토리, 등장인물 또는 언어에 대해 질문하세요:")
else:
    st.write("녹음을 시작하려면 'Start'를 클릭하세요.")
    
    RTC_CONFIGURATION = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

    from streamlit_webrtc import AudioProcessorBase

    class AudioProcessor(AudioProcessorBase):
        def __init__(self):
            self.audio_frames = []

        def recv(self, frame):
            # 오디오 프레임 수집
            self.audio_frames.append(frame)
            return frame

    webrtc_ctx = webrtc_streamer(
        key="speech-recognition",
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"audio": True, "video": False},
        audio_processor_factory=AudioProcessor,
        async_processing=True,
    )

    if webrtc_ctx.audio_processor:
        if st.button("오디오 처리하기"):
            st.write("오디오를 처리 중입니다...")
           
            audio_frames = webrtc_ctx.audio_processor.audio_frames

          
            from pydub import AudioSegment
            from io import BytesIO

            combined = AudioSegment.empty()
            for frame in audio_frames:
                audio = frame.to_ndarray()
                sound = AudioSegment(
                    data=audio.tobytes(),
                    sample_width=audio.dtype.itemsize,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels),
                )
                combined += sound

            
            audio_buffer = BytesIO()
            combined.export(audio_buffer, format="wav")
            audio_buffer.seek(0)

           
            import speech_recognition as sr

            r = sr.Recognizer()
            with sr.AudioFile(audio_buffer) as source:
                audio_data = r.record(source)
                try:
                    user_input = r.recognize_google(audio_data)
                    st.write(f"당신이 말한 내용: {user_input}")

               
                    current_line = initial_script[st.session_state.current_line]
                    accuracy = evaluate_speech_accuracy(current_line, user_input)
                    st.write(f"음성 인식 정확도: {accuracy:.2f}%")

                    if accuracy >= 90:
                        st.success("발음이 매우 좋습니다!")
                    elif accuracy >= 70:
                        st.info("좋은 발음입니다. 계속 연습하세요!")
                    else:
                        st.warning("발음 개선이 필요합니다. 다시 시도해 보세요!")
                except sr.UnknownValueError:
                    st.error("음성을 이해할 수 없습니다.")
                except sr.RequestError:
                    st.error("음성 인식 서비스에 요청할 수 없습니다.")
        else:
            st.write("녹음을 마친 후 '오디오 처리하기'를 눌러주세요.")

if st.button("🚀 제출") and 'user_input' in locals():
    with st.spinner("AI 튜터가 생각 중입니다..."):
        ai_response = generate_response(user_input)
    st.success("AI 튜터: " + ai_response)
    if st.button("🔊 AI 응답 듣기"):
        text_to_speech(ai_response)

st.header("📜 대화 기록")
for message in st.session_state.conversation_history:
    if message['role'] == 'user':
        st.markdown(f"**사용자:** {message['content']}")
    else:
        st.markdown(f"**AI 튜터:** {message['content']}")