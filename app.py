# Rishabh bhai , take this as a sample input and put in the address bar of any browse
# after running the flask server

# http://127.0.0.1:5000/api/groundwater?state=Madhya%20Pradesh&district=Sehore&start_date=2024-01-01&end_date=2024-01-31

# will delete this later

import requests
import pandas as pd
import json
from flask import Flask, request, jsonify

app = Flask(__name__)


# --- THE CORE DATA-FETCHING LOGIC ---
def fetch_groundwater_data(state, district, start_date, end_date):
   #India - WRIS API used here 
    url = "https://indiawris.gov.in/Dataset/Ground Water Level"
    params = {
        'stateName': state,
        'districtName': district,
        'agencyName': 'CGWB',
        'startdate': start_date,
        'enddate': end_date,
        'page': '0',
        'size': '1500'
    }

    print(f"Fetching data for {district}, {state}...")
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        api_data = response.json()
        
        if api_data.get('data'):
            df = pd.DataFrame(api_data['data'])
            print("Data fetched successfully!")
            return df
        else:
            print(f"No data found. Server message: {api_data.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None


# --- THE API ENDPOINT ---
@app.route('/api/groundwater', methods=['GET'])
def get_groundwater_data():
    
    state = request.args.get('state')
    district = request.args.get('district')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # --- Input Validation ---
    if not all([state, district, start_date, end_date]):
        # 400 bad request if bad input 
        return jsonify({"error": "Missing required parameters: state, district, start_date, end_date"}), 400

    # --- Call the Logic and Format the Response ---
    groundwater_df = fetch_groundwater_data(state, district, start_date, end_date)

    if groundwater_df is not None and not groundwater_df.empty:
        result = groundwater_df.to_json(orient="records")
        return json.loads(result), 200
    else:
        # 404 error for no data found
        return jsonify({"error": "No data found for the specified parameters."}), 404


if __name__ == "__main__":
    app.run(debug=True)



