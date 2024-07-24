import streamlit as st
import pandas as pd
from abc import ABC, abstractmethod

from io import StringIO

st.set_page_config(
    page_title='AskThatman: Calculate your dividend',
    page_icon='⚡',
    layout='wide',
    initial_sidebar_state='auto',
)


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
    def analyse(self, valid_lines, transaction_type, threshold_amount):
        pass


class HDFC(Bank):
    def sanitise(self, stri):
        return stri.strip()

    def load_data(self, string_data):
        res = []
        for line in string_data:
            if line.count(",") == 6:
                dt, summary, rNumber, vdt, debit, credit, closingBalance = line.split(",")
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
            dt, summary, rNumber, vdt, debit, credit, closingBalance = line.split(",")
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

    def analyse(self, valid_lines, transaction_type, threshold_amount):
        res_dataframe = {
            'Date': [],
            'Summary': [],
            'Amount': []
        }
        for line in valid_lines:
            dt, summary, rNumber, vdt, debit, credit, closingBalance = line.split(",")
            creditAmount = float(credit) if len(credit) > 0 else 0
            debitAmount = float(debit) if len(debit) > 0 else 0
            targetAmount = debitAmount if (transaction_type == "DEBIT") else creditAmount
            target = debit if (transaction_type == "DEBIT") else credit
            if targetAmount > threshold_amount:
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

    def analyse(self, valid_lines, transaction_type, threshold_amount):
        return None


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


def analyse_statement(valid_lines, bank, transaction_type, threshold_amount):
    try:
        return get_processor(bank).analyse(valid_lines, transaction_type, threshold_amount)
    except:
        st.session_state["processing_error"] = "Error while analysing statement. Please try again later"
        st.session_state["processing_success"] = False



def process_csv_file(uploaded_file, bank):
    try:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        all = stringio.getvalue().split("\n")
        with st.spinner(text="Ingesting Statement..."):
            st.session_state["valid_lines"] = load_statement(all, bank)
            st.session_state['bank'] = bank
            st.session_state["processing_error"] = None
            st.session_state["processing_success"] = True
    except:
        st.session_state["processing_error"] = "Error while processing CSV file. Please make sure you are uploading " \
                                               "correct CSV file. We currently support only HDFC and SBI bank's " \
                                               "statements for calculating dividend. "
        st.session_state["processing_success"] = False


with st.sidebar:
    st.markdown('## Share your Bank Statement')
    bank = st.selectbox(
        'Choose your Bank?', ('Select Here', 'HDFC', 'SBI'))
    st.write("Please choose your bank before uploading the statement")
    uploaded_file = st.file_uploader("Choose CSV file for bank statement", type="csv")
    if uploaded_file is not None:
        if bank == 'Select Here':
            st.session_state["processing_error"] = "Bank not selected. Please select bank first and try again."
            st.session_state["processing_success"] = False
            uploaded_file = None
        else:
            process_csv_file(uploaded_file, bank)
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


if st.session_state.get("bank") == "HDFC" and st.session_state.get("valid_lines") is not None:
    with st.spinner(text="Analysing"):
        valid_lines = st.session_state.get("valid_lines")
        st.header('Detailed statement analysis', divider='rainbow')
        col1, col2, col3 = st.columns(3)
        with col1:
            transaction_type = st.selectbox(
                'Transaction type?',
                ("DEBIT", "CREDIT"))

        with col2:
            threshold_amount = st.selectbox(
                'Threshold amount?',
                (5000, 10000, 25000, 50000, 75000, 100000, 120000, 140000))
        if st.button("Analyse", type="primary", key="button3"):
            df2 = pd.DataFrame(analyse_statement(valid_lines, st.session_state.get("bank"), transaction_type, threshold_amount))
            st.table(df2)
