# app/utils/style.py
import streamlit as st


def apply_theme() -> None:
    """Inject global CSS theme. Call once per page after st.set_page_config()."""
    st.markdown(
        """
        <style>
            /* Main app background */
            .stApp {
                background: radial-gradient(circle at top left, #16214d 0%, #0a0f2d 50%, #000814 100%);
                color: #f1f5f9;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }

            /* Sidebar */
            [data-testid="stSidebar"] {
                background: #1a2b6d;
                border-right: 1px solid rgba(255, 255, 255, 0.15);
            }

            /* Sidebar hover highlight (all input containers) */
            [data-testid="stSidebar"] .stTextInput:hover,
            [data-testid="stSidebar"] .stNumberInput:hover,
            [data-testid="stSidebar"] .stSelectbox:hover {
                transition: 0.25s ease-in-out;
                filter: brightness(1.25);
                box-shadow: 0 0 10px #e63946aa;
                border-radius: 0.5rem;
            }

            /* Sidebar page navigation (Home, Map3D, etc.) */
            [data-testid="stSidebarNav"] a {
                color: #e2e8f0;
                text-decoration: none;
                padding: 6px 10px;
                border-radius: 6px;
                display: flex;              
                align-items: center;        
                gap: 0.4rem;                
                font-size: 0.95rem;
                line-height: 1.2;
            }

            [data-testid="stSidebarNav"] a:hover {
                color: #e63946 !important;  /* red text */
                background-color: rgba(230, 57, 70, 0.18) !important;
                font-weight: 600;
                transition: all 0.18s ease-in-out;
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                color: #e63946 !important;
                background-color: rgba(230, 57, 70, 0.28) !important;
                font-weight: 700;
            }

            /* Sidebar Headers */
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3 {
                color: #e2e8f0 !important;
            }

            /* Labels */
            label, .stTextInput label, .stNumberInput label {
                font-weight: 500 !important;
                color: #e2e8f0 !important;
            }

            /* Input fields */
            .stTextInput > div > div > input,
            .stNumberInput input {
                background-color: #12204a !important;
                color: #f1f5f9 !important;
                border-radius: 0.5rem !important;
                border: 1px solid rgba(255, 255, 255, 0.25) !important;
            }

            /* Focus accent color (RED) */
            .stTextInput > div > div > input:focus,
            .stNumberInput input:focus {
                border: 1px solid #e63946 !important;
                box-shadow: 0 0 0 1px #e63946aa !important;
            }

            /* Buttons */
            .stButton>button {
                background: linear-gradient(135deg, #e63946, #b81f2d);
                color: white;
                border-radius: 999px;
                border: none;
                font-weight: 600;
                padding: 0.45rem 1.3rem;
            }
            .stButton>button:hover {
                filter: brightness(1.1);
                box-shadow: 0px 10px 25px rgba(230, 57, 70, 0.45);
            }

            /* DataFrame container */
            .stDataFrame {
                background-color: #0a0f2d !important;
                border-radius: 0.75rem !important;
                padding: 0.25rem;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }

            /* Title styling */
            .app-title {
                font-size: 2.4rem;
                font-weight: 700;
                background: linear-gradient(135deg, #e63946, #ff9f9f);
                -webkit-background-clip: text;
                color: transparent;
                margin-bottom: 0.1rem;
            }

            /* Subtitle */
            .app-subtitle {
                font-size: 0.95rem;
                color: #cbd5e1;
            }

            /* Section titles */
            .section-title {
                font-size: 1.25rem;
                font-weight: 600;
                margin-bottom: 0.4rem;
                color: #e2e8f0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
