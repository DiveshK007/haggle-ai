import streamlit as st
import pandas as pd
from datetime import datetime
import json

from agent import NegotiationAgent
from db import Database

# Page config
st.set_page_config(
    page_title="Haggle.ai - Autonomous Negotiation Agent",
    page_icon="💰",
    layout="wide"
)

# Initialize database and agent
@st.cache_resource
def init_resources():
    db = Database()
    agent = NegotiationAgent()
    return db, agent

db, agent = init_resources()

# Main UI
st.title("💰 Haggle.ai")
st.subtitle("Your AI-Powered Negotiation Assistant")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page:", ["Negotiate", "Dashboard", "Settings"])

if page == "Negotiate":
    st.header("🤝 Start Negotiation")
    
    # Input section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Vendor Communication")
        vendor_message = st.text_area(
            "Paste vendor email/message:",
            placeholder="e.g., 'Hi John, Your annual subscription renewal is due at $6,000 for the next year. Please confirm by Friday.'",
            height=120
        )
        
        # Context inputs
        st.subheader("Negotiation Context")
        past_price = st.number_input("Previous/Current Price ($)", min_value=0, value=500, step=50)
        target_price = st.number_input("Target Price ($)", min_value=0, value=400, step=50)
        
        service_type = st.selectbox(
            "Service Type:",
            ["SaaS Subscription", "Cloud Services", "Marketing Services", "Consulting", "Other"]
        )
        
        relationship = st.selectbox(
            "Relationship Length:",
            ["New Customer", "< 1 Year", "1-3 Years", "3+ Years", "Long-term Partner"]
        )
    
    with col2:
        st.subheader("Quick Stats")
        if past_price > 0 and target_price > 0:
            savings_target = past_price - target_price
            savings_percent = (savings_target / past_price) * 100
            
            st.metric("Target Savings", f"${savings_target:,.0f}", f"{savings_percent:.1f}%")
            st.metric("Annual Impact", f"${savings_target * 12:,.0f}")
    
    # Generate proposals
    if st.button("🎯 Generate Counter-Offers", type="primary"):
        if vendor_message.strip():
            with st.spinner("AI is crafting your counter-offers..."):
                try:
                    context = {
                        "vendor_message": vendor_message,
                        "past_price": past_price,
                        "target_price": target_price,
                        "service_type": service_type,
                        "relationship": relationship
                    }
                    
                    proposals = agent.generate_proposals(context)
                    
                    # Store in session state
                    st.session_state.proposals = proposals
                    st.session_state.context = context
                    
                except Exception as e:
                    st.error(f"Error generating proposals: {str(e)}")
        else:
            st.error("Please enter a vendor message to analyze.")
    
    # Display proposals if available
    if 'proposals' in st.session_state:
        st.header("📝 AI-Generated Counter-Offers")
        
        proposals = st.session_state.proposals
        
        # Create tabs for different strategies
        tab1, tab2, tab3 = st.tabs(["🤝 Polite Approach", "💪 Firm Approach", "🔄 Term Swap"])
        
        with tab1:
            st.subheader("Polite & Collaborative")
            st.write(proposals["polite"]["content"])
            st.info(f"**Strategy:** {proposals['polite']['reasoning']}")
            
            if st.button("📧 Use Polite Approach", key="polite"):
                st.session_state.selected_proposal = proposals["polite"]
                st.session_state.selected_strategy = "polite"
        
        with tab2:
            st.subheader("Firm & Direct")
            st.write(proposals["firm"]["content"])
            st.info(f"**Strategy:** {proposals['firm']['reasoning']}")
            
            if st.button("📧 Use Firm Approach", key="firm"):
                st.session_state.selected_proposal = proposals["firm"]
                st.session_state.selected_strategy = "firm"
        
        with tab3:
            st.subheader("Alternative Terms")
            st.write(proposals["term_swap"]["content"])
            st.info(f"**Strategy:** {proposals['term_swap']['reasoning']}")
            
            if st.button("📧 Use Term Swap", key="term_swap"):
                st.session_state.selected_proposal = proposals["term_swap"]
                st.session_state.selected_strategy = "term_swap"
    
    # Simulate vendor response
    if 'selected_proposal' in st.session_state:
        st.header("🎭 Vendor Response Simulation")
        st.success(f"**Selected Strategy:** {st.session_state.selected_strategy.title()}")
        
        if st.button("🎲 Simulate Vendor Reply", type="secondary"):
            with st.spinner("Simulating vendor response..."):
                try:
                    response = agent.simulate_vendor_response(
                        st.session_state.context,
                        st.session_state.selected_proposal
                    )
                    
                    st.session_state.vendor_response = response
                    
                except Exception as e:
                    st.error(f"Error simulating response: {str(e)}")
        
        # Show simulated response and save results
        if 'vendor_response' in st.session_state:
            response = st.session_state.vendor_response
            
            st.subheader("📬 Simulated Vendor Reply")
            st.write(response["content"])
            
            # Show outcome
            if response["accepted_price"]:
                original_price = st.session_state.context["past_price"]
                final_price = response["accepted_price"]
                savings = original_price - final_price
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Original Price", f"${original_price:,.0f}")
                with col2:
                    st.metric("Final Price", f"${final_price:,.0f}")
                with col3:
                    st.metric("Savings", f"${savings:,.0f}", f"${savings * 12:,.0f}/year")
                
                # Save to database
                if st.button("💾 Save Negotiation Results", type="primary"):
                    negotiation_data = {
                        "date": datetime.now(),
                        "service_type": st.session_state.context["service_type"],
                        "original_price": original_price,
                        "final_price": final_price,
                        "savings": savings,
                        "annual_savings": savings * 12,
                        "strategy": st.session_state.selected_strategy,
                        "vendor_message": st.session_state.context["vendor_message"][:200] + "..."
                    }
                    
                    db.save_negotiation(negotiation_data)
                    st.success("✅ Negotiation saved to database!")
                    
                    # Clear session state
                    for key in ['proposals', 'context', 'selected_proposal', 'selected_strategy', 'vendor_response']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.rerun()

elif page == "Dashboard":
    st.header("📊 Savings Dashboard")
    
    # Get saved negotiations
    negotiations = db.get_all_negotiations()
    
    if negotiations:
        df = pd.DataFrame(negotiations)
        
        # Key metrics
        total_savings = df['annual_savings'].sum()
        total_negotiations = len(df)
        avg_savings = df['savings'].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Annual Savings", f"${total_savings:,.0f}")
        with col2:
            st.metric("Negotiations", total_negotiations)
        with col3:
            st.metric("Avg. Savings Per Deal", f"${avg_savings:,.0f}")
        with col4:
            success_rate = (df['final_price'] < df['original_price']).mean() * 100
            st.metric("Success Rate", f"{success_rate:.0f}%")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Savings by Service Type")
            service_savings = df.groupby('service_type')['annual_savings'].sum().sort_values(ascending=True)
            st.bar_chart(service_savings)
        
        with col2:
            st.subheader("Strategy Performance")
            strategy_performance = df.groupby('strategy').agg({
                'savings': 'mean',
                'annual_savings': 'sum'
            }).round(0)
            st.dataframe(strategy_performance)
        
        # Recent negotiations table
        st.subheader("Recent Negotiations")
        display_df = df[['date', 'service_type', 'original_price', 'final_price', 'savings', 'strategy']].copy()
        display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
        display_df = display_df.sort_values('date', ascending=False)
        
        st.dataframe(display_df, use_container_width=True)
        
        # Export functionality
        if st.button("📁 Export to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"haggle_ai_savings_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    else:
        st.info("No negotiations saved yet. Start your first negotiation to see results here!")

elif page == "Settings":
    st.header("⚙️ Settings")
    
    # LLM Engine status
    st.subheader("AI Engine Status")
    
    try:
        engine_info = agent.get_engine_info()
        
        if engine_info["engine"] == "ollama":
            st.success(f"✅ Using Ollama with model: {engine_info['model']}")
        else:
            st.success(f"✅ Using OpenAI with model: {engine_info['model']}")
            
    except Exception as e:
        st.error(f"❌ Engine Error: {str(e)}")
        st.info("Check your .env configuration and ensure the selected AI service is running.")
    
    # Database info
    st.subheader("Database")
    negotiation_count = len(db.get_all_negotiations())
    st.info(f"📁 {negotiation_count} negotiations stored in local database")
    
    if st.button("🗑️ Clear All Data", type="secondary"):
        if st.checkbox("I understand this will delete all saved negotiations"):
            db.clear_all_data()
            st.success("All data cleared!")
            st.rerun()
    
    # Configuration tips
    st.subheader("Configuration")
    st.markdown("""
    **To switch AI engines:**
    1. Edit your `.env` file
    2. Change `ENGINE=ollama` to `ENGINE=openai` (or vice versa)
    3. Restart the app
    
    **For OpenAI:** Set your `OPENAI_API_KEY` in `.env`
    **For Ollama:** Ensure Ollama is running locally with `ollama serve`
    """)

# Footer
st.markdown("---")
st.markdown("Built for the OpenAI Open Model Hackathon 🚀 | Powered by AI negotiation strategies")
