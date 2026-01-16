import streamlit as st
import time
import json
import os
import base64
import re
import random

# --- 1. ページ基本設定 & CSS ---
st.set_page_config(page_title="BARISTA TIMER", layout="wide")

def local_css():
    st.markdown("""
        <style>
        .stApp { background-color: #000000; color: #ffffff; }
        .block-container {
            padding-top: 4rem !important;
        }
        [data-testid="stMetric"] {
            margin-bottom: -1.1rem !important;
        }
        [data-testid="stMetricValue"] { 
            font-size: 1.2rem !important; 
            color: #d4a373 !important; 
        }
        [data-testid="stMetricLabel"] { 
            font-size: 1.0rem !important; 
            color: #ffffff !important; 
            font-weight: 600;
            letter-spacing: 1px;
        }
        .op-title { font-size: 1.5rem; color: #d4a373; text-align: center; margin-top: 10px; font-weight: bold; }
        .timer-display { font-size: 100px; font-weight: 800; color: #ffffff; text-align: center; line-height: 1; margin: 0; font-family: 'Courier New', Courier, monospace; }
        .cumulative-display { font-size: 2.5rem; color: #888888; text-align: center; letter-spacing: 2px; }
        
        .weight-container {
            text-align: center;
            margin-top: 10px;
            font-family: sans-serif;
        }
        .prev-weight {
            font-size: 1.8rem;
            color: #666666;
        }
        .arrow {
            font-size: 1.8rem;
            color: #d4a373;
            margin: 0 15px;
        }
        .target-weight {
            font-size: 3.5rem;
            font-weight: bold;
            color: #d4a373;
            text-shadow: 0 0 10px rgba(212, 163, 115, 0.3);
        }
        .add-weight {
            display: block;
            font-size: 1.2rem;
            color: #888888;
            margin-top: -5px;
        }

        .stButton>button {
            width: 100%;
            border-radius: 8px;
            background-color: #262626;
            color: #ffffff;
            border: 1px solid #444444;
            height: 4em;
            font-weight: 800;
            font-size: 1.1rem;
            letter-spacing: 2px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .stButton>button:hover {
            border-color: #d4a373;
            color: #d4a373;
            background-color: #1a1a1a;
            box-shadow: 0 0 15px rgba(212, 163, 115, 0.4);
        }
        .stProgress > div > div > div > div { background-color: #d4a373; }
        .step-card-mini { font-size: 1.1rem; padding: 8px 0; border-bottom: 1px solid #222; }
        .next-step-box {
            background-color: #111; border: 2px solid #d4a373; border-radius: 12px;
            padding: 15px; text-align: center; margin: 10px 0 25px 0;
        }
        .next-label { color: #888; font-size: 1.00rem; text-transform: uppercase; letter-spacing: 3px; }
        .next-action { color: #d4a373; font-size: 1.5rem; font-weight: bold; }
        .next-specs-unified { color: #ffffff; font-size: 1.6rem; margin-top: 5px; font-weight: bold; }
        .recipe-note-box {
            background-color: #1a1a1a; border-left: 3px solid #d4a373;
            padding: 12px; margin: 15px 0; font-size: 1.0rem; color: #cccccc; 
            font-style: italic; border-radius: 0 4px 4px 0;
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. ユーティリティ ---
sound_placeholder = st.empty()

def play_sound_js(file_name):
    if os.path.exists(file_name):
        with open(file_name, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            t = time.time()
            audio_html = f"""
                <div id="audio-container-{t}">
                    <audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>
                </div>
            """
            with sound_placeholder:
                st.components.v1.html(audio_html, height=0)

def load_recipes():
    # パスを 'recipes' に修正
    recipe_dir = 'recipes'
    all_recipes = []
    
    if os.path.exists(recipe_dir):
        json_files = sorted([f for f in os.listdir(recipe_dir) if f.endswith('.json')], reverse=True)
        
        for file_name in json_files:
            file_path = os.path.join(recipe_dir, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_recipes.extend(data)
                    else:
                        all_recipes.append(data)
            except Exception as e:
                st.error(f"Error loading {file_name}: {e}")
    
    # データがない場合のデフォルト値を "No recipe" に設定
    if not all_recipes:
        return [{
            "name": "No recipe", 
            "beans": "No recipe", 
            "temp": "No recipe", 
            "grind": "No recipe", 
            "steps": []
        }]
    
    return all_recipes

# --- 3. セッション状態 ---
if 'running' not in st.session_state: st.session_state.running = False
if 'current_step' not in st.session_state: st.session_state.current_step = -1

# --- 4. UI構築 ---
if os.path.exists("logo.png"):
    _, col2, _ = st.columns([1, 4, 1])
    with col2:
        st.image("logo.png", use_container_width=True)

st.markdown("<h3 style='text-align: center; color: #d4a373; margin-bottom:0;'>BARISTA TIMER</h3>", unsafe_allow_html=True)

recipes_data = load_recipes()
recipe_names = [r["name"] for r in recipes_data]
selected_name = st.selectbox("Select Profile", recipe_names, label_visibility="collapsed")
recipe = next(r for r in recipes_data if r["name"] == selected_name)

# データの計算
total_duration_sec = sum(step["duration"] for step in recipe["steps"])
total_mins, total_secs = divmod(total_duration_sec, 60)
total_time_str = f"{total_mins:02d}:{total_secs:02d}"
total_water_sum = sum(step["water"] for step in recipe["steps"])

beans_val = recipe.get('beans', 0)
if isinstance(beans_val, str):
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", beans_val)
    beans_num = float(nums[0]) if nums else 0
else:
    beans_num = float(beans_val)

brew_ratio_str = f"1:{total_water_sum / beans_num:.1f}" if beans_num > 0 else "-"

# 表示エリア (横並びから1行ずつに変更)
st.metric("TOTAL WATER", f"{total_water_sum}g")
st.metric("TOTAL TIME", total_time_str)
st.metric("TEMP", recipe.get('temp', '-'))
st.metric("BEANS", recipe.get('beans', '-'))
st.metric("BREW RATIO", brew_ratio_str)
st.metric("GRIND", recipe.get('grind', '-'))

if "note" in recipe and recipe["note"]:
    st.markdown(f'<div class="recipe-note-box">💡 {recipe["note"]}</div>', unsafe_allow_html=True)

btn_label = "🔄 RESET" if st.session_state.running else "▶ START"
if st.button(btn_label):
    st.session_state.running = not st.session_state.running
    st.session_state.current_step = 0 if st.session_state.running else -1
    st.rerun()

# --- タイマーおよびスケジュール表示 ---
timer_area = st.empty()
schedule_area = st.empty()

def draw_schedule(current_idx):
    with schedule_area.container():
        steps = recipe["steps"]
        if st.session_state.running:
            if current_idx == -2: 
                n = steps[0]
                st.markdown(f'<div class="next-step-box"><div class="next-label">PREPARING...</div><div class="next-action">READY?</div><div class="next-specs-unified">First: {n["action"]}</div></div>', unsafe_allow_html=True)
            elif 0 <= current_idx < len(steps):
                next_idx = current_idx + 1
                if next_idx < len(steps):
                    n = steps[next_idx]
                    st.markdown(f'<div class="next-step-box"><div class="next-label">UP NEXT</div><div class="next-action">{n["action"]}</div><div class="next-specs-unified">{n["water"]}g / {n["duration"]}s</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="next-step-box"><div class="next-label">UP NEXT</div><div class="next-action">FINISH</div></div>', unsafe_allow_html=True)

        st.write("**Schedule Detail**")
        w_sum = 0
        for idx, s in enumerate(steps):
            w_sum += s["water"]
            if current_idx > idx: icon, color = "✅", "#555555"
            elif current_idx == idx: icon, color = "🟧", "#ffffff"
            else: icon, color = "○", "#888888"
            st.markdown(f'<div class="step-card-mini" style="color: {color};">{icon} {idx+1}. {s["action"]} <span style="float:right;">{s["duration"]}s | {w_sum}g</span></div>', unsafe_allow_html=True)

draw_schedule(st.session_state.current_step)

# --- 6. タイマー実行ロジック ---
if st.session_state.running:
    steps = recipe["steps"]
    total_steps = len(steps)
    prev_cumulative_water = 0
    current_cumulative_water = 0
    
    COUNTDOWN_SOUND = "Countdown03-3.mp3"
    FINISH_SOUND = "Water_Drop02-1(Low-Reverb).mp3"

    # --- 心の余裕時間 (3秒) ---
    PREP_TIME = 3
    st.session_state.current_step = -2
    draw_schedule(-2)
    
    for s in range(PREP_TIME, 0, -1):
        if not st.session_state.running: break
        with timer_area.container():
            st.markdown('<div class="cumulative-display">READY...</div>', unsafe_allow_html=True)
            st.markdown('<div class="op-title">GET SET</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="timer-display" style="color: #d4a373;">{s:02d}</div>', unsafe_allow_html=True)
            st.progress(1.0)
        time.sleep(1)

    # --- メイン抽出工程 ---
    start_time = time.time()
    for i, step in enumerate(steps):
        if not st.session_state.running: break
        st.session_state.current_step = i
        draw_schedule(i)
        
        current_cumulative_water += step["water"]
        duration = step["duration"]
        
        for s in range(duration, 0, -1):
            if not st.session_state.running: break
            if s == 5 and i < total_steps - 1:
                play_sound_js(COUNTDOWN_SOUND)
            
            elapsed_total = int(time.time() - start_time)
            mins, secs = divmod(elapsed_total, 60)
            step_progress = (duration - s) / duration if duration > 0 else 1.0
            
            with timer_area.container():
                st.markdown(f'<div class="cumulative-display">TOTAL {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="op-title">{step["action"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="timer-display">{s:02d}</div>', unsafe_allow_html=True)
                st.progress(step_progress)
                
                st.markdown(f"""
                    <div class="weight-container">
                        <span class="prev-weight">{prev_cumulative_water}g</span>
                        <span class="arrow">→</span>
                        <span class="target-weight">{current_cumulative_water}g</span>
                        <span class="add-weight">(+{step['water']}g)</span>
                    </div>
                """, unsafe_allow_html=True)
            
            time.sleep(1)
        
        prev_cumulative_water = current_cumulative_water
            
    if st.session_state.running:
        st.session_state.current_step = len(steps)
        # draw_schedule(st.session_state.current_step)
        play_sound_js(FINISH_SOUND)
        
        positive_words = [
            "Happy", "Lucky", "Smile", "Relax", "Awesome", "Great", "Enjoy", 
            "Peace", "Love", "Shine", "Sweet", "Fun", "Good", "Nice", "Cool"
        ]
        random_word = random.choice(positive_words)
        finish_message = f"BREW FINISHED! ✨ {random_word} ✨"
        
        timer_area.success(finish_message)
        time.sleep(7)
        st.session_state.running = False
        st.rerun()
else:
    with timer_area.container():
        st.markdown('<div class="timer-display" style="color:#222;">00</div>', unsafe_allow_html=True)
        st.info("Ready to brew")

st.write("---")
recipe_url = recipe.get('url')
if recipe_url and recipe_url.strip() != "":
    link_html = f'REFERRENCE LINK <a href="{recipe_url}" target="_blank" rel="noopener noreferrer">{recipe_url}</a>'
    st.markdown(f'<div style="font-size: 0.9rem; color: #d4a373; margin-bottom: 17px;">{link_html}</div>', unsafe_allow_html=True)

st.caption("©2026 [やっぱり猫が大好き](https://note.com/otz5099/) | Sound by [OtoLogic](https://otologic.jp/) (CC BY 4.0)")
st.caption("[AI Recipe Generator](https://gemini.google.com/gem/1xwL8d-56B3SF-KxoIm--vC6wKjSM542i?usp=sharing)")