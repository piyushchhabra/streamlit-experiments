import streamlit as st
from io import StringIO

st.set_page_config(
    page_title='AskThatman: Calculate your dividend',
    page_icon='⚡',
    layout='wide',
    initial_sidebar_state='auto',
)


def load_statement(string_data):
    res = []
    for line in string_data:
        if line.count(",") == 6:
            dt, summary, rNumber, vdt, debit, credit, closingBalance = line.split(",")
            if dt is not None and dt.count("/") == 2:
                res.append(line)
    return res


def is_dividend(summary):
    if summary is None or len(summary) < 3:
        return False
    if summary.startswith("NEFT") or summary.startswith("NEFT"):
        return False
    if "ACH C-" in summary or " DIV " in summary:
        return True
    return False


def calculate_dividend(valid_lines):
    res_dividend = 0
    for line in valid_lines:
        dt, summary, rNumber, vdt, debit, credit, closingBalance = line.split(",")
        creditAmount = float(credit) if len(credit) > 0 else 0
        if creditAmount > 0 and is_dividend(summary):
            res_dividend += creditAmount

    return res_dividend


def process_csv_file(uploaded_file):
    try:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        all = stringio.getvalue().split("\n")
        with st.spinner(text="Ingesting Statement..."):
            st.session_state["valid_lines"] = load_statement(all)
            st.session_state["processing_error"] = None
            st.session_state["processing_success"] = True
    except:
        st.session_state["processing_error"] = "Error while processing CSV file. Please make sure you are uploading " \
                                               "correct CSV file. We currently support only HDFC bank's statements for " \
                                               "calculating dividend. "
        st.session_state["processing_success"] = False


with st.sidebar:
    st.markdown('## Share your Bank Statement')
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        process_csv_file(uploaded_file)
        if st.session_state.get("processing_error") is None:
            st.write("Statement Successfully Processed")

st.title('Calculate your dividend')
st.write("This is a simple utility to calculate the total dividend you received from your stock investments. Just upload your bank statement in CSV format in the left panel. We currently support only HDFC bank's statements.")
if st.session_state.get("processing_error") is not None:
    st.error(st.session_state.get("processing_error"), icon="🚨")
if st.session_state.get("processing_success"):
    st.success("Statement processed successfully. Please click on calculate to find your dividend for this financial year", icon="✅")

if st.button('Calculate', key='button2'):
    with st.spinner(text="Calculating"):
        valid_lines = st.session_state.get("valid_lines")
        if valid_lines is not None:
            result = calculate_dividend(valid_lines)
            st.write("Your dividend for this financial year is: " + str(result) + " INR")
        else:
            st.write("Please load bank statement first from left panel.")
