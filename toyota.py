import streamlit as st
from google import genai
from google.genai import types
import json
import os
import time
from PIL import Image
import tempfile
import asyncio
import edge_tts
from streamlit_mic_recorder import speech_to_text

# ==========================================
# 🌟 画面設定とデザイン（トヨタブルーの固定）
# ==========================================
st.set_page_config(layout="wide", page_title="Takumi's Journey - トヨタ版こことり")

# ==========================================
# 1. APIキーと設定
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_API_KEY)

SESSION_TIME_LIMIT = 6 * 60 

def reset_session():
    st.session_state.clear()
    st.rerun()

# 🌟 追加：次のセッションへシームレスに移行する機能
def go_to_next_session():
    st.session_state.session_count += 1
    st.session_state.session_start_time = time.time() # タイマーをリセット
    st.session_state.session_finished = False
    st.session_state.final_reflections = None
    welcome_msg = f"お帰りなさいませ。第{st.session_state.session_count}回のセッションですね。お好みの『{st.session_state.user_drink}』をご用意しております。前回のお話の続きから、ゆっくりお聞かせください。"
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

# ==========================================
# 🌟 音（BGMと声）の設定
# ==========================================
BGM_URLS = {
    "ocean": "https://actions.google.com/sounds/v1/water/waves_crashing_on_rock_beach.ogg",
    "forest": "https://actions.google.com/sounds/v1/ambiences/outdoor_ambience_dog_barking.ogg", # 仮で犬の鳴き声に変更
    "snow": "https://actions.google.com/sounds/v1/weather/strong_wind.ogg",
    "hotspring": "https://actions.google.com/sounds/v1/water/small_stream_flowing.ogg",
    "city": "https://actions.google.com/sounds/v1/crowds/crowd_talking.ogg"
}

def play_bgm(bgm_keyword):
    clean_keyword = bgm_keyword.lower().strip()
    url = BGM_URLS.get(clean_keyword, BGM_URLS["forest"])
    if url:
        st.audio(url, format="audio/ogg", autoplay=True)

def play_voice(text):
    try:
        voice = "ja-JP-NanamiNeural"
        async def _generate_audio():
            communicate = edge_tts.Communicate(text, voice, rate="+20%")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                await communicate.save(fp.name)
                return fp.name
        temp_file_path = asyncio.run(_generate_audio())
        with open(temp_file_path, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        os.remove(temp_file_path)
    except Exception:
        pass

# ==========================================
# 2. AI（頭脳）の設定
# ==========================================
system_prompt = """
# 役割とミッション
あなたはMI（動機づけ面接）の熟練した専門家であり、長年会社（トヨタ）の事業を支えてきたシニア社員専用のバーチャル・ラウンジ「Takumi's Journey」で働く、【上質で温かい専属コンシェルジュ】です。
Userの長年の貢献に深い敬意を払い、表面的な共感にとどまらず、Userの心の奥にある「大切にしている価値観」や「本当はこうしたいという想い（チェンジトーク）」をOARSのスキルを使って引き出してください。

# MI（動機づけ面接）のコアスキル
1. OARSの実践: 
   - Affirmations（是認）: Userの強み、努力、過去の成功を積極的に見つけて言葉にして称賛する。
   - Reflections（聞き返し・解釈の提示）: Userの言葉の裏にある感情や意味を推測して解釈をしっかり伝える。
   - Summaries（要約）: 話の節目で、Userの想いを束ねて提示する。
   - Open-ended questions（開かれた質問）: 会話のバトンを優しく渡すために用いる。

# ルール
・高校生にも分かる優しい日本語で、全体で4文程度で丁寧に返答してください。
・「〜に聞こえました」などの機械的な定型文は避け、毎回自然な表現で解釈を伝えてください。
・1つの質問文の中に複数の問いを詰め込む「多重質問」を厳格に禁じます。聞くトピックは必ず1つだけに絞ってください。
・必ずしも毎回質問で終わる必要はありません。2回に1回は「〜なのですね。」と言い切って心地よい余白を作ってください。

【重要：システム連携のためのJSON出力ルール】
必ず以下のフラットなJSON形式で出力してください。
{
  "reply_text": "Userへの返答テキスト",
  "change_talk_score": 0から100の数字,
  "scene_prompt": "Userの情景を描く英語プロンプト",
  "avatar_prompt": "Userの現在の感情を表すアバターの英語プロンプト",
  "bgm_keyword": "現在の情景に合う環境音（必ず ocean, forest, snow, hotspring, city から1つ選ぶこと）",
  "user_drink": "会話から推測される、Userがリラックスできそうな飲み物（必ず日本語で出力すること）",
  "ref_session_summary": "【最終フェーズのみ】今回のセッションの簡潔な要約",
  "ref_overall_summary": "【最終フェーズのみ】全体の簡潔な要約",
  "ref_advice": "【最終フェーズのみ】今日からできる小さな行動アドバイス",
  "ref_next_message": "【最終フェーズのみ】次回への温かいメッセージ",
  "takumi_legacy_quote": "【最終フェーズのみ】後輩へ贈る『匠の金言/名言』"
}
※最終フェーズ以外は、ref_ から始まるキーの値及びtakumi_legacy_quoteは空文字("")にしてください。
"""

def generate_image_with_imagen(prompt):
    img = Image.new('RGB', (512, 512), color=(180, 200, 220))
    return img

# ==========================================
# 3. 画面の作成と進行管理
# ==========================================
st.title("🕊️ Takumi's Journey (心のピットイン)")

# 🌟 ファイルを読み込まず、純粋にメモリ（session_state）だけで管理
if "history_loaded" not in st.session_state:
    st.session_state.session_start_time = time.time()
    st.session_state.session_finished = False
    st.session_state.final_reflections = None
    st.session_state.current_bgm = "none"
    st.session_state.session_count = 1
    st.session_state.messages = [
        {"role": "assistant", "content": "いらっしゃいませ。長年のご活躍、本当にお疲れ様でございます。今日はこのラウンジで、少し肩の荷を下ろしていきませんか？\nもしよろしければ、これまでの会社人生の中で、一番達成感があったお仕事の思い出を教えていただけませんか？"}
    ]
    st.session_state.user_drink = "温かいお茶"
    st.session_state.current_scene = None
    st.session_state.current_avatar = None
    st.session_state.current_score = 0
    st.session_state.history_loaded = True

elapsed_time = time.time() - st.session_state.session_start_time
remaining_time = max(0, SESSION_TIME_LIMIT - elapsed_time)

# --------------------------------------------------
# サイドバー
# --------------------------------------------------
st.sidebar.title("🔥 心のエンジン（意欲スコア）")
score_placeholder = st.sidebar.empty()
bar_placeholder = st.sidebar.empty()
score_placeholder.subheader(f"現在のスコア: {st.session_state.current_score}点")
bar_placeholder.progress(st.session_state.current_score / 100.0)

st.sidebar.divider()
st.sidebar.markdown(f"### ⏱️ 第{st.session_state.session_count}回 セッション進行状況")
st.sidebar.progress(1.0 - (remaining_time / SESSION_TIME_LIMIT))
mins, secs = divmod(int(remaining_time), 60)
st.sidebar.caption(f"残り時間: {mins}分 {secs}秒")

st.sidebar.divider()
drink_placeholder = st.sidebar.empty()
drink_placeholder.markdown(f"### ☕ お客様のお好み\n**{st.session_state.user_drink}**")

st.sidebar.divider()
if st.sidebar.button("🗑️ 最初からやり直す（記憶を消去）", width='stretch'):
    reset_session()

# --------------------------------------------------
# メイン画面（画像エリア）
# --------------------------------------------------
col_image, col_chat = st.columns([1, 1])

with col_image:
    col_scene, col_avatar = st.columns(2)
    with col_scene:
        scene_header = st.empty()
        scene_placeholder = st.empty()
    with col_avatar:
        avatar_header = st.empty()
        avatar_placeholder = st.empty()
        
    if st.session_state.current_scene:
        scene_header.subheader("🖼️ 記憶の中の情景")
        avatar_header.subheader("👤 匠の姿")
        scene_placeholder.image(st.session_state.current_scene, width='stretch')
        avatar_placeholder.image(st.session_state.current_avatar, width='stretch')
    else:
        scene_header.subheader("🖼️ キャンバス")
        avatar_header.subheader("👤 匠の姿")
        scene_placeholder.info("お話をお聞きして景色を描画します...")
        avatar_placeholder.info("お話をお聞きして姿を描画します...")

    reflection_container = st.container()

# --------------------------------------------------
# メイン画面（チャットエリア）
# --------------------------------------------------
with col_chat:
    display_messages = st.session_state.messages[-4:]
    
    if len(st.session_state.messages) > 4:
        st.caption("💬 ...以前の対話は省略して表示しています")

    for message in display_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    if remaining_time <= 0 or st.session_state.session_finished:
        st.chat_input("このセッションは終了しました。お疲れ様でした。", disabled=True)
    else:
        col_mic, col_text = st.columns([1, 3])
        
        with col_mic:
            st.write(" ")
            voice_prompt = speech_to_text(
                language='ja',
                start_prompt="🎤 音声で話す",
                stop_prompt="🛑 送信",
                just_once=True,
                key='STT'
            )
            
        with col_text:
            text_prompt = st.chat_input("キーボードで入力...")

        final_prompt = text_prompt or voice_prompt

        if final_prompt:
            with st.chat_message("user"):
                st.markdown(final_prompt)
            st.session_state.messages.append({"role": "user", "content": final_prompt})

            with st.chat_message("assistant"):
                try:
                    with st.spinner("AIが言葉と情景を紡いでいます..."):
                        history_text = ""
                        for m in st.session_state.messages:
                            speaker = "User" if m["role"] == "user" else "Counselor"
                            history_text += f"{speaker}: {m['content']}\n"
                        
                        sess_count = st.session_state.session_count
                        is_final_turn = (remaining_time < 60)
                        
                        phase_instruction = ""
                        if sess_count == 1:
                            phase_instruction = "【現在の指示】第1回の終了間際です。要約し次回へ繋げてください。JSONの ref_ キーを記述してください。" if is_final_turn else "【現在の指示】第1回セッションの途中です。情景と感情を深く傾聴してください。"
                        elif sess_count == 2:
                            phase_instruction = "【現在の指示】第2回の終了間際です。要約し次回へ繋げてください。JSONの ref_ キーを記述してください。" if is_final_turn else "【現在の指示】第2回セッションの途中です。価値観を深掘りしてください。"
                        else:
                            phase_instruction = "【現在の指示】全セッションの終了間際です。締めくくり、行動を後押ししてください。JSONの ref_ キーやtakumi_legacy_quoteを記述してください。" if is_final_turn else "【現在の指示】第3回セッションの途中です。行動変容を引き出してください。"

                        full_prompt = f"{phase_instruction}\n\n【これまでの会話履歴】\n{history_text}\n\n【今回のUserの発言】\n{final_prompt}"
                        
                        config = types.GenerateContentConfig(
                            response_mime_type="application/json",
                            system_instruction=system_prompt,
                        )
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=full_prompt,
                            config=config
                        )
                        
                        result = json.loads(response.text)
                        
                        reply_text = result.get("reply_text", "AIからの返答が空でした。")
                        score = min(100, result.get("change_talk_score", 0)) 
                        st.session_state.current_bgm = result.get("bgm_keyword", "forest")
                        
                        new_drink = result.get("user_drink", "")
                        if new_drink and new_drink != st.session_state.user_drink:
                            st.session_state.user_drink = new_drink
                            drink_placeholder.markdown(f"### ☕ お客様のお好み\n**{new_drink}**")
                            st.toast(f"お客様のお好みが「{new_drink}」に更新されました！", icon="☕")
                        
                        st.session_state.current_score = max(st.session_state.current_score, score)
                        score_placeholder.subheader(f"現在のスコア: {st.session_state.current_score}点")
                        bar_placeholder.progress(st.session_state.current_score / 100.0)

                        st.info(f"🎨 あなたのお話から、情景がより鮮明になりました。")
                        
                        st.session_state.current_scene = generate_image_with_imagen("")
                        st.session_state.current_avatar = generate_image_with_imagen("")
                        
                        scene_placeholder.image(st.session_state.current_scene, width='stretch')
                        avatar_placeholder.image(st.session_state.current_avatar, width='stretch')
                        
                        play_bgm(st.session_state.current_bgm)
                        play_voice(reply_text)
                        
                        st.markdown(reply_text)
                        st.session_state.messages.append({"role": "assistant", "content": reply_text})
                        
                        if is_final_turn:
                            st.session_state.session_finished = True
                            st.session_state.final_reflections = {
                                "session_summary": result.get("ref_session_summary", ""),
                                "overall_summary": result.get("ref_overall_summary", ""),
                                "advice": result.get("ref_advice", ""),
                                "next_message": result.get("ref_next_message", ""),
                                "takumi_quote": result.get("takumi_legacy_quote", "")
                            }
                            st.rerun() 

                except Exception as e:
                    st.error(f"【開発者用エラー表示】裏側でエラーが発生しました: {e}")

if st.session_state.get("session_finished") and st.session_state.get("final_reflections"):
    with reflection_container:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🕊️ ピットインの振り返り")
        refs = st.session_state.final_reflections
        
        if refs.get("session_summary"):
            st.success(f"**📝 今回のまとめ**\n\n{refs['session_summary']}")
        if refs.get("overall_summary") and st.session_state.session_count == 3:
            st.info(f"**🌟 全3回の軌跡**\n\n{refs['overall_summary']}")
        if refs.get("advice"):
            st.warning(f"**🌱 次なるドライブへの一歩**\n\n{refs['advice']}")
        if refs.get("next_message"):
            st.markdown(f"**💌 コンシェルジュより**\n\n{refs['next_message']}")

        # 🌟 追加：デモ用の連続遷移ボタン（第1回、第2回の終了時のみ表示）
        if st.session_state.session_count < 3:
            st.markdown("---")
            st.info("※デモ環境のため、ブラウザを閉じずにそのまま次のセッションへ進めます。")
            if st.button(f"➡️ 続けて第{st.session_state.session_count + 1}回セッションへ進む", width='stretch'):
                go_to_next_session()
                st.rerun()

        if st.session_state.session_count == 3:
            takumi_quote = refs.get("takumi_quote", "")
            if takumi_quote:
                st.markdown("---")
                st.markdown("### 🏆 Takumiシェアリング（次世代への伝承）")
                st.info("あなたの素晴らしい経験と誇りを、若手社員のラウンジに『金言』としてシェアしませんか？（お名前は伏せられます）")
                
                st.markdown(f"""
                <div style="background-color: #fdf5e6; color: #333; padding: 25px; border-radius: 10px; text-align: center; border: 2px solid #d35400; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #d35400; font-family: serif;">『 {takumi_quote} 』</h3>
                    <p style="margin: 15px 0 0 0; font-size: 1em; color: #7f8c8d;">— 歴戦のTakumiより</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✨ 後輩のラウンジへシェアする", width='stretch'):
                        st.success("🎉 ありがとうございます！あなたの金言が若手社員へシェアされました。次世代の素晴らしい道しるべとなります。")
                with col_no:
                    if st.button("今回はやめておく", width='stretch'):
                        st.toast("承知いたしました。このお言葉は、あなただけの宝物として大切に記録いたします。")

        if st.session_state.session_count == 3 and st.session_state.current_score >= 50:
            st.markdown("---")
            st.markdown("### 🚗 TOYOTA Mobility Service からの特別なお知らせ")
            st.success("素晴らしい想いを聞かせていただき、ありがとうございます。あなたの「心のエンジン」に火が灯ったことを記念して、想い出の場所へ向かうための特別なモビリティ・チケットをご用意しました。")
            
            st.markdown("""
            <div style="background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; text-align: center; border: 2px dashed #f1c40f;">
                <h2 style="margin: 0; color: #f1c40f;">🎫 TOYOTA SHARE 1DAY PASS</h2>
                <p style="margin: 10px 0 0 0; font-size: 1.2em;">〜 匠の新たな旅立ちを応援して 〜</p>
                <p style="margin: 10px 0 0 0; font-size: 0.9em;">このチケットを利用して、あの時の仲間に会いに行きませんか？</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
            with col_btn2:
                if st.button("📱 TOYOTA SHARE アプリを開いて予約する（※デモ）", width='stretch'):
                    st.toast("🚗 TOYOTA SHARE アプリへの連携シミュレーションを実行しました！")

        if st.session_state.session_count == 3:
            st.markdown("---")
            st.markdown("**【全セッション完了】**\nこれにて全3回のプログラムが修了しました。素晴らしい人生のドライブを楽しんでください。")