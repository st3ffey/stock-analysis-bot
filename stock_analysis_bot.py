#!/usr/bin/env python
# coding: utf-8

# In[39]:


import os
import warnings
import openai
import langchain
import requests
import yfinance as yf
os.environ["OPENAI_API_KEY"] = "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"
openai.api_key = "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"

warnings.filterwarnings("ignore")


# ### Creating tools for fetching data



# In[52]:


import yfinance as yf

# Stock data from Yahoo Finance

def get_stock_price(ticker, history=5):
    # time.sleep(4) #To avoid rate limit error
    if "." in ticker:
        ticker=ticker.split(".")[0]
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y")
    df = df[["Close","Volume"]]
    df.index = [str(x).split()[0] for x in list(df.index)]
    df.index.rename("Date", inplace=True)
    df = df[-history:]
    # print(df.columns)
    
    return df.to_string()

print(get_stock_price("AAPL"))


# In[55]:


def get_recent_stock_news(company_name):
    api_key = '53561b20660b48f49e135d473534196c'
    
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    # Constructing the API URL
    query = company_name + "stock news"
    count = 10  # to get 5 results
    offset = 0  # to start from the first result
    mkt = 'en-US'  # market: language-country/region
    safesearch = 'Moderate'  # or 'Strict' or 'Off'
    api_url = f'https://api.bing.microsoft.com/v7.0/news/search?q={query}&count={count}&offset={offset}&mkt={mkt}&safesearch={safesearch}'
    
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        results = response.json()
        
        # Extracting titles and URLs of the results
        top_news = []
        for result in results['value']:
            title = result['name']
            top_news.append(title)
        
        return top_news
    
    else:
        print('Failed to retrieve data:', response.status_code)
        return None


# In[46]:


# Fetch financial statements from Yahoo Finance

def get_financial_statements(ticker):
    # time.sleep(4) #To avoid rate limit error
    if "." in ticker:
        ticker = ticker.split(".")[0]
    else:
        ticker = ticker
    company = yf.Ticker(ticker)
    balance_sheet = company.balance_sheet
    if balance_sheet.shape[1] >= 3:
        balance_sheet = balance_sheet.iloc[:, :3]    # Remove 4th years data
    balance_sheet = balance_sheet.dropna(how = "any")
    balance_sheet = balance_sheet.to_string()

    return balance_sheet


# In[30]:


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


# In[58]:
def get_stock_ticker(query):
    response = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            temperature = 0.1,
            messages = [{
                "role":"user",
                "content":f"From the following user request, what is the comapany name and the company stock ticker ?: {query}?"
            }],
            functions = function,
            function_call = {"name": "get_company_ticker"},
    )
    message = response["choices"][0]["message"]
    arguments = json.loads(message["function_call"]["arguments"])
    company_name = arguments["company_name"]
    company_ticker = arguments["ticker_symbol"]
    return company_ticker, company_name

def analyze_stock_with_openai_chat(user_request):
    # Extract company name and ticker from user's request
    ticker, company_name = get_stock_ticker(user_request)
    
    # Gather relevant information
    stock_price_data = get_stock_price(ticker)
    recent_news = get_recent_stock_news(company_name)
    financial_statements = get_financial_statements(ticker)
    
    # Construct the message for GPT-3.5-turbo
    messages = [
        {"role": "user", "content": user_request},
        {"role": "system", "content": f"Given the user's request, use the following information to develop a pros and cons list for investing in {company_name}. Stock Price: {stock_price_data}, Recent News: {', '.join(recent_news)}, Financial Statements: {financial_statements}. Ultimately, conclude whether or not {company_name} is a good investment."}
    ]
    
    # Use OpenAI API to get the model's response
    # Uncomment the below code when you have the OpenAI API set up in your environment
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    
    result = response.choices[0].message['content']
    final = ' '.join(result.split())
    
    for i in final:
        i.replace(":", ":\n")
    return final


# In[59]:


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

    
