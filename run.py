import hmac
import time
import hashlib
import requests
from urllib.parse import urlencode






""" This is a very simple script working on Binance API
- work with USER_DATA endpoint with no third party dependency
- work with testnet
Provide the API key and secret, and it's ready to go
Because USER_DATA endpoints require signature:
- call `send_signed_request` for USER_DATA endpoints
- call `send_public_request` for public endpoints

"""

KEY = '#'
SECRET = '#'
BASE_URL = 'https://dapi.binance.com' # production base url
#BASE_URL = 'https://testnet.binancefuture.com' # testnet base url

def hashing(query_string):
    return hmac.new(SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_timestamp():
    return int(time.time() * 1000)

def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json;charset=utf-8',
        'X-MBX-APIKEY': KEY
    })
    return {
        'GET': session.get,
        'DELETE': session.delete,
        'PUT': session.put,
        'POST': session.post,
    }.get(http_method, 'GET')

# used for sending request requires the signature
def send_signed_request(http_method, url_path, payload={}):
    query_string = urlencode(payload)
    # replace single quote to double quote
    query_string = query_string.replace('%27', '%22')
    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = 'timestamp={}'.format(get_timestamp())

    url = BASE_URL + url_path + '?' + query_string + '&signature=' + hashing(query_string)
    print("{} {}".format(http_method, url))
    params = {'url': url, 'params': {}}
    response = dispatch_request(http_method)(**params)
    return response.json()

# used for sending public data request
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload, True)
    url = BASE_URL + url_path
    if query_string:
        url = url + '?' + query_string
    response = dispatch_request('GET')(url=url)
    return response.json()




def order(symbol, position, quantity, positionside):
    if position == 1 :
        params = {
        "symbol": symbol,
        "side": "BUY",
        "positionSide" : positionside,
        "type": "MARKET",
        "quantity": quantity,
        }
    if position == -1 :
        params = {
        "symbol": symbol,
        "side": "SELL",
        "positionSide" : positionside,
        "type": "MARKET",
        "quantity": quantity,
        }
    response = send_signed_request('POST', '/dapi/v1/order', params)
    return response

def main(symbol,position,quantity):
    response = send_signed_request('POST', '/dapi/v1/leverage', {'symbol': symbol, 'leverage': 10})
    print(response)
    response = send_public_request('/dapi/v1/klines', {"symbol": symbol, "interval": "1m"})
    open_price = float(response[-1][4])
    if position == 1:
        response = order(symbol, position, quantity, "LONG")
        print(response)
        max_price = open_price
        while True:
            response = send_public_request('/dapi/v1/klines', {"symbol": symbol, "interval": "1m"})
            current_price = float(response[-1][4])
            if current_price > open_price:
                max_price = current_price
            if current_price <= max_price * 0.85:
                response = order(symbol, - position, quantity, "LONG")
                print(response)

                break
            if current_price <= open_price*0.95:
                hedge_price = current_price
                order(symbol, - position, quantity, "SHORT")
                min_hedge_price = hedge_price
                while True:
                    response = send_public_request('/dapi/v1/klines', {"symbol": symbol, "interval": "1m"})
                    current_price = float(response[-1][4])
                    if current_price < min_hedge_price :
                        min_hedge_price = current_price
                    if current_price >= min_hedge_price * 1.05:
                        response = order(symbol, position, quantity, "SHORT")
                        print(response)
                        break
    if position == -1:
        min_price = open_price
        response = order(symbol, position, quantity, "SHORT")
        print(response)

        while True:
            response = send_public_request('/dapi/v1/klines', {"symbol": symbol, "interval": "1m"})
            current_price = float(response[-1][4])
            if current_price < open_price:
                min_price = current_price
            if current_price >= min_price * 1.15:
                response = order(symbol, - position, quantity, "SHORT")
                print(response)
                break
            if current_price >= open_price*1.05:
                hedge_price = current_price
                response = order(symbol, - position, quantity, "LONG")
                print(response)
                max_hedge_price = hedge_price
                while True:
                    response = send_public_request('/dapi/v1/klines', {"symbol": symbol, "interval": "1m"})
                    current_price = float(response[-1][4])
                    if current_price > max_hedge_price :
                        max_hedge_price = current_price
                    if current_price >= max_hedge_price * 0.95:
                        response = order(symbol, position, quantity, "LONG")
                        print(response)
                        break


def execute(symbol, position):

    crypto = symbol.split('USD')[0]
    response = send_signed_request('GET', '/dapi/v1/balance')
    balance = 0
    for item in response :
        if item['asset'] == crypto:
            balance = float(item['balance'])
    response = send_public_request('/dapi/v1/klines', {"symbol": symbol, "interval": "1m"})
    try:
      price = float(response[-1][4])
    except:
      pass
    amount = balance *0.05 * price
    if crypto == 'BTC':
        quantity = int(amount/100)
    else:
        quantity = int(amount/10)
    main(symbol,position,quantity)


# Here you can set the symbol you want to trade and the position (1 for long -1 for short)
execute('BTCUSD_PERP', 1)
