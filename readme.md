# Cash Flow Analyzer

A Python Streamlit application that analyzes bank statements using Azure OpenAI GPT-4o to extract and categorize transactions, providing visual insights into your financial health.

## Features

- **One-Click Statement Upload**: Upload any bank statement PDF and get instant analysis without manual data entry
- **Automatic Categorization**: Transactions are automatically sorted into clear spending categories
- **Monthly Cash Flow Summary**: See your income versus expenses in simple charts
- **Spending Breakdown**: View your top spending categories in a pie chart
- **Exportable Reports**: Download Excel or CSV reports of your financial data
- **Interactive Filtering**: Filter transactions by date, category, type, or search terms

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Azure OpenAI API key with access to GPT-4o

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/cash-flow-analyzer.git
   cd cash-flow-analyzer
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your Azure OpenAI credentials:
   ```
   AZURE_OPENAI_KEY=your_api_key_here
   AZURE_OPENAI_ENDPOINT=https://access-01.openai.azure.com/openai/deployments/gpt-4o/chat/completions
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   ```

### Running the Application

Start the Streamlit application:
```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`

## Usage

1. **Upload a bank statement PDF**: Click the upload button and select your bank statement PDF
2. **Wait for processing**: The application will extract transactions using Azure OpenAI GPT-4o
3. **Explore your financial data**: Navigate through the different tabs to analyze your cash flow
4. **Export your data**: Use the sidebar buttons to export your data to Excel or CSV

## Project Structure

- `app.py`: Main Streamlit application
- `pdf_extractor.py`: Contains the GPTBankStatementExtractor class for parsing bank statements
- `cash_flow_analyzer.py`: Contains the CashFlowAnalyzer class for financial analysis
- `requirements.txt`: Python dependencies
- `.env`: Environment variables (not committed to version control)

## Customization

You can customize the categories and analysis by modifying the `cash_flow_analyzer.py` file. The application is designed to be easily extendable for additional features.

## Limitations

- PDF extraction quality depends on the format and structure of your bank statement
- The application requires an Azure OpenAI API key with access to GPT-4o
- Processing time may vary depending on the size and complexity of your bank statement

## License

MIT License

## Acknowledgements

- This project uses [Streamlit](https://streamlit.io/) for the web interface
- Data visualization is powered by [Plotly](https://plotly.com/)
- Bank statement text extraction uses [PyPDF2](https://github.com/py-pdf/pypdf)
- Transaction extraction and categorization uses [Azure OpenAI GPT-4o](https://learn.microsoft.com/en-us/azure/ai-services/openai/)