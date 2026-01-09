import streamlit as st

# Title of App
st.title("Web Development Lab03")

# Assignment Data 
# TODO: Fill out your team number, section, and team members
@st.cache_resource
def init_llm():
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-pro")

st.subheader("Sneh Patel and Sanyam Mittal")


# Introduction
# TODO: Write a quick description for all of your pages in this lab below, in the form:
#       1. **Page Name**: Description
#       2. **Page Name**: Description
#       3. **Page Name**: Description
#       4. **Page Name**: Description

st.write("""
Welcome to our Streamlit Web Development Lab03 app! You can navigate between the pages using the sidebar to the left. The following pages are:

1. 👾 The Video Game Index: Explore and add to a game ratings comparison chart with interactive filters. Search for any game to view detailed information and add it to the chart. Then play Higher or Lower to test your knowledge of video game ratings!
2. 🕹️ The Game Recommender: Are you a gaming lover but don't know what to play next? Don't fret, Sneh and Sunny's awesome new AI-powered game recommender is for you. Simply select a few games you enjoy along with a few genres and our advanced LLM will analyze your information and select 3 games it thinks you'll love!
3. 💬 The Master Gaming Guide: Are you stuck in a game and need Sneh and Sunny's help? Our expert gaming guide chatbot can help you overcome challenges, solve puzzles, and progress through difficult sections of video games with detailed strategies and tips.

""")

