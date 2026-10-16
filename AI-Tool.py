import streamlit as st
import os
from openai import OpenAI
from datetime import datetime
import json

# 自动创建会话存储文件夹
if not os.path.exists("sessions"):
    os.mkdir("sessions")

#设置页面配置项
st.set_page_config(
    #页面标题
    page_title="AI_智能伴侣",
    page_icon="🤖",
    #页面布局
    layout="wide",
    #侧边栏状态
    initial_sidebar_state="expanded",
    menu_items={'About': "# 这是一个基于streamlit开发的ai智能伴侣!"}
)

#保存对话信息函数
def save_session():
    if st.session_state.current_session:
        #构建完整会话对象，包含name、character、messages
        session_data = {
            "name": st.session_state.name,
            "character": st.session_state.character,
            "current_session": st.session_state.current_session,
            "messages": st.session_state.messages
        }
        # 将完整session_data写入文件
        with open(f"sessions/{st.session_state.current_session}.json", "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

# 加载所有的会话列表信息
def load_sessions():
    session_list = []
    if os.path.exists("sessions"):
        file_list = os.listdir("sessions")
        for filename in file_list:
            if filename.endswith(".json"):
                session_list.append(filename[:-5])
    session_list.sort(reverse=True) # 排序, 降序排列
    return session_list

# 加载指定的会话信息
def load_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.messages = session_data["messages"]
                st.session_state.name = session_data["name"]
                st.session_state.character = session_data["character"]
                st.session_state.current_session = session_name
                st.rerun()
    except Exception as e:
        st.error(f"加载会话失败! 错误:{e}")

# 删除会话信息函数
def delete_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            os.remove(f"sessions/{session_name}.json")
            # 如果删除的是当前会话, 重置对话
            if session_name == st.session_state.current_session:
                st.session_state.messages = []
                st.session_state.current_session = generate_session_name()
                st.rerun()
    except Exception as e:
        st.error(f"删除会话失败! 错误:{e}")

#生成对话标识
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

#页面大标题
st.title("💬AI智能伴侣💬")

#logo，部分streamlit版本不支持表情，可替换图片
st.logo("♥️")

#系统提示词【修复文字笔误：真是 → 真实】
system_prompt = """
        你叫 %s，现在是用户的真实伴侣，请完全代入伴侣角色。：
        规则：
            1.每次只回复1条消息
            2.禁止任何场景或状态描述性文字
            3.匹配用户的语言
            4.回复简短，像微信聊天一样
            5.有需要的话可以使用emoji表情
            6.用符合伴侣性格的方式说话
            7.回复的内容，要充分体现伴侣的性格特征
        伴侣性格：
            - %s
        你必须严格遵守上述规则来回复用户
"""

#初始化session状态
if "messages" not in st.session_state:
    st.session_state.messages = []
#昵称
if "name" not in st.session_state:
    st.session_state.name = "小帅"
#性格
if "character" not in st.session_state:
    st.session_state.character = "幽默风趣，活泼，大方的北京男孩"
#会话名称
if "current_session" not in st.session_state:
    st.session_state.current_session = generate_session_name()

#遍历聊天记录
st.text(f"对话名称：{st.session_state.current_session}")
for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

# 校验API KEY
api_key = os.environ.get('DEEPSEEK_API_KEY')
if not api_key:
    st.warning("⚠️ 未检测到DEEPSEEK_API_KEY环境变量，请配置后再使用对话功能！")
else:
    # 创建与ai大模型交互的客户端对象
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

#左侧侧边栏
with st.sidebar:
    #会话信息
    st.subheader("AI控制面板")

    #新建会话按钮
    if st.button("新建会话",icon="📑",width="stretch"):
        # 先保存当前对话
        save_session()
        # 创建新的对话
        st.session_state.messages = []
        st.session_state.current_session = generate_session_name()
        st.rerun()  # 重新运行当前页面

    # 会话历史
    st.text("会话历史")
    session_list = load_sessions()
    for session in session_list:
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(session, width="stretch", icon="📄", key=f"load_{session}",
                type="primary" if session == st.session_state.current_session else "secondary"):
                load_session(session)
        with col2:
            if st.button("", width="stretch", icon="❌️", key=f"delete_{session}"):
                delete_session(session)
        st.divider()

    #伴侣信息
    st.subheader("这是您的伴侣信息")
    #输入伴侣昵称
    name = st.text_input("您的伴侣昵称：",placeholder="请输入您的伴侣昵称",value=st.session_state.name)
    if name:
        st.session_state.name = name
    #性格输入框
    character = st.text_area("您的伴侣性格：",placeholder="请输入您的伴侣性格",value=st.session_state.character)
    if character:
        st.session_state.character = character

#对话框
prompt = st.chat_input("⌨️请输入您的问题...")
if prompt:
    #判断api密钥是否存在
    if not os.environ.get('DEEPSEEK_API_KEY'):
        st.error("请先配置DEEPSEEK_API_KEY环境变量！")
    else:
        #显示用户输入
        st.chat_message("user").write(prompt)
        print("-------------> 调用ai大模型，提示词：",prompt)
        #保存用户输入的提示词
        st.session_state.messages.append({"role": "user", "content": prompt})

        #调用ai大模型
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt % (st.session_state.name,st.session_state.character)},
                    *st.session_state.messages
                ],
                stream=True,
            )
            #流式输出
            response_message = st.empty()
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    response_message.chat_message("assistant").write(full_response)

            #保存AI返回消息
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            #保存会话信息
            save_session()
        except Exception as e:
            st.error(f"调用大模型失败！{e}")
