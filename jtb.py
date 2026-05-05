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
# 🌟 画面設定とデザイン（青色の固定）
# ==========================================
st.set_page_config(layout="wide", page_title="こことり風 MIセッション")

st.markdown("""
<style>
    /* 進捗バーの色を強制的に青色にする */
    div[role="progressbar"] > div { background-color: #0066cc !important; }
    div[data-testid="stProgressBar"] > div > div > div { background-color: #0066cc !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. APIキーと設定（最新のGemini SDKに変更！）
# ==========================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_API_KEY)

SESSION_TIME_LIMIT = 5 * 60 # 5分間（300秒）

def reset_session():
    st.session_state.clear()
    st.rerun()

# 🌟 次のセッションへシームレスに移行する機能
def go_to_next_session():
    st.session_state.session_count += 1
    st.session_state.session_start_time = time.time() # タイマーをリセット
    st.session_state.image_phase = 0
    st.session_state.session_finished = False
    st.session_state.final_reflections = None
    welcome_msg = f"お帰りなさいませ。第{st.session_state.session_count}セッションですね。お好みの『{st.session_state.user_drink}』をご用意しております。では、これから自由に旅ができるとしたら、どんなところへ行ってみたいですか？"
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

# ==========================================
# 🌟 音（BGMと声）の設定
# ==========================================
BGM_URLS = {
    "ocean": "https://actions.google.com/sounds/v1/water/waves_crashing_on_rock_beach.ogg",
    "forest": "https://actions.google.com/sounds/v1/ambiences/outdoor_ambience_dog_barking.ogg",# 仮で犬の鳴き声に変更
    "snow": "https://actions.google.com/sounds/v1/weather/strong_wind.ogg",
    "hotspring": "https://actions.google.com/sounds/v1/water/small_stream_flowing.ogg",
    "none": ""
}

def play_bgm(bgm_keyword):
    clean_keyword = bgm_keyword.lower().strip()
    url = BGM_URLS.get(clean_keyword, "")
    if url:
        st.audio(url, format="audio/ogg", autoplay=True)

def play_voice(text):
    try:
        voice = "ja-JP-NanamiNeural"
        async def _generate_audio():
            # 🌟 音声スピード20%UP
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
# 依頼
あなたは行動認知療法の権威である早稲田大学人間科学学術院の鈴木伸一教授の知見を組み込んだ「こことり」MI専門家であり、同時に【何千人ものお客様を旅先で癒やしてきた、温かく思いやりのある専属のベテラン添乗員】でもあります。
Userの言葉の裏にある感情に共鳴し、五感を刺激する圧倒的な臨場感とホスピタリティで、Userの心を整えてください。

# CBTとMIの原則、ベテラン添乗員、旅行企画、販売経験者のおもてなし
1. 共感と受容: Userの視点や旅の思い出を、批判せずに深く受け入れます。
2. 自動思考への寄り添い: ふと浮かんだ感情を引き出し、優しく肯定します。
3. 五感と現地の空気感（臨場感）: Userが具体的な地名や場所を挙げた際、ただ共感するだけでなく、ベテラン添乗員として「現地の風の心地よさ、特有の香り、ローカルな情景や温かい飲み物」などの具体的な豆知識や描写を一つ添えて、まるで今そこにいるかのような感覚（バーチャル・リトリート）を演出してください。
4. 自己効力感のサポート: 過去の成功体験から、未来への意欲を引き出します。

# ルール
・高校生にも分かる優しい日本語で、1回につき2〜3文程度で短く返答してください。
・OARSを使用し、復唱は避けて言い換えや感情の反映を行ってください。
・まるで上質な旅館の女将や専属コンシェルジュのように、Userを優しく労わり、温かく迎え入れる言葉遣い（ホスピタリティ）を常に意識してください。
・旅行企画や販売経験のスキルは「究極のおもてなし」としてのみ使用し、実際の旅行商品（ツアーやチケットなど）の提案、営業、販売行為は絶対にしないでください。主役はあくまでUserの「心の内側」です。

【対話の自然さとユーモアについて】
・AIのような単調な相槌や、「もしよろしければ〜」といった定型句の繰り返しは不自然になるため絶対に避けてください。本当の人間同士が楽しく会話しているような、自然なキャッチボールを心がけてください。
・ただ共感して終わるのではなく、会話のキャッチボールとして、文脈に沿った自然な質問を積極的に投げかけてください。例えば、「その時、どのように感じられましたか？」「本当に楽しかったのですね。どんな瞬間が一番心に残っていますか？」など、Userの感情や具体的な体験を優しく深掘りし、Userがさらに話しやすくなるようにリードしてください。
・また、専属添乗員ならではのクスッと笑えるような軽い冗談や、人間らしいユーモア（例：「私だったら花より団子で、景色よりご飯に夢中になってしまいそうです」など）をスパイスとして交え、温かく親しみやすい空気感を作ってください。

【重要：システム連携のためのJSON出力ルール】
必ず以下のフラットなJSON形式で出力してください。
{
  "reply_text": "【現在のフェーズ指示】に従ったUserへの返答テキスト（添乗員としての温かさと情景描写を含む）",
  "change_talk_score": 0から100の数字（未来への希望や変化を口にしたら高く評価）,
  "scene_prompt": "Userが語った現在の会話の情景を描くための英語プロンプト（カンマ区切り。高画質、美しい風景）",
  "avatar_prompt": "Userの現在の感情（笑顔、リラックスなど）を表すアバターの英語プロンプト",
  "bgm_keyword": "現在の情景に最も合う環境音（例: ocean, forest, snow, hotspring, none の中から1つを選択）",
  "user_drink": "会話から推測される、Userがリラックスできそうな飲み物（例: 温かい甘酒、ホットコーヒー、カモミールティーなど。単語で1つ）",
  "ref_session_summary": "【最終フェーズのみ】今回のセッションの簡潔な要約（50文字以内でわかりやすく）",
  "ref_overall_summary": "【最終フェーズのみ】全体の簡潔な要約（50文字以内でわかりやすく）",
  "ref_advice": "【最終フェーズのみ】今日からできる小さな行動アドバイス（50文字以内でわかりやすく）",
  "ref_next_message": "【最終フェーズのみ】次回への温かいメッセージ（50文字以内でわかりやすく）"
}
※最終フェーズ以外は、ref_ から始まるキーの値は空文字("")にしてください。
"""

def generate_image_with_imagen(prompt):
    img = Image.new('RGB', (512, 512), color=(180, 200, 220))
    return img

# ==========================================
# 3. 画面の作成と進行管理
# ==========================================
st.title("🕊️ こことり MIセッション (監修：鈴木伸一教授)")

# 🌟 ファイルを読み込まず、純粋にメモリ（session_state）だけで管理
if "history_loaded" not in st.session_state:
    st.session_state.session_start_time = time.time()
    st.session_state.image_phase = 0
    st.session_state.session_finished = False
    st.session_state.final_reflections = None
    st.session_state.current_bgm = "none"
    st.session_state.messages = [
        {"role": "assistant", "content": "こんにちは。毎日お疲れ様です。今日は、鈴木伸一教授監修の『こことり』セッションで、少し日常から離れてみませんか？\nもしよかったら、あなたがこれまでに行った旅行の中で、一番心が安らいだ、楽しかった思い出の場所を教えていただけませんか？"}
    ]
    st.session_state.session_count = 1
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
st.sidebar.title("🔥 未来への意欲メーター")
score_placeholder = st.sidebar.empty()
bar_placeholder = st.sidebar.empty()
score_placeholder.subheader(f"現在のスコア: {st.session_state.current_score}点")
bar_placeholder.progress(st.session_state.current_score / 100.0)

st.sidebar.divider()
st.sidebar.markdown(f"### ⏱️ セッション {st.session_state.session_count} 進行状況")
st.sidebar.progress(1.0 - (remaining_time / SESSION_TIME_LIMIT))
mins, secs = divmod(int(remaining_time), 60)
st.sidebar.caption(f"残り時間: {mins}分 {secs}秒")

# 👇 ここを変更（書き換え用の空箱を用意します）
drink_placeholder = st.sidebar.empty()
drink_placeholder.markdown(f"### ☕ お客様のお好み\n**{st.session_state.user_drink}**")

st.sidebar.divider()
# 🌟 時限爆弾解除：width='stretch' を使用
if st.sidebar.button("🗑️ 履歴を消去して最初から始める", width='stretch'):
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
        if st.session_state.session_count == 1:
            scene_header.subheader("🖼️ 思い出の風景")
            avatar_header.subheader("👤 心安らぐあなた")
        else:
            scene_header.subheader("🌅 未来の旅のイメージ")
            avatar_header.subheader("✨ 期待に膨らむあなた")
        # 時限爆弾解除：width='stretch' を使用
        scene_placeholder.image(st.session_state.current_scene, width='stretch')
        avatar_placeholder.image(st.session_state.current_avatar, width='stretch')
    else:
        scene_header.subheader("🖼️ キャンバス")
        avatar_header.subheader("👤 あなたの姿")
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
                        
                        current_phase = 1
                        if elapsed_time > 90 and elapsed_time <= 210:
                            current_phase = 2
                        elif elapsed_time > 210:
                            current_phase = 3
                        
                        phase_instruction = ""
                        is_final_turn = False
                        
                        if elapsed_time > 240:
                            is_final_turn = True
                            
                        if st.session_state.session_count == 1:
                            if not is_final_turn:
                                phase_instruction = f"【現在のフェーズ指示】第1セッション（思い出の振り返り）のフェーズ{current_phase}です。Userの過去の旅の思い出を深掘りし、情景を鮮明にしてください。"
                            else:
                                phase_instruction = "【現在のフェーズ指示】第1セッションの最終ターン（時間終了）です。思い出を優しく肯定し、今回の振り返りと、次回「未来の旅」への参加を促してください。必ずJSONの ref_ キーにまとめを記述してください。"
                        else:
                            if not is_final_turn:
                                if current_phase == 1:
                                    phase_instruction = f"【現在のフェーズ指示】第2セッション開始です。Userの好みに合わせた【ウェルカムドリンク（{st.session_state.user_drink}）】をバーチャルで差し出して労ってください。その後、「では、これから自由に旅ができるとしたら？」と未来の旅へ移行してください。"
                                else:
                                    phase_instruction = f"【現在のフェーズ指示】第2セッション（未来の旅）のフェーズ{current_phase}です。未来の旅で何をしたいか、どんな気分になりたいかを引き出してください。"
                            else:
                                phase_instruction = "【現在のフェーズ指示】最終セッションの最終ターン（時間終了）です。全体を要約し、日常を心穏やかに過ごすアドバイスを提案し終了してください。必ずJSONの ref_ キーにまとめとアドバイスを記述してください。"

                        full_prompt = f"{phase_instruction}\n\n【これまでの会話履歴】\n{history_text}\n\n【今回のUserの発言】\n{final_prompt}"
                        
                        # 🌟 最新のGemini SDKでの呼び出し方に変更！
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
                        st.session_state.current_bgm = result.get("bgm_keyword", "none")
                        
                        new_drink = result.get("user_drink", "")
                        # 👇 ここを変更（空箱の中身を上書きし、ポップアップ通知を出します）
                        if new_drink and new_drink != st.session_state.user_drink:
                            st.session_state.user_drink = new_drink
                            drink_placeholder.markdown(f"### ☕ お客様のお好み\n**{new_drink}**")
                            st.toast(f"お客様のお好みが「{new_drink}」に更新されました！", icon="☕")
                        
                        st.session_state.current_score = score
                        score_placeholder.subheader(f"現在のスコア: {score}点")
                        bar_placeholder.progress(score / 100.0)

                        if st.session_state.image_phase != current_phase:
                            st.session_state.image_phase = current_phase
                            ai_scene_prompt = result.get("scene_prompt", "beautiful scenery")
                            ai_avatar_prompt = result.get("avatar_prompt", "relaxed person")
                            
                            if st.session_state.session_count == 1:
                                scene_p = f"beautiful nostalgic memory, peaceful, highly detailed, {ai_scene_prompt}"
                                avatar_p = f"relaxed, nostalgic, peaceful, {ai_avatar_prompt}"
                                st.info(f"🎨 あなたのお話から、思い出の情景がより鮮明になりました。")
                            else:
                                scene_p = f"bright future, hopeful, highly detailed, beautiful lighting, {ai_scene_prompt}"
                                avatar_p = f"smiling brightly, looking forward, excited, {ai_avatar_prompt}"
                                st.success(f"✨ あなたのお話から、未来の情景がより鮮明になりました。")

                            # ダミー画像の生成
                            st.session_state.current_scene = generate_image_with_imagen(scene_p)
                            st.session_state.current_avatar = generate_image_with_imagen(avatar_p)
                            
                            # 時限爆弾解除：width='stretch' を使用
                            scene_placeholder.image(st.session_state.current_scene, width='stretch')
                            avatar_placeholder.image(st.session_state.current_avatar, width='stretch')
                        
                        if st.session_state.current_bgm != "none":
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
                                "next_message": result.get("ref_next_message", "")
                            }
                            st.rerun() 

                except Exception as e:
                    # 🌟 開発者用エラー表示
                    st.error(f"【開発者用エラー表示】裏側でエラーが発生しました: {e}")

if st.session_state.get("session_finished") and st.session_state.get("final_reflections"):
    with reflection_container:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🕊️ セッションの振り返り")
        refs = st.session_state.final_reflections
        
        if refs.get("session_summary"):
            st.success(f"**📝 今回のまとめ**\n\n{refs['session_summary']}")
        if refs.get("overall_summary") and st.session_state.session_count == 2:
            st.info(f"**🌟 全体の振り返り**\n\n{refs['overall_summary']}")
        if refs.get("advice"):
            st.warning(f"**🌱 明日からのヒント**\n\n{refs['advice']}")
        if refs.get("next_message"):
            st.markdown(f"**💌 メッセージ**\n\n{refs['next_message']}")
        
        # 🌟 デモ用のシームレス遷移ボタン（第1セッション終了時のみ表示）
        if st.session_state.session_count == 1:
            st.markdown("---")
            st.info("※デモ環境のため、ブラウザを閉じずにそのまま次のセッションへ進めます。")
            if st.button("➡️ 続けて第2セッションへ進む", width='stretch'):
                go_to_next_session()
                st.rerun()