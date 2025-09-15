try:
    from whisper import Whisper
except ImportError as e:
    raise ImportError("Whisper library not found. Please install it.") from e

import os
import streamlit as st
from dotenv import load_dotenv
from services.email import GmailClient
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import pandas as pd
from datetime import datetime
import json

from agent import NegotiationAgent
from db import Database

# Load environment variables
load_dotenv()

# Modern UI Enhancements
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #4CAF50; /* Green */
        color: white;
        border: none;
        padding: 15px 32px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 12px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# Page config
st.set_page_config(
    page_title="Haggle.ai - Autonomous Negotiation Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a modern look
st.markdown("""
<style>
    /* General styles */
    .stApp {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #4A90E2;
    }
    .stButton>button {
        border: 2px solid #4A90E2;
        border-radius: 20px;
        color: #FFFFFF;
        background-color: transparent;
        padding: 10px 24px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #4A90E2;
        color: #1E1E1E;
    }
    .stSlider [data-baseweb="slider"] {
        color: #4A90E2;
    }
    /* Sidebar styles */
    .css-1d391kg {
        background-color: #2C2C2C;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database and agent
@st.cache_resource
def init_resources():
    db = Database()
    agent = NegotiationAgent()
    gmail_client = GmailClient()
    return db, agent, gmail_client

db, agent, gmail_client = init_resources()

# Main UI
st.title("💰 Haggle.ai")
st.subheader("Your AI-Powered Negotiation Assistant")
# Button to start negotiation
# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(" ", ["Negotiate", "Dashboard", "Settings"])

if page == "Negotiate":
    st.header("🚀 Start a New Negotiation")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Negotiation Parameters")
        product = st.text_input("Product/Service to Negotiate")
        initial_offer = st.number_input("Your Initial Offer ($)", min_value=0)

    with col2:
        st.subheader("Contact Information")
        recipient_email = st.text_input("Recipient's Email")
        your_name = st.text_input("Your Name")

    st.subheader("Negotiation Strategy")
    strategy = st.selectbox("Choose a strategy:", ["Assertive", "Cooperative", "Balanced"])

    if st.button("Initiate Negotiation"):
        if product and initial_offer and recipient_email and your_name:
            subject = f"Negotiation for {product}"
            body = f"Hi,\n\nMy name is {your_name} and I'm interested in {product}. My initial offer is ${initial_offer}.\n\nI'm looking forward to discussing this with you.\n\nBest,\n{your_name}"
            
            try:
                # We need the thread_id from the sent email to track replies
                sent_message = gmail_client.send_email(recipient_email, subject, body)
                thread_id = sent_message['threadId']
                
                # Save the initial thread to the database
                context = {
                    'product': product,
                    'initial_offer': initial_offer,
                    'recipient_email': recipient_email,
                    'your_name': your_name,
                    'strategy': strategy,
                    'history': [{'id': sent_message['id'], 'sender': 'me', 'body': body}]
                }
                db.save_negotiation_thread(thread_id, context)
                
                st.success(f"Negotiation for {product} initiated with {recipient_email}!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to send email: {e}")
        else:
            st.warning("Please fill in all the fields.")

    st.markdown("---")
    st.subheader("Ongoing Negotiations")
    
    # Placeholder for displaying active negotiation threads
    active_threads = db.get_all_negotiation_threads() # Assuming this method exists
    if active_threads:
        for thread in active_threads:
            with st.expander(f"Negotiation with {thread['recipient']}"):
                st.write(f"**Status:** {thread['status']}")
                
                # Display conversation history
                history = thread.get('context', {}).get('history', [])
                for msg in history:
                    st.text(f"{msg['sender']}: {msg['body']}")

                if st.button(f"Check for Reply", key=thread['id']):
                    try:
                        messages = gmail_client.check_for_replies(thread['thread_id'])
                        new_messages = [m for m in messages if m['id'] not in [h['id'] for h in history]]
                        
                        if new_messages:
                            for msg in new_messages:
                                sender = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'), 'Unknown')
                                body = base64.urlsafe_b64decode(msg['payload']['parts'][0]['body']['data']).decode('utf-8')
                                history.append({'id': msg['id'], 'sender': sender, 'body': body})
                            
                            thread['context']['history'] = history
                            db.save_negotiation_thread(thread['thread_id'], thread['context'])
                            st.success("New reply found!")
                            
                            proposals = agent.generate_proposals(thread['context'])
                            st.session_state[f'proposals_{thread["thread_id"]}'] = proposals
                            st.experimental_rerun()
                        else:
                            st.info("No new replies found.")
                    except Exception as e:
                        st.error(f"Failed to check for replies: {e}")

                if f'proposals_{thread["thread_id"]}' in st.session_state:
                    st.subheader("Agent's Suggested Replies")
                    proposals = st.session_state[f'proposals_{thread["thread_id"]}']
                    for strategy, proposal in proposals.items():
                        with st.expander(f"**{strategy.title()}** Strategy"):
                            st.write(f"**Reasoning:** {proposal['reasoning']}")
                            st.text_area("Suggested Reply", proposal['content'], height=150)
                            if st.button(f"Send {strategy.title()} Reply", key=f"send_{strategy}_{thread['thread_id']}"):
                                try:
                                    gmail_client.send_email(thread['context']['recipient_email'], f"Re: Negotiation for {thread['context']['product']}", proposal['content'])
                                    st.success("Reply sent!")
                                    del st.session_state[f'proposals_{thread["thread_id"]}']
                                    st.experimental_rerun()
                                except Exception as e:
                                    st.error(f"Failed to send reply: {e}")
    else:
        st.info("No active negotiations.")

elif page == "Dashboard":
    st.header("📊 Negotiation Dashboard")

    # Fetch data from the database
    funnel_data = db.get_funnel_analysis()
    strategy_data = db.get_strategy_performance()
    all_negotiations = db.get_all_negotiations()

    # Display KPIs
    total_savings = sum(n['savings'] for n in all_negotiations)
    successful_negotiations = sum(1 for n in all_negotiations if n['success'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Savings", f"${total_savings:,.2f}")
    col2.metric("Successful Negotiations", successful_negotiations)
    col3.metric("Success Rate", f"{(successful_negotiations / len(all_negotiations) * 100) if all_negotiations else 0:.1f}%")

    st.markdown("---")

    # Negotiation Funnel
    st.subheader("Negotiation Funnel")
    if funnel_data:
        funnel_df = pd.DataFrame(list(funnel_data.items()), columns=['Stage', 'Count']).sort_values('Count', ascending=False)
        st.bar_chart(funnel_df.set_index('Stage'))
    else:
        st.info("No negotiation events recorded yet.")

    # Strategy Performance
    st.subheader("Strategy Performance")
    if strategy_data:
        strategy_df = pd.DataFrame(strategy_data).T
        st.bar_chart(strategy_df[['success_rate', 'avg_savings']])
    else:
        st.info("No strategy performance data available.")

    # Savings Trendline
    st.subheader("Cumulative Savings Over Time")
    if all_negotiations:
        savings_df = pd.DataFrame(all_negotiations)
        savings_df['date'] = pd.to_datetime(savings_df['date'])
        savings_df = savings_df.sort_values('date')
        savings_df['cumulative_savings'] = savings_df['savings'].cumsum()
        st.line_chart(savings_df.set_index('date')['cumulative_savings'])
    else:
        st.info("No savings data to display.")

elif page == "Settings":
    st.header("⚙️ Settings")
    st.write("Configure your agent's settings here.")
    st.text_input("API Key")
    st.selectbox("Language Model", ["GPT-4", "Claude", "Gemini"])
