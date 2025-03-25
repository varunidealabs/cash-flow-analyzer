import os
import json
import base64
import requests
import PyPDF2
from io import BytesIO
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import re

class GPTBankStatementExtractor:
    def __init__(self, api_endpoint=None, api_key=None):
        """
        Initialize the extractor with Azure OpenAI API credentials.
        
        If not provided, will attempt to load from environment variables:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_KEY
        """
        load_dotenv()  # Load environment variables from .env file
        
        self.api_endpoint = api_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", 
                           "https://access-01.openai.azure.com/openai/deployments/gpt-4o/chat/completions")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        
        if not self.api_endpoint or not self.api_key:
            raise ValueError("Azure OpenAI API endpoint and key must be provided or set as environment variables")
    
    def extract_text_from_pdf(self, pdf_file):
        """Extract all text from a PDF file upload (works with Streamlit)"""
        text_content = ""
        
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from each page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n\n"
        
        return text_content
    
    def extract_transactions(self, pdf_file):
        """
        Extract transaction data from bank statement PDF using Azure OpenAI
        
        Returns:
            DataFrame with columns: date, description, amount, type (credit/debit), category
        """
        # Get text content from PDF
        text_content = self.extract_text_from_pdf(pdf_file)
        
        # Clean and prepare text content
        text_content = self._preprocess_text(text_content)
        
        # Prepare prompt for GPT
        prompt = self._create_extraction_prompt(text_content)
        
        # Get response from Azure OpenAI
        response = self._call_azure_openai(prompt)
        
        # Parse the JSON response
        try:
            transactions_data = self._parse_gpt_response(response)
            return transactions_data
        except Exception as e:
            print(f"Error parsing GPT response: {e}")
            print("Raw response:", response)
            return None
    
    def _preprocess_text(self, text):
        """Clean and prepare text for better extraction"""
        # Remove page headers/footers that might contain "Page X of Y"
        text = re.sub(r'Page \d+ of \d+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR issues with numbers
        text = re.sub(r'l(\d)', r'1\1', text)  # Replace l1234 with 11234
        text = re.sub(r'O(\d)', r'0\1', text)  # Replace O123 with 0123
        
        return text
    
    def _create_extraction_prompt(self, text_content):
        """Create a structured prompt for GPT to extract transaction data"""
        return [
            {"role": "system", "content": """
            You are a financial data extraction expert specialized in Indian banking documents. Your task is to extract transaction data from Indian bank statements with 100% accuracy. Focus only on actual financial transactions.
            All amounts should be treated as Indian Rupees (₹).

            Extract ONLY the following fields for each transaction:
            1. Date: Format as YYYY-MM-DD
            2. Description: The merchant or transaction description
            3. Amount: Numerical value (positive for credits, negative for debits)
            4. Type: Either "credit" (money in) or "debit" (money out)
            5. Category: Classify into one of these categories:
               - Income (salary, deposits, transfers in)
               - Housing (rent, mortgage, property taxes)
               - Utilities (electricity, water, gas, internet, phone)
               - Food (groceries, restaurants, food delivery)
               - Transportation (gas, public transit, ride sharing, vehicle expenses)
               - Entertainment (streaming services, movies, events)
               - Shopping (retail, online shopping, electronics)
               - Health (medical bills, pharmacy, insurance)
               - Education (tuition, books, courses)
               - Personal (haircuts, gym, clothing)
               - Travel (hotels, flights, vacation expenses)
               - Insurance (health, auto, home, life)
               - Investments (stocks, bonds, retirement contributions)
               - Transfers (money moved between accounts)
               - Fees (bank fees, service charges, penalties)
               - Other (miscellaneous expenses that don't fit elsewhere)

            Return ONLY a JSON array of transactions without any explanations or additional text.
            Each transaction should be a JSON object with the fields above.
            If you cannot determine a field with high confidence, use null.
            Do NOT include balance information, account summaries, or non-transaction data.
            Do NOT hallucinate transactions - only extract what is clearly presented in the statement.
            Ensure dates are properly formatted and amounts are numeric (not strings with currency symbols).
            """
            },
            {"role": "user", "content": f"Here is the bank statement text content. Please extract all transactions following the required format:\n\n{text_content}"}
        ]
    
    def _call_azure_openai(self, messages):
        """Call Azure OpenAI API with the provided messages"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        data = {
            "messages": messages,
            "temperature": 0.1,  # Low temperature for more deterministic outputs
            "max_tokens": 8000,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(
            f"{self.api_endpoint}?api-version={self.api_version}",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
        
        return response.json()
    
    
    def _parse_gpt_response(self, response):
        """Parse the JSON response from GPT into a DataFrame of transactions"""
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '{}')
    
        # Check if response was cut off (finish_reason: length)
        finish_reason = response.get('choices', [{}])[0].get('finish_reason')
    
        try:
            # Try to parse the JSON response
            data = json.loads(content)
        
            # Extract transactions array from the response
            transactions = data.get('transactions', [])
            if not transactions and isinstance(data, list):
            # If GPT returned a direct array instead of nested under 'transactions'
                transactions = data
            
            df = pd.DataFrame(transactions)
        
            # Ensure correct data types
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # Standardize column names (lowercase)
            if not df.empty:
                df.columns = [col.lower() for col in df.columns]
        
            return df
    
        except json.JSONDecodeError as e:
            # Handle incomplete JSON responses
            if finish_reason == 'length':
                # Try to fix incomplete JSON by finding the last complete transaction
                try:
                    # Find the last complete transaction object
                    fixed_content = self._fix_truncated_json(content)
                    data = json.loads(fixed_content)
                
                    # Extract transactions and create DataFrame
                    transactions = data.get('transactions', [])
                    if not transactions and isinstance(data, list):
                        transactions = data
                
                    df = pd.DataFrame(transactions)
                
                    # Ensure correct data types
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    if 'amount' in df.columns:
                        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                    
                    # Standardize column names (lowercase)
                    if not df.empty:
                        df.columns = [col.lower() for col in df.columns]
                
                    return df
                except Exception as inner_e:
                    # If we couldn't fix it, raise the original error
                    raise e
            else:
                # For other JSON parsing errors, re-raise
                raise e

    def _fix_truncated_json(self, incomplete_json):
        """Attempt to fix truncated JSON by finding the last complete transaction"""
        # Find the position of the last complete transaction (ending with "}," or "}")
        last_complete_transaction = incomplete_json.rfind("},")
    
        if last_complete_transaction == -1:
            # If no transaction with a comma is found, look for the last closing brace
            last_complete_transaction = incomplete_json.rfind("}")
            if last_complete_transaction == -1:
                # If no closing brace is found, we can't fix the JSON
                raise ValueError("Cannot fix truncated JSON: No complete transaction found")
    
        if "transactions" in incomplete_json:

            # If JSON has a transactions array, close it properly
            fixed_json = incomplete_json[:last_complete_transaction+1] + "]\n}"
        else:
            # For direct array of transactions
            fixed_json = incomplete_json[:last_complete_transaction+1] + "]"
    
        return fixed_json