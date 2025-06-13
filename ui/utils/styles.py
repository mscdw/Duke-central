import streamlit as st

def apply_global_styles():
    st.markdown("""
        <style>
        /* Global Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 14px;
        }
        </style>
    """, unsafe_allow_html=True)
