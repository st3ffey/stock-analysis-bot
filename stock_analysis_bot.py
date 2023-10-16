import os
import warnings
import openai
import langchain
import requests
import yfinance as yf

# Replace with actual API key
os.environ["OPENAI_API_KEY"] = "xx"
openai.api_key = "xx"

warnings.filterwarnings("ignore")

import yfinance as yf

# Stock data from Yahoo Finance

def get_stock_price(ticker: str, history: int = 5) -> str:
    """
    Fetches the closing price and volume of a stock for a given number of days.

    Parameters:
    - ticker (str): The stock ticker symbol. If the ticker contains a ".", 
                    everything after the "." will be ignored.
    - history (int, optional): Number of days of stock history to fetch. 
                               Default is 5 days.

    Returns:
    - str: A string representation of the stock's closing price and volume 
           for the specified number of days.
    """
    
    # Fetch the stock data for the past year
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y")
    
    # Filter and format the dataframe
    df = df[["Closing", "Volume"]]
    df.index = [str(x).split()[0] for x in list(df.index)]
    df.index.rename("Date", inplace=True)
    df = df[-history:]
    
    return df.to_string()

def get_recent_stock_news(company_name: str) -> list:
    """
    Fetches recent stock news titles related to a given company.
    
    Parameters:
    - company_name (str): The name of the company to fetch the news for.

    Returns:
    - list: A list of titles of the recent stock news related to the company. 
            Returns None if there's an issue fetching the data.
    """
    
    # API setup
    api_key = 'xx'  # Replace 'xx' with actual API key
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    # Constructing the API URL
    query = f"{company_name} stock news"
    count = 10  # Number of news results
    offset = 0  # Starting point for the results
    mkt = 'en-US'  # Market: language-country/region
    safesearch = 'Moderate'  # Safety level for the search
    
    api_url = f'https://api.bing.microsoft.com/v7.0/news/search?q={query}&count={count}&offset={offset}&mkt={mkt}&safesearch={safesearch}'
    
    # Fetching the data
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        results = response.json()
        
        # Extracting titles of the news
        top_news = [result['name'] for result in results['value']]
        
        return top_news
    else:
        print(f'Failed to retrieve data. Status code: {response.status_code}')
        return None
        
# Fetch financial statements from Yahoo Finance

def get_financial_statements(ticker: str) -> str:
    """
    Fetches the balance sheet of a given stock ticker for the most recent 3 years.
    
    Parameters:
    - ticker (str): The stock ticker symbol. If the ticker contains a ".", 
                    everything after the "." will be ignored.
    
    Returns:
    - str: A string representation of the balance sheet for the most recent 
           3 years. Returns an empty string if no data is found.
    """
    
    # Extract the main part of the ticker if it contains a "."
    if "." in ticker:
        ticker = ticker.split(".")[0]
    
    company = yf.Ticker(ticker)
    balance_sheet = company.balance_sheet
    
    # Limit the data to the most recent 3 years
    if balance_sheet.shape[1] >= 3:
        balance_sheet = balance_sheet.iloc[:, :3]
    
    # Drop rows with missing values
    balance_sheet = balance_sheet.dropna(how="any")
    
    return balance_sheet.to_string()

# Organizing a function for prompt engineering to get stock ticker
import json
function=[
        {
        "name": "get_company_ticker",
        "description": "This will get the stock ticker of the company",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker_symbol": {
                    "type": "string",
                    "description": "This is the stock symbol of the company.",
                },
                "company_name": {
                    "type": "string",
                    "description": "This is the name of the company given in the user query",
                }
            },
            "required": ["company_name","ticker_symbol"],
        },
    }
]

def get_stock_ticker(query: str) -> tuple:
    """
    Fetches the company name and stock ticker based on a given query using the OpenAI GPT-3.5 Turbo model.
    
    Parameters:
    - query (str): The user's request containing details to identify the company name and stock ticker.
    
    Returns:
    - tuple: A tuple containing the company stock ticker and company name.
             Returns an empty tuple if no data is found or there's an error in processing.
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.1,
            messages = [
                {
                    "role": "user",
                    "content": f"From the following user request, what is the company name and the company stock ticker?: {query}?"
                }
            ],
            functions = function,
            function_call = {"name": "get_company_ticker"},
        )

        # Formatting to retrieve ticker and company name
        message = response["choices"][0]["message"]
        arguments = json.loads(message["function_call"]["arguments"])
        company_name = arguments["company_name"]
        company_ticker = arguments["ticker_symbol"]

        return company_ticker, company_name
    
    except Exception as e:
        print(f"Error processing request: {e}")
        return ()

def analyze_stock_with_openai_chat(user_request: str) -> str:
    """
    Analyzes a stock based on user's request using OpenAI's GPT-3.5 Turbo model. The function gathers stock price, 
    recent news, and financial statements to provide a pros and cons list for investing in the specified company.
    
    Parameters:
    - user_request (str): The user's request containing details about the stock or company to analyze.
    
    Returns:
    - str: A detailed analysis from GPT-3.5 Turbo model on whether or not the company is a good investment.
    """
    
    # Extract company name and ticker from user's request
    ticker, company_name = get_stock_ticker(user_request)
    
    # Gather relevant information for processing
    stock_price_data = get_stock_price(ticker)
    recent_news = get_recent_stock_news(company_name)
    financial_statements = get_financial_statements(ticker)
    
    # Construct the message for GPT-3.5-turbo
    messages = [
        {"role": "user", "content": user_request},
        {"role": "system", "content": f"Given the user's request, use the following information to develop a pros and cons list for investing in {company_name}. Stock Price: {stock_price_data}, Recent News: {', '.join(recent_news)}, Financial Statements: {financial_statements}. Ultimately, conclude whether or not {company_name} is a good investment."}
    ]
    
    # Use OpenAI API to get the model's response
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=messages
    )

    # Format as string and remove uncessary newlines
    result = response.choices[0].message['content']
    final = ' '.join(result.split())
    
    # Format the output for better readability
    final = final.replace(":", ":\n")
    
    return final


## flask application
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    response = ''
    if request.method == 'POST':
        user_request = request.form['question']
        response = analyze_stock_with_openai_chat(user_request)
    
    return render_template('index.html', response = response)

if __name__ == '__main__':
    app.run(debug=True)
