from __future__ import print_function
from datetime import datetime, timedelta
import time
from security import safe_requests

app_key = '612be68d-eb1f-4b43-935d-ab3974d758b6'
location  = 75  

def cimis_get(current_hour):
    date = datetime.now() - timedelta(days=1)
    
    # checks if time is the next day at 00:00 till 00:59, then find the cimis data that is recorded from the day before at 2400
    if (current_hour <= 0) and (date.hour > time.localtime(time.time()).tm_hour):
        # print(date)
        # print(timedelta(days=1))
        date = datetime.strftime(date - timedelta(days=1), '%Y-%m-%d')
        current_hour = 25 #kinda hacky but 25-1 is 24 so it will be at 2400
    else:
        date = datetime.now() - timedelta(days=1)
        date = date.strftime('%Y-%m-%d')

    data = cimis_api(app_key, location, date, date)

    if data is None:
        return None
    else:
        # print(data[current_hour-2])
        # do -2 for now idk why CIMIS is hour slower
        data_received = irrigation_data(data[current_hour-1]['HlyRelHum']['Value'], data[current_hour-1]['HlyAirTmp']['Value'])

        return data_received

def cimis_api(appkey, location, startDate, endDate):
    request_data = {'hly-air-tmp','hly-rel-hum'}

    request_string = ",".join(request_data)

    api_url = f'http://et.water.ca.gov/api/data?appKey={appkey}&targets={str(location)}&startDate={startDate}&endDate={endDate}&dataItems={request_string}&unitOfMeasure=M'
    response = safe_requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        # Process the data as needed
        if(data is None):
            return None    
        else:
            return data['Data']['Providers'][0]['Records']
    else:
        print("Error:", response.status_code)

class irrigation_data:
    def __init__(self, humidity,temperature):
        self.humidity = humidity
        self.temperature = temperature
    def get_humidity(self):
        return self.humidity
    def get_temperature(self):
        return self.temperature

if __name__ == "__main__":
    date = datetime.now().strftime('%Y-%m-%d')
    # print(cimis_api(app_key, location, date, date))
