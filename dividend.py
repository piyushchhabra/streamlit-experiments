import streamlit as st
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime

from io import StringIO

st.set_page_config(
    page_title='AskThatman: Calculate your dividend',
    page_icon='⚡',
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


class Bank(ABC):
    @abstractmethod
    def sanitise(self, stri):
        pass

    @abstractmethod
    def load_data(self, string_data):
        pass

    @abstractmethod
    def calculate_dividend(self, valid_lines):
        pass

    @abstractmethod
    def is_dividend(self, summary):
        pass

    @abstractmethod
    def analyse(self, valid_lines, transaction_type, threshold_amount, max_amount, from_date, to_date):
        pass


class HDFC(Bank):
    def sanitise(self, stri):
        return stri.strip()

    def load_data(self, string_data):
        res = []
        for line in string_data:
            if line.count(",") == 6:
                dt, summary, vdt, debit, credit, rNumber, closingBalance = line.split(",")
                if dt is not None and dt.count("/") == 2:
                    res.append(line)
        return res

    def calculate_dividend(self, valid_lines):
        res_dividend = 0
        res_dataframe = {
            'Date': [],
            'Summary': [],
            'Credit Amount': []
        }
        for line in valid_lines:
            dt, summary, vdt, debit, credit, rNumber, closingBalance = line.split(",")
            creditAmount = float(credit) if len(credit) > 0 else 0
            if creditAmount > 0 and self.is_dividend(summary):
                res_dividend += creditAmount
                res_dataframe['Date'].append(dt)
                res_dataframe['Summary'].append(summary)
                res_dataframe['Credit Amount'].append(credit)
        return {"res_dividend": res_dividend, "res_dataframe": res_dataframe}

    def is_dividend(self, summary):
        if summary is None or len(summary) < 3:
            return False
        if summary.startswith("NEFT") or summary.startswith("UPI"):
            return False
        if "ACH C-" in summary or " DIV " in summary:
            return True
        for i in range(0, 10):
            x = " DIV" + str(i)
            if x in summary:
                return True
        return False

    def analyse(self, valid_lines, transaction_type, threshold_amount, max_amount, from_date, to_date, contains_text):
        res_dataframe = {
            'Date': [],
            'Summary': [],
            'Amount': []
        }
        for line in valid_lines:
            dt, summary, vdt, debit, credit, rNumber, closingBalance = map(str.strip, line.split(","))
            creditAmount = float(credit) if len(credit) > 0 else 0
            debitAmount = float(debit) if len(debit) > 0 else 0
            targetAmount = debitAmount if (transaction_type == "DEBIT") else creditAmount
            target = debit if (transaction_type == "DEBIT") else credit

            line_date = datetime.strptime(dt, "%d/%m/%y").date()

            summary_filter_passed = True
            if contains_text and len(contains_text.strip()) > 0:
                summary_filter_passed = contains_text.lower() in summary.lower()

            if from_date <= line_date <= to_date and targetAmount >= threshold_amount and targetAmount <= max_amount and summary_filter_passed:
                res_dataframe['Date'].append(dt)
                res_dataframe['Summary'].append(summary)
                res_dataframe['Amount'].append(target)
        return res_dataframe


class SBI(Bank):
    def sanitise(self, stri):
        special_chars = ["$", "#", "@"]
        special_one = ''
        to_transfer_index = stri.find("TO TRANSFER")
        transfer_to_index = stri.find("TRANSFER TO")
        ignore_index = []
        if to_transfer_index > -1:
            for i in range(to_transfer_index + 1, len(stri)):
                if stri[i] == ",":
                    ignore_index.append(i)
                    break
        if transfer_to_index > -1:
            for i in range(transfer_to_index + 1, len(stri)):
                if stri[i] == ",":
                    ignore_index.append(i)
                    break

        for sp in special_chars:
            if sp not in stri:
                special_one = sp
                break
        all_index = [i for i, ltr in enumerate(stri) if ltr == ","]
        for index in all_index:
            if index > 40 and index not in ignore_index and index + 1 < len(stri) and stri[index + 1].isdigit() and \
                    stri[
                        index - 1].isdigit():
                stri = stri[: index] + special_one + stri[index + 1:]

        return stri.replace(special_one, "")

    def load_data(self, string_data):
        res = []
        for line in string_data:
            line = self.sanitise(line)
            if line.count(",") == 7:
                dt, vDt, summary, ref, debit, credit, balance, nothing = line.split(",")
                if line.startswith("Txn") == False and (len(debit) > 0 or len(credit) > 0):
                    res.append(line)
        return res

    def calculate_dividend(self, valid_lines):
        res_dividend = 0
        res_dataframe = {
            'Date': [],
            'Summary': [],
            'Credit Amount': []
        }
        for line in valid_lines:
            dt, vDt, summary, ref, debit, credit, balance, nothing = line.split(",")
            credit = credit.strip()
            credit = credit.replace('"', '')
            credit = credit.replace("'", "")
            creditAmount = float(credit) if credit is not None and len(credit.strip()) > 0 else 0
            if creditAmount > 0 and self.is_dividend(summary):
                res_dividend += creditAmount
                res_dataframe['Date'].append(dt)
                res_dataframe['Summary'].append(summary)
                res_dataframe['Credit Amount'].append(credit)
        return {"res_dividend": res_dividend, "res_dataframe": res_dataframe}

    def is_dividend(self, summary):
        return "-ACHCr" in summary

    def analyse(self, valid_lines, transaction_type, threshold_amount, max_amount, from_date, to_date, contains_text):
        res_dataframe = {
            'Date': [],
            'Summary': [],
            'Amount': []
        }
        for line in valid_lines:
            dt, vDt, summary, ref, debit, credit, balance, nothing = map(str.strip, line.split(","))

            credit = credit.replace('"', '').replace("'", "")
            debit = debit.replace('"', '').replace("'", "")

            creditAmount = float(credit) if len(credit) > 0 else 0
            debitAmount = float(debit) if len(debit) > 0 else 0

            targetAmount = debitAmount if (transaction_type == "DEBIT") else creditAmount
            target = debit if (transaction_type == "DEBIT") else credit
            
            line_date = datetime.strptime(dt, "%d/%m/%y").date()

            summary_filter_passed = True
            if contains_text and len(contains_text.strip()) > 0:
                summary_filter_passed = contains_text.lower() in summary.lower()

            if from_date <= line_date <= to_date and targetAmount >= threshold_amount and targetAmount <= max_amount and summary_filter_passed:
                res_dataframe['Date'].append(dt)
                res_dataframe['Summary'].append(summary)
                res_dataframe['Amount'].append(target)
        return res_dataframe


sbi_processor = SBI()
hdfc_processor = HDFC()


def get_processor(bank):
    if bank == "HDFC":
        return hdfc_processor
    elif bank == "SBI":
        return sbi_processor
    else:
        raise Exception("Invalid Bank Provided")


def load_statement(string_data, bank):
    return get_processor(bank).load_data(string_data)


def calculate_dividend(valid_lines, bank):
    try:
        return get_processor(bank).calculate_dividend(valid_lines)
    except:
        st.session_state["processing_error"] = "Error while calculating dividend. Please try again later"
        st.session_state["processing_success"] = False


def analyse_statement(valid_lines, bank, transaction_type, threshold_amount, max_amount, from_date, to_date, contains_text):
    try:
        return get_processor(bank).analyse(valid_lines, transaction_type, threshold_amount, max_amount, from_date, to_date, contains_text)
    except:
        st.session_state["processing_error"] = "Error while analysing statement. Please try again later"
        st.session_state["processing_success"] = False


def process_statement_file(uploaded_file, bank):
    try:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        all = stringio.getvalue().split("\n")
        with st.spinner(text="Ingesting Statement..."):
            st.session_state["valid_lines"] = load_statement(all, bank)
            st.session_state['bank'] = bank
            st.session_state["processing_error"] = None
            st.session_state["processing_success"] = True
    except:
        st.session_state["processing_error"] = "Error while processing file. Please make sure you are uploading " \
                                               "correct csv file. We currently support only HDFC and SBI bank's " \
                                               "statements for calculating dividend. "
        st.session_state["processing_success"] = False


with st.sidebar:
    st.markdown('## Share your Bank Statement')
    bank = st.selectbox(
        'Choose your Bank?', ('Select Here', 'HDFC', 'SBI'))
    st.write("Please choose your bank before uploading the statement")
    uploaded_file = st.file_uploader("Choose file for bank statement", type=["csv", "DELIMITED"])
    if uploaded_file is not None:
        if bank == 'Select Here':
            st.session_state["processing_error"] = "Bank not selected. Please select bank first and try again."
            st.session_state["processing_success"] = False
            uploaded_file = None
        else:
            process_statement_file(uploaded_file, bank)
            if st.session_state.get("processing_error") is None:
                st.write("Statement Successfully Processed")


st.title('Calculate your dividend')
st.write(
    "This is a simple utility to calculate the total dividend you received from your stock investments. Just upload your bank statement in CSV format in the left panel. We currently support only HDFC and SBI bank's statements.")
if st.session_state.get("processing_error") is not None:
    st.error(st.session_state.get("processing_error"), icon="🚨")
if st.session_state.get("processing_success"):
    st.success(
        "Statement processed successfully. Please click on calculate to find your dividend for this financial year",
        icon="✅")

if st.button('Calculate Dividend', key='button2'):
    with st.spinner(text="Calculating"):
        valid_lines = st.session_state.get("valid_lines")
        if valid_lines is not None:
            result = calculate_dividend(valid_lines, st.session_state.get("bank"))
            st.write("Your dividend for this financial year is: " + str(result["res_dividend"]) + " INR")
            df = pd.DataFrame(result["res_dataframe"])
            st.table(df)
        else:
            st.write("Please load bank statement first from left panel.")


def get_date_range(valid_lines, bank):
    if not valid_lines:
        return None, None
    dates = []
    for line in valid_lines:
        try:
            date_str = line.split(",")[0].strip()
            dates.append(datetime.strptime(date_str, "%d/%m/%y").date())
        except (ValueError, IndexError):
            continue
    if not dates:
        return None, None
    return min(dates), max(dates)


if st.session_state.get("valid_lines") is not None:
    with st.spinner(text="Analysing"):
        valid_lines = st.session_state.get("valid_lines")
        st.header('Detailed statement analysis', divider='rainbow')

        min_date, max_date = get_date_range(valid_lines, st.session_state.get("bank"))

        col1, col2, col3 = st.columns(3)
        with col1:
            transaction_type = st.selectbox(
                'Transaction type?',
                ("DEBIT", "CREDIT"))

        with col2:
            threshold_amount = st.number_input(
                'Minimum amount?', value=5000, step=500)
            st.caption(f"₹ {format_inr(threshold_amount)}")
        with col3:
            max_amount = st.number_input(
                'Max amount?', value=100000, step=500)
            st.caption(f"₹ {format_inr(max_amount)}")

        if min_date and max_date:
            col4, col5, col6 = st.columns(3)
            with col4:
                from_date = st.date_input("From Date", value=min_date, min_value=min_date, max_value=max_date)
            with col5:
                to_date = st.date_input("To Date", value=max_date, min_value=min_date, max_value=max_date)
            with col6:
                contains_text = st.text_input("Contains (optional)", "", placeholder="Filter by text in summary (case-insensitive)")

        
        if st.button("Analyse", type="primary", key="button3"):
            if threshold_amount >= max_amount:
                st.error("Max amount should be greater than threshold amount")
            else:
                result_data = analyse_statement(valid_lines, st.session_state.get("bank"), transaction_type,
                                                    threshold_amount, max_amount, from_date, to_date, contains_text)
                df2 = pd.DataFrame(result_data)
                st.table(df2)
                if not df2.empty:
                    total_amount = pd.to_numeric(df2['Amount']).sum()
                    st.subheader(f"Total Amount: :blue[₹ {format_inr(total_amount)}]")
