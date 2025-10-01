## My Streamlit Experiments
This repository contains my experiments with [Streamlit]("https://streamlit.io/")

I love automating boring stuff in Python, and I use **Streamlit** to deploy those automations to share my work with other people.

My automations are hosted on Streamlit Community Cloud. You can access them using below links:


### Ask Dividend
It's a simple utility I use to calculate the dividend amount I received from my stock investments. It takes my bank statement
as an input and process it to calculate the dividend that was credited to my bak account.
Checkout: https://ask-dividend.streamlit.app/

### Run it Locally
1. Make sure you have python installed locally. You can download it from [here](https://www.python.org/downloads/)
2. Clone the repository and install dependencies
```shell
git clone https://github.com/piyush-chhabra/streamlit-experiments.git
cd streamlit-experiments
python3 -m venv myenv
source myenv/bin/activate   
pip3 install -r requirements.txt
```
3. Run the app
```shell
streamlit run dividend.py
```