#DISCLAIMER:
#1) This sample code is for learning purposes only.
#2) Always be very careful when dealing with codes in which you can place orders in your account.
#3) The actual results may or may not be similar to backtested results. The historical results do not guarantee any profits or losses in the future.
#4) You are responsible for any losses/profits that occur in your account in case you plan to take trades in your account.
#5) TFU and Aseem Singhal do not take any responsibility of you running these codes on your account and the corresponding profits and losses that might occur.
#6) The running of the code properly is dependent on a lot of factors such as internet, broker, what changes you have made, etc. So it is always better to keep checking the trades as technology error can come anytime.
#7) This is NOT a tip providing service/code.
#8) This is NOT a software. Its a tool that works as per the inputs given by you.
#9) Slippage is dependent on market conditions.
#10) Option trading and automatic API trading are subject to market risks

from kiteconnect import KiteConnect
import datetime
import time
import requests
from datetime import timedelta
from pytz import timezone
import pandas as pd
import json
import pytz
from urllib3.exceptions import ProtocolError
######PIVOT POINTS##########################
####################__INPUT__#####################

def getNiftyExpiryDate():
    nifty_expiry = {
        datetime.datetime(2025, 12, 30).date(): '25DEC',
        datetime.datetime(2026, 1, 6).date(): '26106',
        datetime.datetime(2026, 1, 13).date(): '26113',
        datetime.datetime(2026, 1, 20).date(): '26120',
        datetime.datetime(2026, 1, 27).date(): '26JAN',
        datetime.datetime(2026, 2, 3).date(): '26203',
        datetime.datetime(2026, 2, 10).date(): '26210',
        datetime.datetime(2026, 2, 17).date(): '26217',
        datetime.datetime(2026, 2, 24).date(): '26FEB',
        datetime.datetime(2026, 3, 3).date(): '26302',
        datetime.datetime(2026, 3, 10).date(): '26310',
        datetime.datetime(2026, 3, 17).date(): '26317',
        datetime.datetime(2026, 3, 24).date(): '26324',
        datetime.datetime(2026, 3, 31).date(): '26MAR',
        datetime.datetime(2026, 4, 7).date(): '26407',
        datetime.datetime(2026, 4, 14).date(): '26413',
        datetime.datetime(2026, 4, 21).date(): '26421',
        datetime.datetime(2026, 4, 28).date(): '26APR',
        datetime.datetime(2026, 5, 5).date(): '26505',
        datetime.datetime(2026, 5, 12).date(): '26512',
        datetime.datetime(2026, 5, 19).date(): '26519',
        datetime.datetime(2026, 5, 26).date(): '26MAY',
        datetime.datetime(2026, 6, 2).date(): '26602',
        datetime.datetime(2026, 6, 9).date(): '26609',
        datetime.datetime(2026, 6, 16).date(): '26616',
        datetime.datetime(2026, 6, 23).date(): '26623',
        datetime.datetime(2026, 6, 30).date(): '26JUN',
        datetime.datetime(2026, 7, 7).date(): '26707',
        datetime.datetime(2026, 7, 14).date(): '26714',
        datetime.datetime(2026, 7, 21).date(): '26721',
        datetime.datetime(2026, 7, 28).date(): '26JUL',
        datetime.datetime(2026, 8, 4).date(): '26804',
        datetime.datetime(2026, 8, 11).date(): '26811',
        datetime.datetime(2026, 8, 18).date(): '26818',
        datetime.datetime(2026, 8, 25).date(): '26AUG',
        datetime.datetime(2026, 9, 1).date(): '26901',
        datetime.datetime(2026, 9, 8).date(): '26908',
        datetime.datetime(2026, 9, 15).date(): '26915',
        datetime.datetime(2026, 9, 22).date(): '26922',
        datetime.datetime(2026, 9, 29).date(): '26SEP',
        datetime.datetime(2026, 10, 6).date(): '26O06',
        datetime.datetime(2026, 10, 13).date(): '26O13',
        datetime.datetime(2026, 10, 20).date(): '26O19',
        datetime.datetime(2026, 10, 27).date(): '26OCT',
        datetime.datetime(2026, 11, 3).date(): '26N03',
        datetime.datetime(2026, 11, 10).date(): '26N09',
        datetime.datetime(2026, 11, 17).date(): '26N17',
        datetime.datetime(2026, 11, 24).date(): '26NOV',
        datetime.datetime(2026, 12, 1).date(): '26D01',
        datetime.datetime(2026, 12, 8).date(): '26D08',
        datetime.datetime(2026, 12, 15).date(): '26D15',
        datetime.datetime(2026, 12, 22).date(): '26D22',
        datetime.datetime(2026, 12, 29).date(): '26DEC',
    }


    today = datetime.datetime.now().date()

    for date_key, value in nifty_expiry.items():
        if today <= date_key:
            print(value)
            return value

def getSensexExpiryDate():
    sensex_expiry = {
        datetime.datetime(2026, 1, 1).date(): '26101',
        datetime.datetime(2026, 1, 8).date(): '26108',
        datetime.datetime(2026, 1, 15).date(): '26115',
        datetime.datetime(2026, 1, 22).date(): '26122',
        datetime.datetime(2026, 1, 29).date(): '26JAN',
        datetime.datetime(2026, 2, 5).date(): '26205',
        datetime.datetime(2026, 2, 12).date(): '26212',
        datetime.datetime(2026, 2, 19).date(): '26219',
        datetime.datetime(2026, 2, 26).date(): '26FEB',
        datetime.datetime(2026, 3, 5).date(): '26305',
        datetime.datetime(2026, 3, 12).date(): '26312',
        datetime.datetime(2026, 3, 19).date(): '26319',
        datetime.datetime(2026, 3, 26).date(): '26MAR',
        datetime.datetime(2026, 4, 2).date(): '26402',
        datetime.datetime(2026, 4, 9).date(): '26409',
        datetime.datetime(2026, 4, 16).date(): '26416',
        datetime.datetime(2026, 4, 23).date(): '26423',
        datetime.datetime(2026, 4, 30).date(): '26APR',
        datetime.datetime(2026, 5, 7).date(): '26507',
        datetime.datetime(2026, 5, 14).date(): '26514',
        datetime.datetime(2026, 5, 21).date(): '26521',
        datetime.datetime(2026, 5, 28).date(): '26MAY',
        datetime.datetime(2026, 6, 4).date(): '26604',
        datetime.datetime(2026, 6, 11).date(): '26611',
        datetime.datetime(2026, 6, 18).date(): '26618',
        datetime.datetime(2026, 6, 25).date(): '26JUN',
        datetime.datetime(2026, 7, 2).date(): '26702',
        datetime.datetime(2026, 7, 9).date(): '26709',
        datetime.datetime(2026, 7, 16).date(): '26716',
        datetime.datetime(2026, 7, 23).date(): '26723',
        datetime.datetime(2026, 7, 30).date(): '26JUL',
        datetime.datetime(2026, 8, 6).date(): '26806',
        datetime.datetime(2026, 8, 13).date(): '26813',
        datetime.datetime(2026, 8, 20).date(): '26820',
        datetime.datetime(2026, 8, 27).date(): '26AUG',
        datetime.datetime(2026, 9, 3).date(): '26903',
        datetime.datetime(2026, 9, 10).date(): '26910',
        datetime.datetime(2026, 9, 17).date(): '26917',
        datetime.datetime(2026, 9, 24).date(): '26SEP',
        datetime.datetime(2026, 10, 1).date(): '26O01',
        datetime.datetime(2026, 10, 8).date(): '26O08',
        datetime.datetime(2026, 10, 15).date(): '26O15',
        datetime.datetime(2026, 10, 22).date(): '26O22',
        datetime.datetime(2026, 10, 29).date(): '26OCT',
        datetime.datetime(2026, 11, 5).date(): '26N05',
        datetime.datetime(2026, 11, 12).date(): '26N12',
        datetime.datetime(2026, 11, 19).date(): '26N19',
        datetime.datetime(2026, 11, 26).date(): '26NOV',
        datetime.datetime(2026, 12, 3).date(): '26D03',
        datetime.datetime(2026, 12, 10).date(): '26D10',
        datetime.datetime(2026, 12, 17).date(): '26D17',
        datetime.datetime(2026, 12, 24).date(): '26D24',
        datetime.datetime(2026, 12, 31).date(): '26DEC',
    }


    today = datetime.datetime.now().date()

    for date_key, value in sensex_expiry.items():
        if today <= date_key:
            print(value)
            return value

def getBankNiftyExpiryDate():
    return getStockExpiryDate()

def getFinNiftyExpiryDate():
    return getStockExpiryDate()

def getStockExpiryDate():
    stock_expiry = {
        datetime.datetime(2026, 1, 27).date(): "26JAN",
        datetime.datetime(2026, 2, 24).date(): "26FEB",
        datetime.datetime(2026, 3, 31).date(): "26MAR",
        datetime.datetime(2026, 4, 28).date(): "26APR",
        datetime.datetime(2026, 5, 26).date(): "26MAY",
        datetime.datetime(2026, 6, 30).date(): "26JUN",
        datetime.datetime(2026, 7, 28).date(): "26JUL",
        datetime.datetime(2026, 8, 25).date(): "26AUG",
        datetime.datetime(2026, 9, 29).date(): "26SEP",
        datetime.datetime(2026, 10, 27).date(): "26OCT",
        datetime.datetime(2026, 11, 24).date(): "26NOV",
        datetime.datetime(2026, 12, 29).date(): "26DEC",
    }

    today = datetime.datetime.now().date()

    for date_key, value in stock_expiry.items():
        if today <= date_key:
            return value

def getNiftyNextExpiryDate():
    nifty_expiry = {
        datetime.datetime(2026, 1, 6).date(): '26113',
        datetime.datetime(2026, 1, 13).date(): '26120',
        datetime.datetime(2026, 1, 20).date(): '26JAN',
        datetime.datetime(2026, 1, 27).date(): '26203',
        datetime.datetime(2026, 2, 3).date(): '26210',
        datetime.datetime(2026, 2, 10).date(): '26217',
        datetime.datetime(2026, 2, 17).date(): '26FEB',
        datetime.datetime(2026, 2, 24).date(): '26302',
        datetime.datetime(2026, 3, 3).date(): '26310',
        datetime.datetime(2026, 3, 10).date(): '26317',
        datetime.datetime(2026, 3, 17).date(): '26324',
        datetime.datetime(2026, 3, 24).date(): '26MAR',
        datetime.datetime(2026, 3, 31).date(): '26407',
        datetime.datetime(2026, 4, 7).date(): '26413',
        datetime.datetime(2026, 4, 14).date(): '26421',
        datetime.datetime(2026, 4, 21).date(): '26APR',
        datetime.datetime(2026, 4, 28).date(): '26505',
        datetime.datetime(2026, 5, 5).date(): '26512',
        datetime.datetime(2026, 5, 12).date(): '26519',
        datetime.datetime(2026, 5, 19).date(): '26MAY',
        datetime.datetime(2026, 5, 26).date(): '26602',
        datetime.datetime(2026, 6, 2).date(): '26609',
        datetime.datetime(2026, 6, 9).date(): '26616',
        datetime.datetime(2026, 6, 16).date(): '26623',
        datetime.datetime(2026, 6, 23).date(): '26JUN',
        datetime.datetime(2026, 6, 30).date(): '26707',
        datetime.datetime(2026, 7, 7).date(): '26714',
        datetime.datetime(2026, 7, 14).date(): '26721',
        datetime.datetime(2026, 7, 21).date(): '26JUL',
        datetime.datetime(2026, 7, 28).date(): '26804',
        datetime.datetime(2026, 8, 4).date(): '26811',
        datetime.datetime(2026, 8, 11).date(): '26818',
        datetime.datetime(2026, 8, 18).date(): '26AUG',
        datetime.datetime(2026, 8, 25).date(): '26901',
        datetime.datetime(2026, 9, 1).date(): '26908',
        datetime.datetime(2026, 9, 8).date(): '26915',
        datetime.datetime(2026, 9, 15).date(): '26922',
        datetime.datetime(2026, 9, 22).date(): '26SEP',
        datetime.datetime(2026, 9, 29).date(): '26O06',
        datetime.datetime(2026, 10, 6).date(): '26O13',
        datetime.datetime(2026, 10, 13).date(): '26O19',
        datetime.datetime(2026, 10, 20).date(): '26OCT',
        datetime.datetime(2026, 10, 27).date(): '26N03',
        datetime.datetime(2026, 11, 3).date(): '26N09',
        datetime.datetime(2026, 11, 10).date(): '26N17',
        datetime.datetime(2026, 11, 17).date(): '26NOV',
        datetime.datetime(2026, 11, 24).date(): '26D01',
        datetime.datetime(2026, 12, 1).date(): '26D08',
        datetime.datetime(2026, 12, 8).date(): '26D15',
        datetime.datetime(2026, 12, 15).date(): '26D22',
        datetime.datetime(2026, 12, 22).date(): '26DEC',
        datetime.datetime(2026, 12, 29).date(): '26DEC',
    }


    today = datetime.datetime.now().date()

    for date_key, value in nifty_expiry.items():
        if today <= date_key:
            return value

def getExpiryFormat(year, month, day, monthly):
    if monthly == 0:
        day1 = day
        if month == "JAN":
            month1 = 1
        elif month == "FEB":
            month1 = 2
        elif month == "MAR":
            month1 = 3
        elif month == "APR":
            month1 = 4
        elif month == "MAY":
            month1 = 5
        elif month == "JUN":
            month1 = 6
        elif month == "JUL":
            month1 = 7
        elif month == "AUG":
            month1 = 8
        elif month == "SEP":
            month1 = 9
        elif month == "OCT":
            month1 = "O"
        elif month == "NOV":
            month1 = "N"
        elif month == "DEC":
            month1 = "D"
    elif monthly == 1:
        day1 = ""
        month1 = month

    return str(year)+str(month1)+str(day1)

def getIndexSpot(stock):
    if stock == "BANKNIFTY":
        name = "NSE:NIFTY BANK"
    elif stock == "NIFTY":
        name = "NSE:NIFTY 50"
    elif stock == "FINNIFTY":
        name = "NSE:NIFTY FIN SERVICE"
    elif stock == "SENSEX":
        name = "BSE:SENSEX"

    return name

def getOptionFormat(stock, intExpiry, strike, ce_pe):
    return "NFO:" + str(stock) + str(intExpiry)+str(strike)+str(ce_pe)

def getOptionFormat_bfo(stock, intExpiry, strike, ce_pe):
    return "BFO:" + str(stock) + str(intExpiry)+str(strike)+str(ce_pe)

def getOptionFormat_bse(stock, intExpiry, strike, ce_pe):
    return "BSE:" + str(stock) + str(intExpiry)+str(strike)+str(ce_pe)

def getLTP(instrument):
    url = "http://localhost:4000/ltp?instrument=" + instrument
    try:
        resp = requests.get(url)
    except Exception as e:
        print(e)
    data = resp.json()
    return data

def getQuotes(instrument):
    try:
        with open("zerodha_data.json", "r") as f:
            result = json.load(f)
        return float(result.get(instrument, None))
    except (FileNotFoundError, ValueError, TypeError):
        return -1

def manualLTP(symbol,kc):
    temp = kc.ltp(symbol)
    return temp[symbol]['last_price']

def placeOrder(inst ,t_type,qty,order_type,price,variety, kc,papertrading=0,productType="intraday_eq"):
    exch = inst[:3]
    symb = inst[4:]
    #papertrading = 0 #if this is 1, then real trades will be placed
    dt = datetime.datetime.now()
    print(dt.hour,":",dt.minute,":",dt.second ," => ",t_type," ",symb," ",qty," ",order_type)

    if productType == "intraday_eq":
        productType = kc.PRODUCT_MIS
    elif productType == "positional_eq":
        productType = kc.PRODUCT_CNC
    elif productType == "intraday_fno":
        productType = kc.PRODUCT_MIS
    elif productType == "positional_fno":
        productType = kc.PRODUCT_NRML
    else:
        productType = kc.PRODUCT_MIS

    try:
        if (papertrading == 1):
            order_id  = kc.place_order( variety = variety,
                                        tradingsymbol= symb ,
                                        exchange= exch,
                                        transaction_type= t_type,
                                        quantity= qty,
                                        market_protection=-1,
                                        order_type=order_type,
                                        product=productType,
                                        price=price,
                                        trigger_price=price)


            print(dt.hour,":",dt.minute,":",dt.second ," => ", symb , int(order_id) )
            return order_id
        else:
            return 0

    except Exception as e:
        print(dt.hour,":",dt.minute,":",dt.second ," => ", symb , "Failed : {} ".format(e))

def fetch_with_retry(instrument,range_from, range_to,interval_str, kc, retries=3):
    for i in range(retries):
        try:
            return kc.historical_data(instrument,range_from, range_to,interval_str)
        except (ProtocolError, Exception) as e:
            print(f"Helper Attempt {i+1} failed: {e}. Retrying...")
            #send_telegram_alert(f"Attempt {i+1} failed: {e}. Retrying...")
            time.sleep(2) # Wait 2 seconds before retrying
    return None

def getHistorical(ticker,interval,duration,kc):
    instrument_dump = kc.instruments(ticker[:3])
    instrument_df = pd.DataFrame(instrument_dump)

    range_from = datetime.datetime.today()-timedelta(duration)
    range_to = datetime.datetime.today()
    symb = ticker[4:]

    if interval == 1:
        interval_str = "minute"
    elif interval == 3:
        interval_str = "3minute"
    elif interval == 5:
        interval_str = "5minute"
    elif interval == 10:
        interval_str = "10minute"
    elif interval == 15:
        interval_str = "15minute"
    elif interval == 30:
        interval_str = "30minute"
    elif interval == 60:
        interval_str = "60minute"
    interval_str = "minute"
    instrument = instrument_df[instrument_df.tradingsymbol==symb].instrument_token.values[0]

    #if(symb=="NIFTY 50"):
    #    instruments = kc.instruments("NFO")
    #    nifty_fut = [ins for ins in instruments if ins['name'] == 'NIFTY' and ins['segment'] == 'NFO-FUT'][0]
    #    instrument = nifty_fut['instrument_token']
        #print(f"Use this token: {nifty_fut['instrument_token']} for {nifty_fut['tradingsymbol']}")
        #exit()

    ### NEW CODE####
    temp = kc.historical_data(instrument,range_from, range_to,interval_str)
    #temp = fetch_with_retry(instrument,range_from, range_to,interval_str, kc)
    for entry in temp:
        entry['date'] = entry['date'].timestamp()
    data = pd.DataFrame(temp)
    # Convert 'date' back to datetime if needed
    data['date'] = pd.to_datetime(data['date'], unit='s')
    data['date'] = data['date'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    ###

    ###OLD CODE
    #data = pd.DataFrame(kc.historical_data(instrument,range_from, range_to,interval_str))
    ###
    data['datetime2'] = data['date'].copy()

    data.set_index("date",inplace=True)
    #filtered_df = data[data.index.time < pd.to_datetime('15:30:00').time()]
    filtered_df = data[(data.index.time >= pd.to_datetime("09:15:00").time()) &
                       (data.index.time <= pd.to_datetime("15:29:00").time())]

    # Function to calculate dynamic origin based on the date (9:15 AM IST)
    def get_daily_origin(date):
        return pytz.timezone('Asia/Kolkata').localize(datetime.datetime(date.year, date.month, date.day, 9, 15))

    # Create the dynamic resampling logic for each day
    resampled_df_list = []

    for date, group in filtered_df.groupby(filtered_df.index.date):
        # Get the dynamic origin for the current day
        origin = get_daily_origin(date)

        # Resample each day's group based on the 'interval' you want (e.g., 30min, 35min, etc.)
        resampled_day = group.resample(f'{interval}min', label='left', origin=origin).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'datetime2': 'first'
        })

        # Append the resampled data to the list
        resampled_df_list.append(resampled_day)

    # Combine the resampled data from all days
    final_resampled_df = pd.concat(resampled_df_list)

    # Drop rows with missing 'open' values
    final_resampled_df = final_resampled_df.dropna(subset=['open'])

    return final_resampled_df


def getHistorical_Feb2025(ticker,interval,duration,kc):
    instrument_dump = kc.instruments(ticker[:3])
    instrument_df = pd.DataFrame(instrument_dump)

    range_from = datetime.datetime.today()-timedelta(duration)
    range_to = datetime.datetime.today()
    symb = ticker[4:]

    if interval == 1:
        interval_str = "minute"
    elif interval == 3:
        interval_str = "3minute"
    elif interval == 5:
        interval_str = "5minute"
    elif interval == 10:
        interval_str = "10minute"
    elif interval == 15:
        interval_str = "15minute"
    elif interval == 30:
        interval_str = "30minute"
    elif interval == 60:
        interval_str = "60minute"
    interval_str = "minute"
    instrument = instrument_df[instrument_df.tradingsymbol==symb].instrument_token.values[0]
    ### NEW CODE####
    temp = kc.historical_data(instrument,range_from, range_to,interval_str)
    for entry in temp:
        entry['date'] = entry['date'].timestamp()
    data = pd.DataFrame(temp)
    # Convert 'date' back to datetime if needed
    data['date'] = pd.to_datetime(data['date'], unit='s')
    data['date'] = data['date'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    ###

    ###OLD CODE
    #data = pd.DataFrame(kc.historical_data(instrument,range_from, range_to,interval_str))
    ###
    data['datetime2'] = data['date'].copy()

    data.set_index("date",inplace=True)
    #filtered_df = data[data.index.time < pd.to_datetime('15:30:00').time()]
    filtered_df = data[(data.index.time >= pd.to_datetime("09:15:00").time()) &
                       (data.index.time <= pd.to_datetime("15:29:00").time())]

    #finaltimeframe = str(interval)  + "min"
    if interval < 375:
        finaltimeframe = str(interval)  + "min"
    elif interval == 375:
        finaltimeframe = "D"

    # Resample to a specific time frame, for example, 30 minutes
    resampled_df = filtered_df.resample(finaltimeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'datetime2': 'first'
    })

    # If you want to fill any missing values with a specific method, you can use fillna
    #resampled_df = resampled_df.fillna(method='ffill')  # Forward fill

    #print(resampled_df)
    resampled_df = resampled_df.dropna(subset=['open'])
    return resampled_df

def getHistorical_old(ticker,interval,duration,kc):
    instrument_dump = kc.instruments(ticker[:3])
    instrument_df = pd.DataFrame(instrument_dump)

    range_from = datetime.datetime.today()-timedelta(duration)
    range_to = datetime.datetime.today()
    symb = ticker[4:]

    if interval == 1:
        interval_str = "minute"
    elif interval == 3:
        interval_str = "3minute"
    elif interval == 5:
        interval_str = "5minute"
    elif interval == 10:
        interval_str = "10minute"
    elif interval == 15:
        interval_str = "15minute"
    elif interval == 30:
        interval_str = "30minute"
    elif interval == 60:
        interval_str = "60minute"

    instrument = instrument_df[instrument_df.tradingsymbol==symb].instrument_token.values[0]
    data = pd.DataFrame(kc.historical_data(instrument,range_from, range_to,interval_str))
    data.set_index("date",inplace=True)
    filtered_df = data[data.index.time < pd.to_datetime('15:30:00').time()]
    return filtered_df