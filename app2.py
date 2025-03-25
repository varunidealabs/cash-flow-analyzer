import streamlit as st
import pandas as pd
import os
import tempfile
import base64
from datetime import datetime
import plotly.express as px
import numpy as np
import time
import json

# Import our custom modules
from pdf_extractor import GPTBankStatementExtractor
from cash_flow_analyzer import CashFlowAnalyzer
from financial_insights import FinancialInsightsGenerator

# Set page config
st.set_page_config(
    page_title="Cash Flow Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("Cash Flow Analyzer")
st.markdown("""
    **Transform your bank statements into clear visual reports with just one upload.**
    Automatically categorize transactions and see simple charts of income and expenses.
""")

# Session state initialization
if 'transactions_df' not in st.session_state:
    st.session_state.transactions_df = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = None
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("AZURE_OPENAI_KEY", "")
if 'financial_insights' not in st.session_state:
    st.session_state.financial_insights = None


# Main app workflow
if not st.session_state.file_processed:
    # File upload section
    st.header("Upload Your Bank Statement")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    #dummy statement

    if st.button("Test with dummy data"):
        uploaded_file = "dummy_statement.pdf"
          

    if uploaded_file is not None:
        # Validate API key is present
        if not st.session_state.api_key:
            st.error("Please enter your Azure OpenAI API key")
        else:
            # Process the uploaded file
            with st.spinner("Extracting transactions from your bank statement... This may take a minute."):
                try:
                    # Initialize the extractor with API key
                    extractor = GPTBankStatementExtractor(
                        api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                        api_key=st.session_state.api_key
                    )
                    
                    # Extract transactions
                    transactions_df = extractor.extract_transactions(uploaded_file)
                    
                    if transactions_df is not None and not transactions_df.empty:
                        st.session_state.transactions_df = transactions_df
                        
                        # Initialize analyzer and perform analysis
                        analyzer = CashFlowAnalyzer()
                        analyzer.load_data(transactions_df)
                        analyzer.preprocess_data()
                        analyzer.analyze_cash_flow()
                        
                        st.session_state.analyzer = analyzer
                        st.session_state.analysis_results = analyzer.analysis_results
                        
                        # Generate financial insights
                        with st.spinner("Generating personalized financial insights..."):
                            insights_generator = FinancialInsightsGenerator(
                                api_key=st.session_state.api_key,
                                api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
                            )
                            insights = insights_generator.generate_financial_summary(
                                transactions_df,
                                analyzer.analysis_results
                            )
                            st.session_state.financial_insights = insights
                        
                        st.session_state.file_processed = True
                        
                        st.success(f"Successfully extracted {len(transactions_df)} transactions!")
                        st.rerun()
                    else:
                        st.error("No transactions were found in the uploaded statement. Please try another file.")
                
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
                    st.exception(e)
                    
else:
    # Display analysis results
    
    # Get data from session state
    transactions_df = st.session_state.transactions_df
    analysis_results = st.session_state.analysis_results
    analyzer = st.session_state.analyzer
    financial_insights = st.session_state.financial_insights
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Summary", "Financial Insights", "Transactions"])
    
    with tab1:
        st.header("Financial Summary")
        
        # Summary statistics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Income", f"₹{analysis_results['summary']['total_income']:,.2f}")
            st.metric("Total Expenses", f"₹{analysis_results['summary']['total_expenses']:,.2f}")
            st.metric("Net Cash Flow", f"₹{analysis_results['summary']['net_flow']:,.2f}", 
                     delta=f"₹{analysis_results['summary']['net_flow']:,.2f}")
        
        with col2:
            st.metric("Avg. Monthly Income", f"₹{analysis_results['summary']['avg_monthly_income']:,.2f}")
            st.metric("Avg. Monthly Expenses", f"₹{analysis_results['summary']['avg_monthly_expenses']:,.2f}")
            st.metric("Avg. Savings Rate", f"{analysis_results['summary']['avg_savings_rate']:.1f}%")
        
        with col3:
            st.metric("Top Expense Category", analysis_results['summary']['top_expense_category'])
            st.metric("Top Expense Amount", f"₹{analysis_results['summary']['top_expense_amount']:,.2f}")
            st.metric("Transaction Count", analysis_results['summary']['transaction_count'])
        
        # Date range information
        st.markdown(f"""
        <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; border: 1px solid #d1e7dd;">
            <h4 style="color: #0d6efd; margin: 0;">Analysis Period</h4>
            <p style="margin: 0; font-size: 16px; color: #212529;">{analysis_results['summary']['date_range']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Dashboard overview charts
        st.subheader("Financial Insights Dashboard")
        
        # Side-by-side charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(analyzer.generate_monthly_cash_flow_chart(), use_container_width=True)
        
        with col2:
            st.plotly_chart(analyzer.generate_spending_breakdown_chart(), use_container_width=True)

    with tab2:
        st.header(" Personalized Financial Insights")
        
        # Financial health score with gauge
        health_score = financial_insights.get('health_score', 50)
        
        # Create three columns for the health score visualization
        score_col1, score_col2, score_col3 = st.columns([1, 2, 1])
        
        with score_col2:
            # Display health score with custom HTML/CSS
            health_color = "#28a745" if health_score >= 70 else "#ffc107" if health_score >= 40 else "#dc3545"
            
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="margin-bottom: 5px;">Your Financial Health Score</h3>
                <div style="width: 150px; height: 150px; border-radius: 50%; background: conic-gradient({health_color} {health_score}%, #e9ecef {health_score}%); margin: 0 auto; display: flex; align-items: center; justify-content: center;">
                    <div style="width: 120px; height: 120px; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center;">
                        <span style="font-size: 32px; font-weight: bold; color: {health_color};">{health_score}</span>
                    </div>
                </div>
                <p style="margin-top: 10px; font-size: 16px;">
                    {
                    "Excellent financial health! Keep it up!" if health_score >= 80 else
                    "Good financial standing with room for improvement." if health_score >= 60 else
                    "Average financial health. Consider the tips below." if health_score >= 40 else
                    "Financial warning signs. Action recommended." if health_score >= 20 else
                    "Immediate financial attention needed."
                    }
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display personalized summary
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #0d6efd;">Financial Summary</h3>
            <p style="font-size: 18px; line-height: 1.6;">{financial_insights.get('summary', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display savings tips
        st.markdown("""
        <h3 style="margin-bottom: 15px; color: #0d6efd;"> Personalized Savings Tips</h3>
        """, unsafe_allow_html=True)
        
        tips = financial_insights.get('tips', [])
        for i, tip in enumerate(tips):
            st.markdown(f"""
            <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #0d6efd;">
                <p style="font-size: 16px; margin: 0;"><strong>{i+1}:</strong> {tip}</p>
            </div>
            """, unsafe_allow_html=True)
            
        # Display custom advice
        custom_advice = financial_insights.get('custom_advice', '')
        if custom_advice:
            st.markdown(f"""
            <div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; margin-top: 30px; border-left: 5px solid #ffc107;">
                <h3 style="margin-top: 0; color: #856404;"> Custom Recommendation</h3>
                <p style="font-size: 18px; line-height: 1.6;">{custom_advice}</p>
            </div>
            """, unsafe_allow_html=True)
    
    
        

    with tab3:
        st.header("Transactions")
        
        # Filters for transactions
        st.subheader("Filter Transactions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            min_date = transactions_df['date'].min().date()
            max_date = transactions_df['date'].max().date()
            date_range = st.date_input("Date range", [min_date, max_date], min_value=min_date, max_value=max_date)
        
        with col2:
            # Category filter
            all_categories = ['All'] + sorted(transactions_df['category'].unique().tolist())
            selected_category = st.selectbox("Category", all_categories)
        
        with col3:
            # Transaction type filter
            all_types = ['All', 'credit', 'debit']
            selected_type = st.selectbox("Transaction Type", all_types)
        
        # Apply filters
        filtered_df = transactions_df.copy()
        
        # Date filter
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[(filtered_df['date'].dt.date >= start_date) & 
                                      (filtered_df['date'].dt.date <= end_date)]
        
        # Category filter
        if selected_category != 'All':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
        # Type filter
        if selected_type != 'All':
            filtered_df = filtered_df[filtered_df['type'] == selected_type]
        
        # Search filter
        import re
        search_term = st.text_input("Search in descriptions")
        
        if search_term:
            try:
                sanitized_term = re.escape(search_term)
                filtered_df = filtered_df[filtered_df['description'].str.contains(sanitized_term, case=False, na=False)]
            except Exception as e:
                st.warning(f"Search error: {str(e)}. Showing all results.")
        
        # Display filtered transactions
        st.subheader(f"Transactions - {len(filtered_df)} records")
        
        # Format the dataframe for display
        display_df = filtered_df.copy()
        display_df['date'] = display_df['date'].dt.date
        
        # Sort by date (newest first)
        display_df = display_df.sort_values('date', ascending=False)
        
        # Display the dataframe
        st.dataframe(display_df.style.format({
            'amount': '₹{:.2f}'
        }), use_container_width=True)
        
        # Summary of filtered results
        if not filtered_df.empty:
            st.markdown(f"""
            <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; border: 1px solid #d1e7dd;">
            <h4 style="color: #0d6efd; margin: 0;">Filtered Results Summary</h4>
            <ul style="margin: 0; padding-left: 20px; font-size: 16px; color: #212529;">
                <li><strong>Total Credits:</strong> ₹{filtered_df[filtered_df['amount'] > 0]['amount'].sum():,.2f}</li>
                <li><strong>Total Debits:</strong> ₹{abs(filtered_df[filtered_df['amount'] < 0]['amount'].sum()):,.2f}</li>
                <li><strong>Net Amount:</strong> ₹{filtered_df['amount'].sum():,.2f}</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.file_processed:
        if st.button("Start Over", key="start_over"):
            st.session_state.transactions_df = None
            st.session_state.analysis_results = None
            st.session_state.analyzer = None
            st.session_state.financial_insights = None
            st.session_state.file_processed = False
            st.rerun()

with col2:
    if st.session_state.transactions_df is not None and st.session_state.analyzer:
        if st.button("Export to Excel", key="export_excel"):
            excel_path = st.session_state.analyzer.export_to_excel()

            with open(excel_path, "rb") as file:
                excel_data = file.read()

            b64_excel = base64.b64encode(excel_data).decode()
            href = f"""
            <div style="text-align: center; margin-top: 10px;">
                <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" 
                   download="cash_flow_analysis.xlsx" 
                   style="text-decoration: none; color: white; background-color: #007bff; padding: 10px 20px; border-radius: 5px; display: inline-block;">
                    Download Excel File
                </a>
            </div>
            """
            st.markdown(href, unsafe_allow_html=True)

            # Cleanup temp file
            os.remove(excel_path)

with col3:
    if st.session_state.transactions_df is not None and st.session_state.analyzer:
        if st.button("Export to CSV", key="export_csv"):
            csv_path = st.session_state.analyzer.export_to_csv()

            with open(csv_path, "rb") as file:
                csv_data = file.read()

            b64_csv = base64.b64encode(csv_data).decode()
            href = f"""
            <div style="text-align: center; margin-top: 10px;">
                <a href="data:text/csv;base64,{b64_csv}" 
                   download="transactions.csv" 
                   style="text-decoration: none; color: white; background-color: #28a745; padding: 10px 20px; border-radius: 5px; display: inline-block;">
                    Download CSV File
                </a>
            </div>
            """
            st.markdown(href, unsafe_allow_html=True)

            # Cleanup temp file
            os.remove(csv_path)