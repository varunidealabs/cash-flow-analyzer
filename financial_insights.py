import openai
import pandas as pd
import numpy as np
from datetime import datetime
import os
import re
import json

class FinancialInsightsGenerator:
    def __init__(self, api_key=None, api_endpoint=None):
        """
        Initialize the Financial Insights Generator with OpenAI API credentials.
        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY", "")
        self.api_endpoint = api_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", 
                           "https://access-01.openai.azure.com/openai/deployments/gpt-4o/chat/completions")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        
    def generate_financial_summary(self, transactions_df, analysis_results):
        """
        Generate a human-readable financial summary based on transaction data and analysis results
        
        Args:
            transactions_df: DataFrame containing transaction data
            analysis_results: Dictionary with analysis metrics
            
        Returns:
            Dictionary with summary, tips, and financial health score
        """
        # Prepare data for the prompt
        summary_data = {
            "total_transactions": len(transactions_df),
            "date_range": analysis_results['summary']['date_range'],
            "total_income": analysis_results['summary']['total_income'],
            "total_expenses": analysis_results['summary']['total_expenses'],
            "net_flow": analysis_results['summary']['net_flow'],
            "savings_rate": analysis_results['summary']['avg_savings_rate'],
            "top_expense_category": analysis_results['summary']['top_expense_category'],
            "top_expense_amount": analysis_results['summary']['top_expense_amount']
        }
        
        # Get income sources
        income_transactions = transactions_df[transactions_df['amount'] > 0]
        top_income_sources = income_transactions.groupby('description')['amount'].sum().sort_values(ascending=False).head(3)
        
        # Get expense categories
        expense_transactions = transactions_df[transactions_df['amount'] < 0]
        category_expenses = expense_transactions.groupby('category')['amount'].sum().abs().sort_values(ascending=False)
        
        # Identify recurring expenses (transactions with similar descriptions that occur multiple times)
        freq_descriptions = expense_transactions['description'].value_counts()
        recurring_expenses = freq_descriptions[freq_descriptions > 1].index.tolist()
        
        # Look for unusual large transactions (outliers)
        expense_mean = expense_transactions['amount'].mean()
        expense_std = expense_transactions['amount'].std()
        large_transactions = expense_transactions[expense_transactions['amount'] < (expense_mean - 2*expense_std)]
        
        # Check for high frequency small expenses
        small_expenses = expense_transactions[expense_transactions['amount'] > -500]  # Adjust threshold as needed
        small_expense_count = len(small_expenses)
        
        # Create transaction patterns summary
        transaction_patterns = {
            "top_income_sources": top_income_sources.to_dict(),
            "category_expenses": category_expenses.to_dict(),
            "recurring_expenses": recurring_expenses[:5] if len(recurring_expenses) > 5 else recurring_expenses,
            "large_transactions": large_transactions[['date', 'description', 'amount']].to_dict(orient='records')[:3],
            "small_expense_count": small_expense_count
        }
        
        # Calculate financial health score (0-100)
        financial_health = self._calculate_financial_health(summary_data, transaction_patterns)
        
        # Generate insights using OpenAI
        insights = self._generate_insights_with_gpt(summary_data, transaction_patterns, financial_health)
        
        return {
            "summary": insights.get("summary", ""),
            "tips": insights.get("tips", []),
            "health_score": financial_health,
            "custom_advice": insights.get("custom_advice", "")
        }
    
    def _calculate_financial_health(self, summary_data, transaction_patterns):
        """Calculate a financial health score from 0-100"""
        score = 50  # Start at neutral
        
        # Positive factors
        if summary_data["net_flow"] > 0:
            score += 10
        
        # Savings rate impact
        savings_rate = summary_data["savings_rate"]
        if savings_rate > 30:
            score += 15
        elif savings_rate > 20:
            score += 10
        elif savings_rate > 10:
            score += 5
        elif savings_rate < 0:
            score -= 15
            
        # Diverse income sources
        income_sources = len(transaction_patterns["top_income_sources"])
        if income_sources > 2:
            score += 5
            
        # Too many expense categories
        if len(transaction_patterns["category_expenses"]) > 8:
            score -= 5
            
        # Large expenses
        if len(transaction_patterns["large_transactions"]) > 2:
            score -= 5
            
        # Too many small expenses
        if transaction_patterns["small_expense_count"] > 20:
            score -= 5
            
        # Balance score between 0-100
        return max(0, min(100, score))
    
    def _generate_insights_with_gpt(self, summary_data, transaction_patterns, financial_health):
        """Generate personalized financial insights using GPT"""
        
        # Create a detailed prompt for GPT
        prompt = f"""
        Based on the following financial data, provide a personalized financial summary and savings tips:
        
        Financial Summary:
        - Date Range: {summary_data['date_range']}
        - Total Income: ₹{summary_data['total_income']:,.2f}
        - Total Expenses: ₹{summary_data['total_expenses']:,.2f}
        - Net Cash Flow: ₹{summary_data['net_flow']:,.2f}
        - Savings Rate: {summary_data['savings_rate']:.1f}%
        - Top Expense Category: {summary_data['top_expense_category']} (₹{summary_data['top_expense_amount']:,.2f})
        - Financial Health Score: {financial_health}/100
        
        Income Sources:
        {self._format_dict_for_prompt(transaction_patterns['top_income_sources'])}
        
        Expense Categories:
        {self._format_dict_for_prompt(transaction_patterns['category_expenses'])}
        
        Recurring Expenses:
        {', '.join(transaction_patterns['recurring_expenses']) if transaction_patterns['recurring_expenses'] else 'None identified'}
        
        Large Transactions:
        {self._format_list_for_prompt(transaction_patterns['large_transactions'])}
        
        Small Expenses Count: {transaction_patterns['small_expense_count']}
        
        Based on this data:
        1. Provide a friendly, concise 3-4 sentence summary of the person's financial situation in second person ("you").
        2. Identify 3-5 specific personalized saving opportunities based on the spending patterns.
        3. Provide one piece of custom financial advice specifically tailored to their unique situation.
        
        Format your response as JSON with keys: "summary", "tips" (as a list), and "custom_advice".
        Use conversational, encouraging language. The advice should be realistic and helpful.
        """
        
        try:
            # Call the Azure OpenAI API
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            data = {
                "messages": [
                    {"role": "system", "content": "You are a friendly financial advisor who analyzes bank statements and provides personalized insights."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            }
            
            import requests
            response = requests.post(
                f"{self.api_endpoint}?api-version={self.api_version}",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return json.loads(content)
            else:
                # Fallback if API call fails
                return {
                    "summary": f"During this period, you had an income of ₹{summary_data['total_income']:,.2f} and expenses of ₹{summary_data['total_expenses']:,.2f}, resulting in a {'positive' if summary_data['net_flow'] > 0 else 'negative'} cash flow of ₹{abs(summary_data['net_flow']):,.2f}. Your savings rate was {summary_data['savings_rate']:.1f}%.",
                    "tips": [
                        "Track your expenses regularly to identify potential savings",
                        "Consider creating a budget for your top spending categories",
                        "Look for ways to increase your income or reduce unnecessary expenses"
                    ],
                    "custom_advice": "Focus on building an emergency fund equivalent to 3-6 months of expenses for financial security."
                }
                
        except Exception as e:
            print(f"Error generating insights: {e}")
            # Simple fallback
            return {
                "summary": f"During this period, you had an income of ₹{summary_data['total_income']:,.2f} and expenses of ₹{summary_data['total_expenses']:,.2f}, resulting in a {'positive' if summary_data['net_flow'] > 0 else 'negative'} cash flow of ₹{abs(summary_data['net_flow']):,.2f}.",
                "tips": [
                    "Track your expenses regularly",
                    "Create a budget for better financial planning",
                    "Build an emergency fund for unexpected expenses"
                ],
                "custom_advice": "Consider reviewing your spending in your top expense category."
            }
    
    def _format_dict_for_prompt(self, data_dict):
        """Format dictionary data for the prompt"""
        formatted = []
        for key, value in data_dict.items():
            formatted.append(f"- {key}: ₹{value:,.2f}")
        return "\n".join(formatted)
    
    def _format_list_for_prompt(self, data_list):
        """Format list data for the prompt"""
        if not data_list:
            return "None identified"
            
        formatted = []
        for item in data_list:
            if isinstance(item, dict):
                date = item.get('date', '')
                if isinstance(date, pd.Timestamp):
                    date = date.strftime('%Y-%m-%d')
                desc = item.get('description', '')
                amount = item.get('amount', 0)
                formatted.append(f"- {date} | {desc} | ₹{amount:,.2f}")
            else:
                formatted.append(f"- {item}")
        return "\n".join(formatted)