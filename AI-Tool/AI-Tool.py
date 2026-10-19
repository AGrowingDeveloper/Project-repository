import streamlit as st
import os
from openai import OpenAI
from datetime import datetime

from app_utils import auth
from app_utils import database as db


st.set_page_config(
    page_title="AI_智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'About': "# 这是一个基于streamlit开发的ai智能助手!"}
)

# ============ 路由状态初始化 ============
if "page" not in st.session_state:
    st.session_state.page = "login"
if "user" not in st.session_state:
    st.session_state.user = None

def navigate(page):
    st.session_state.page = page
    st.rerun()

def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def get_ai_client():
    settings = db.get_settings(st.session_state.user["id"])
    api_key = settings.get("api_key") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None, None
    client = OpenAI(api_key=api_key, base_url=settings.get("base_url", "https://api.deepseek.com"))
    return client, settings

SYSTEM_PROMPT_TEMPLATE = """
        你叫 %s，现在是用户的真实助手，请完全代入助手角色。
        规则：
            1.每次只回复1条消息
            2.禁止任何场景或状态描述性文字
            3.匹配用户的语言
            4.回复简短，像微信聊天一样
            5.有需要的话可以使用emoji表情
            6.用符合助手性格的方式说话
            7.回复的内容，要充分体现助手的性格特征
        助手性格：
            - %s
        你必须严格遵守上述规则来回复用户
"""

# ============ 登录页 ============
def render_login():
    st.title("🤖 AI 智能助手")
    st.markdown("### 欢迎使用，请登录或注册")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            with st.form("login_form"):
                username = st.text_input("用户名", placeholder="请输入用户名")
                password = st.text_input("密码", type="password", placeholder="请输入密码")
                submit = st.form_submit_button("登录", use_container_width=True)
                if submit:
                    user = auth.login(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.page = "home"
                        st.rerun()
                    else:
                        st.error("用户名或密码错误！")

        with tab2:
            with st.form("register_form"):
                username = st.text_input("用户名", placeholder="3-20个字符")
                password = st.text_input("密码", type="password", placeholder="至少6位")
                password2 = st.text_input("确认密码", type="password", placeholder="再次输入密码")
                submit = st.form_submit_button("注册", use_container_width=True)
                if submit:
                    if not username or len(username) < 3:
                        st.error("用户名至少3个字符！")
                    elif password != password2:
                        st.error("两次密码不一致！")
                    elif len(password) < 6:
                        st.error("密码至少6位！")
                    else:
                        user = auth.register(username, password)
                        if user:
                            st.success("注册成功！正在进入...")
                            st.session_state.user = user
                            st.session_state.page = "home"
                            st.rerun()
                        else:
                            st.error("用户名已存在！")

    st.markdown("---")
    st.caption("💡 新用户请先注册，数据保存在本地 SQLite 数据库中")

# ============ 首页 ============
def render_home():
    user = st.session_state.user
    st.title(f"👋 欢迎回来，{user['username']}！")
    st.markdown("---")

    stats = db.get_stats(user["id"])
    settings = db.get_settings(user["id"]) or {}
    api_ok = bool(settings.get("api_key") or os.environ.get("DEEPSEEK_API_KEY"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总会话数", stats["sessions"])
    with col2:
        st.metric("总消息数", stats["messages"])
    with col3:
        st.metric("API 状态", "✅ 已配置" if api_ok else "❌ 未配置")

    st.markdown("---")
    st.subheader("🚀 快速开始")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💬 开始新对话", use_container_width=True, type="primary"):
            st.session_state.pop("current_session_id", None)
            st.session_state.pop("messages", None)
            navigate("chat")
    with c2:
        if st.button("⚙️ 配置 API Key", use_container_width=True):
            navigate("settings")
    with c3:
        if st.button("📚 会话历史", use_container_width=True):
            navigate("chat")

    st.markdown("---")
    st.subheader("✨ 功能介绍")
    st.markdown("""
    - **🎭 自定义人设**：自由设定助手昵称与性格
    - **💾 多会话管理**：新建、切换、删除会话
    - **⚡ 流式输出**：逐字显示，模拟实时打字
    - **🔒 私有数据**：每用户数据独立存储
    - **🔑 自主配置**：设置页配置 API Key 与模型参数
    """)

# ============ 通用侧边栏 ============
def render_sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        st.divider()
        if st.button("🏠 首页", use_container_width=True):
            navigate("home")
        if st.button("💬 对话", use_container_width=True):
            navigate("chat")
        if st.button("⚙️ 设置", use_container_width=True):
            navigate("settings")
        st.divider()
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "login"
            st.session_state.pop("current_session_id", None)
            st.session_state.pop("messages", None)
            st.rerun()

# ============ 聊天页 ============
def render_chat():
    user = st.session_state.user

    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "name" not in st.session_state:
        st.session_state.name = "小帅"
    if "character" not in st.session_state:
        st.session_state.character = "幽默风趣，活泼，大方的北京男孩"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("💬 AI 智能助手")

    current_id = st.session_state.current_session_id
    if current_id:
        session = db.get_session(current_id)
        if session:
            st.text(f"对话名称：{session['name']}")

    for message in st.session_state.messages:
        st.chat_message(message["role"]).write(message["content"])

    # 侧边栏
    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        st.divider()
        if st.button("🏠 首页", use_container_width=True):
            navigate("home")
        if st.button("⚙️ 设置", use_container_width=True):
            navigate("settings")
        st.divider()
        st.subheader("AI 控制面板")

        if st.button("📑 新建会话", use_container_width=True):
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.session_state.name = "小帅"
            st.session_state.character = "幽默风趣，活泼，大方的北京男孩"
            st.rerun()

        st.text("会话历史")
        sessions = db.list_sessions(user["id"])
        for s in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(s["name"], width="stretch", icon="📄", key=f"load_{s['id']}",
                             type="primary" if s["id"] == current_id else "secondary"):
                    msgs = db.list_messages(s["id"])
                    st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in msgs]
                    st.session_state.name = s.get("assistant_name") or "小帅"
                    st.session_state.character = s.get("character") or "幽默风趣，活泼，大方的北京男孩"
                    st.session_state.current_session_id = s["id"]
                    st.rerun()
            with col2:
                if st.button("", width="stretch", icon="❌", key=f"del_{s['id']}"):
                    db.delete_session(s["id"])
                    if s["id"] == current_id:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                    st.rerun()

        st.divider()
        st.subheader("助手信息")
        name = st.text_input("助手昵称：", placeholder="请输入助手昵称", value=st.session_state.name)
        if name:
            st.session_state.name = name
        character = st.text_area("助手性格：", placeholder="请输入助手性格", value=st.session_state.character)
        if character:
            st.session_state.character = character

        st.divider()
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "login"
            st.session_state.pop("current_session_id", None)
            st.session_state.pop("messages", None)
            st.rerun()

    # 对话框
    prompt = st.chat_input("⌨️请输入您的问题...")
    if prompt:
        client, settings = get_ai_client()
        if not client:
            st.error("请先在【设置】中配置 API Key，或设置 DEEPSEEK_API_KEY 环境变量！")
        else:
            if not current_id:
                current_id = db.create_session(
                    user["id"], generate_session_name(),
                    st.session_state.name, st.session_state.character
                )
                st.session_state.current_session_id = current_id

            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            db.add_message(current_id, "user", prompt)

            try:
                response = client.chat.completions.create(
                    model=settings.get("model", "deepseek-chat"),
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE % (st.session_state.name, st.session_state.character)},
                        *st.session_state.messages
                    ],
                    stream=True,
                    temperature=settings.get("temperature", 0.7),
                    max_tokens=settings.get("max_tokens", 2048),
                )
                response_message = st.empty()
                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        response_message.chat_message("assistant").write(full_response)

                st.session_state.messages.append({"role": "assistant", "content": full_response})
                db.add_message(current_id, "assistant", full_response)
            except Exception as e:
                st.error(f"调用大模型失败！{e}")

# ============ 设置页 ============
def render_settings():
    user = st.session_state.user
    st.title("⚙️ 设置中心")

    settings = db.get_settings(user["id"]) or {}

    with st.form("settings_form"):
        st.subheader("🔑 API 配置")
        api_key = st.text_input(
            "API Key",
            value=settings.get("api_key", "") or "",
            type="password",
            placeholder="sk-... 留空则使用环境变量 DEEPSEEK_API_KEY"
        )
        base_url = st.text_input(
            "API Base URL",
            value=settings.get("base_url", "https://api.deepseek.com"),
            placeholder="https://api.deepseek.com"
        )
        model = st.text_input(
            "模型名称",
            value=settings.get("model", "deepseek-chat"),
            placeholder="deepseek-chat / gpt-4o 等"
        )

        st.subheader("🎛️ 生成参数")
        col1, col2 = st.columns(2)
        with col1:
            temperature = st.slider("Temperature", 0.0, 2.0, float(settings.get("temperature", 0.7)), 0.1)
        with col2:
            max_tokens = st.number_input("Max Tokens", 1, 32768, int(settings.get("max_tokens", 2048)))

        submit = st.form_submit_button("💾 保存设置", use_container_width=True, type="primary")
        if submit:
            db.update_settings(
                user["id"],
                api_key=api_key if api_key else None,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            st.success("✅ 设置已保存！")

    render_sidebar()

# ============ 路由分发 ============
if st.session_state.user is None:
    st.session_state.page = "login"

page = st.session_state.page

if page == "login":
    render_login()
elif page == "home":
    render_sidebar()
    render_home()
elif page == "chat":
    render_chat()
elif page == "settings":
    render_settings()
else:
    render_home()