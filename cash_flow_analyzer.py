import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
from datetime import datetime, timedelta
import tempfile
import os

class CashFlowAnalyzer:
    def __init__(self, transaction_data=None):
        """
        Initialize the Cash Flow Analyzer with transaction data
        
        Args:
            transaction_data: Pandas DataFrame with transaction data (date, amount, category, etc.)
        """
        self.transactions = transaction_data
        self.analysis_results = {}
    
    def load_data(self, dataframe):
        """Load transaction data from a DataFrame"""
        self.transactions = dataframe
        
        # Ensure date column is datetime
        if 'date' in self.transactions.columns:
            self.transactions['date'] = pd.to_datetime(self.transactions['date'])
        
        # Sort by date
        self.transactions = self.transactions.sort_values('date')
        
        return self
    
    def preprocess_data(self):
        """Clean and prepare data for analysis"""
        if self.transactions is None or self.transactions.empty:
            raise ValueError("No transaction data loaded. Call load_data() first.")
        
        # Create month and year columns for aggregation
        self.transactions['month'] = self.transactions['date'].dt.month
        self.transactions['year'] = self.transactions['date'].dt.year
        self.transactions['year_month'] = self.transactions['date'].dt.strftime('%Y-%m')
        
        # Ensure amount is numeric
        self.transactions['amount'] = pd.to_numeric(self.transactions['amount'], errors='coerce')
        
        # Fill missing categories
        if 'category' in self.transactions.columns:
            self.transactions['category'].fillna('Other', inplace=True)
            
        # Add sign for income/expense if not present
        if 'type' in self.transactions.columns and 'amount' in self.transactions.columns:
            # Make sure debits are negative and credits are positive
            self.transactions.loc[self.transactions['type'] == 'debit', 'amount'] = -abs(self.transactions.loc[self.transactions['type'] == 'debit', 'amount'])
            self.transactions.loc[self.transactions['type'] == 'credit', 'amount'] = abs(self.transactions.loc[self.transactions['type'] == 'credit', 'amount'])
        
        return self
    
    def analyze_cash_flow(self):
        """Perform cash flow analysis"""
        if self.transactions is None or self.transactions.empty:
            raise ValueError("No transaction data loaded. Call load_data() first.")
        
        # Get time range
        start_date = self.transactions['date'].min()
        end_date = self.transactions['date'].max()
        date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
        
        # Monthly Cash Flow
        monthly_cash_flow = self.transactions.groupby('year_month').agg({
            'amount': ['sum', 'count']
        })
        monthly_cash_flow.columns = ['net_flow', 'num_transactions']
        monthly_cash_flow = monthly_cash_flow.reset_index()
        
        # Income vs Expenses by Month
        income = self.transactions[self.transactions['amount'] > 0].groupby('year_month')['amount'].sum()
        expenses = self.transactions[self.transactions['amount'] < 0].groupby('year_month')['amount'].sum().abs()
        
        # Combine into DataFrame with all months represented
        all_months = pd.DataFrame({'year_month': sorted(list(set(income.index) | set(expenses.index)))})
        monthly_income_vs_expenses = all_months.merge(pd.DataFrame({'income': income}), on='year_month', how='left')
        monthly_income_vs_expenses = monthly_income_vs_expenses.merge(pd.DataFrame({'expenses': expenses}), on='year_month', how='left')
        monthly_income_vs_expenses = monthly_income_vs_expenses.fillna(0)
        
        # Calculate savings rate
        monthly_income_vs_expenses['savings'] = monthly_income_vs_expenses['income'] - monthly_income_vs_expenses['expenses']
        monthly_income_vs_expenses['savings_rate'] = (monthly_income_vs_expenses['savings'] / monthly_income_vs_expenses['income'] * 100).round(2)
        monthly_income_vs_expenses.loc[monthly_income_vs_expenses['income'] == 0, 'savings_rate'] = 0
        
        # Spending by Category
        if 'category' in self.transactions.columns:
            category_spending = self.transactions[self.transactions['amount'] < 0].groupby('category')['amount'].sum().abs()
            category_spending = category_spending.sort_values(ascending=False).reset_index()
            
            # Monthly spending by category
            monthly_category_spending = self.transactions[self.transactions['amount'] < 0].groupby(['year_month', 'category'])['amount'].sum().abs().reset_index()
        else:
            category_spending = pd.DataFrame(columns=['category', 'amount'])
            monthly_category_spending = pd.DataFrame(columns=['year_month', 'category', 'amount'])
        
        # Running balance calculation
        sorted_transactions = self.transactions.sort_values('date')
        sorted_transactions['running_balance'] = sorted_transactions['amount'].cumsum()
        
        # Store results
        self.analysis_results = {
            'monthly_cash_flow': monthly_cash_flow,
            'monthly_income_vs_expenses': monthly_income_vs_expenses,
            'category_spending': category_spending,
            'monthly_category_spending': monthly_category_spending,
            'running_balance': sorted_transactions[['date', 'running_balance']],
            'summary': {
                'total_income': self.transactions[self.transactions['amount'] > 0]['amount'].sum(),
                'total_expenses': abs(self.transactions[self.transactions['amount'] < 0]['amount'].sum()),  # Fixed line
                'net_flow': self.transactions['amount'].sum(),
                'avg_monthly_income': monthly_income_vs_expenses['income'].mean(),
                'avg_monthly_expenses': monthly_income_vs_expenses['expenses'].mean(),
                'avg_savings_rate': monthly_income_vs_expenses['savings_rate'].mean(),
                'top_expense_category': category_spending.iloc[0]['category'] if not category_spending.empty else None,
                'top_expense_amount': category_spending.iloc[0]['amount'] if not category_spending.empty else 0,
                'transaction_count': len(self.transactions),
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }
        }
        
        return self
    
    def generate_monthly_cash_flow_chart(self):
        """Generate monthly cash flow chart with income and expenses"""
        if not self.analysis_results:
            self.analyze_cash_flow()
        
        data = self.analysis_results['monthly_income_vs_expenses']
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=data['year_month'],
            y=data['income'],
            name='Income',
            marker_color='rgba(50, 171, 96, 0.7)'
        ))
        
        fig.add_trace(go.Bar(
            x=data['year_month'],
            y=data['expenses'],
            name='Expenses',
            marker_color='rgba(219, 64, 82, 0.7)'
        ))
        
        
        
        fig.update_layout(
            title='Monthly Income vs Expenses',
            xaxis_title='Month',
            yaxis_title='Amount',
            barmode='group',
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def generate_spending_breakdown_chart(self):
        """Generate pie chart of spending by category"""
        if not self.analysis_results:
            self.analyze_cash_flow()
        
        data = self.analysis_results['category_spending']
        
        # Limit to top 10 categories and group the rest as "Other"
        if len(data) > 10:
            top_categories = data.iloc[:9]
            other_sum = data.iloc[9:]['amount'].sum()
            
            other_row = pd.DataFrame({'category': ['Other'], 'amount': [other_sum]})
            data = pd.concat([top_categories, other_row], ignore_index=True)
        
        fig = px.pie(
            data,
            values='amount',
            names='category',
            title='Spending Breakdown by Category',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(template='plotly_white')
        
        return fig
    
    def generate_running_balance_chart(self):
        """Generate line chart of running balance over time"""
        if not self.analysis_results:
            self.analyze_cash_flow()
        
        data = self.analysis_results['running_balance']
        
        fig = px.line(
            data,
            x='date',
            y='running_balance',
            title='Account Balance Over Time',
            labels={'running_balance': 'Balance', 'date': 'Date'}
        )
        
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Balance',
            template='plotly_white'
        )
        
        # Add a horizontal line at zero
        fig.add_shape(
            type="line",
            x0=data['date'].min(),
            y0=0,
            x1=data['date'].max(),
            y1=0,
            line=dict(color="black", width=1, dash="dash")
        )
        
        return fig
    
    def generate_category_trend_chart(self, top_n=5):
        """Generate line chart showing spending trends by top categories"""
        if not self.analysis_results:
            self.analyze_cash_flow()
        
        # Get top categories by total spending
        top_categories = self.analysis_results['category_spending'].head(top_n)['category'].tolist()
        
        # Filter monthly data for top categories
        data = self.analysis_results['monthly_category_spending']
        data = data[data['category'].isin(top_categories)]
        
        fig = px.line(
            data,
            x='year_month',
            y='amount',
            color='category',
            title=f'Monthly Spending Trends - Top {top_n} Categories',
            labels={'amount': 'Amount', 'year_month': 'Month', 'category': 'Category'}
        )
        
        fig.update_layout(
            xaxis_title='Month',
            yaxis_title='Amount Spent',
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def generate_savings_rate_chart(self):
        """Generate chart showing savings rate over time"""
        if not self.analysis_results:
            self.analyze_cash_flow()
        
        data = self.analysis_results['monthly_income_vs_expenses']
        
        fig = go.Figure()
        
        # Add savings rate line
        fig.add_trace(go.Scatter(
            x=data['year_month'],
            y=data['savings_rate'],
            name='Savings Rate (%)',
            mode='lines+markers',
            line=dict(color='rgba(0, 128, 0, 0.8)', width=3),
            marker=dict(size=8)
        ))
        
        # Add horizontal line at 20% (good savings target)
        fig.add_shape(
            type="line",
            x0=data['year_month'].iloc[0],
            y0=20,
            x1=data['year_month'].iloc[-1],
            y1=20,
            line=dict(color="green", width=1, dash="dash")
        )
        
        fig.update_layout(
            title='Monthly Savings Rate',
            xaxis_title='Month',
            yaxis_title='Savings Rate (%)',
            template='plotly_white',
            annotations=[
                dict(
                    x=data['year_month'].iloc[-1],
                    y=20,
                    xref="x",
                    yref="y",
                    text="Target (20%)",
                    showarrow=False,
                    font=dict(size=12, color="green"),
                    xanchor="left",
                    xshift=10
                )
            ]
        )
        
        return fig
    
    def export_to_excel(self, output_path=None):
        """Export all analysis results to Excel"""
        if not self.analysis_results:
            self.analyze_cash_flow()
        
        if output_path is None:
            # Create a temporary file
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"cash_flow_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Raw transactions
            self.transactions.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Monthly cash flow
            self.analysis_results['monthly_cash_flow'].to_excel(writer, sheet_name='Monthly Cash Flow', index=False)
            
            # Income vs Expenses
            self.analysis_results['monthly_income_vs_expenses'].to_excel(writer, sheet_name='Income vs Expenses', index=False)
            
            # Category spending
            self.analysis_results['category_spending'].to_excel(writer, sheet_name='Category Spending', index=False)
            
            # Summary statistics
            pd.DataFrame([self.analysis_results['summary']]).to_excel(writer, sheet_name='Summary', index=False)
        
        return output_path
    
    def export_to_csv(self, output_path=None):
        """Export transactions to CSV"""
        if not self.transactions is None:
            if output_path is None:
                # Create a temporary file
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            
            self.transactions.to_csv(output_path, index=False)
            
        return output_path