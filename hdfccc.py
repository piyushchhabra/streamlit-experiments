import streamlit as st
import requests
import pandas as pd

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title='HDFC CC Transactions',
    page_icon='💳',
    layout='wide',
    initial_sidebar_state='auto',
)

def format_inr(n):
    s = str(int(n))
    s = s[::-1]
    groups = []
    i = 0
    while i < len(s):
        if i == 0:
            groups.append(s[i:i+3])
        else:
            groups.append(s[i:i+2])
        i += 2 if i > 0 else 3
    return ','.join(groups)[::-1]

with st.sidebar:
    st.markdown('## Get HDFC Credit Card Transactions')
    email = st.text_input("Enter your email")
    secret = st.text_input("Enter your secret", type="password")

    fetch_button = st.button("Fetch Transactions", type="primary")

st.title("HDFC Credit Card Transactions Viewer")

if fetch_button:
    if 'raw_data' in st.session_state:
        del st.session_state.raw_data
    if not email or not secret:
        st.error("Please provide both email and secret.")
    else:
        with st.spinner("Fetching transactions..."):
            try:
                api_url = "https://themindmap.azurewebsites.net/api/hdfc/transactions"
                payload = {
                    "userEmail": email,
                    "secret": secret
                }
                response = requests.post(api_url, json=payload, verify=False)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data"):
                        st.session_state.raw_data = data["data"]
                    else:
                        st.error(f"API Error: {data.get('message', 'An unknown error occurred.')}")

                elif response.status_code == 401:
                    st.error("Unauthorized: The secret provided is incorrect.")
                
                else:
                    st.error(f"Error fetching transactions. Status code: {response.status_code}")
                    st.text(response.text)

            except requests.exceptions.ConnectionError as e:
                st.error("Connection Error: Could not connect to the API.")
                st.error(f"Underlying error: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

if 'raw_data' in st.session_state:
    st.success("Transactions fetched successfully!")
    
    statement_dates = [item['statementDate'] for item in st.session_state.raw_data]
    selected_date = st.selectbox("Select Statement Date", statement_dates)

    selected_statement_data = next((item for item in st.session_state.raw_data if item['statementDate'] == selected_date), None)

    if selected_statement_data and selected_statement_data.get('transactions'):
        df = pd.DataFrame(selected_statement_data['transactions'])
        df['amount'] = pd.to_numeric(df['amount'])

        col1, col2 = st.columns(2)
        with col1:
            contains_text = st.text_input("Filter by description (case-insensitive)", "", placeholder="e.g., swiggy, amazon", key=f"filter_{selected_date}")
        with col2:
            sort_order = st.selectbox("Sort by amount", ("Default", "Low to High", "High to Low"), key=f"sort_{selected_date}")


        if contains_text:
            filtered_df = df[df['description'].str.contains(contains_text, case=False, na=False)].copy()
        else:
            filtered_df = df.copy()
        
        if sort_order == "Low to High":
            filtered_df = filtered_df.sort_values(by='amount', ascending=True)
        elif sort_order == "High to Low":
            filtered_df = filtered_df.sort_values(by='amount', ascending=False)

        st.table(filtered_df)

        if not filtered_df.empty:
            debit_total = filtered_df[filtered_df['transactionType'] == 'DEBIT']['amount'].sum()
            credit_total = filtered_df[filtered_df['transactionType'] == 'CREDIT']['amount'].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Total Debit: :red[₹ {format_inr(debit_total)}]")
            with col2:
                st.subheader(f"Total Credit: :green[₹ {format_inr(credit_total)}]")

            st.header("Spending by Keyword", divider="rainbow")
            
            keywords = ['zomato', 'swiggy', 'zepto', 'blinkit','amazon', 'myntra']
            summary_data = []

            debit_df = filtered_df[filtered_df['transactionType'] == 'DEBIT'].copy()

            for keyword in keywords:
                mask = debit_df['description'].str.contains(keyword, case=False, na=False)
                total = debit_df[mask]['amount'].sum()
                if total > 0:
                    summary_data.append({'Keyword': keyword.capitalize(), 'Total Spent': total})
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                summary_df['Total Spent'] = summary_df['Total Spent'].apply(lambda x: f"₹ {format_inr(x)}")
                st.table(summary_df)

        elif contains_text:
            st.info("No transactions match your filter.")
    else:
        st.info(f"No transactions found for statement date {selected_date}.")
