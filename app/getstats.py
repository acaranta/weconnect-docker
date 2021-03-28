#!/usr/bin/python3
import asyncio
import aioredis
import json
import yaml
import glob
import sys
import os
import time

from pprint import pprint
from datetime import datetime
from pprint import pprint

from WebAPI import WeConnect

#### OPTS ####
waitTimeOnError=240
redisserver = "localhost:6379"
if os.getenv('REDIS_SRV') != None:
      redisserver = os.getenv('REDIS_SRV')

VWUSER=''
if os.getenv('VWUSER') != None:
      VWUSER = os.getenv('VWUSER')
VWPASS = ''
if os.getenv('VWPASS') != None:
      VWPASS = os.getenv('VWPASS')

COUNTRY_LANG = 'fr_FR'
if os.getenv('COUNTRY_LANG') != None:
      COUNTRY_LANG = os.getenv('COUNTRY_LANG')


vwc = WeConnect(COUNTRY_LANG)

async def main():
    # Get messages from REDIS queue
    redis = await aioredis.create_redis('redis://'+redisserver+'/0', encoding='utf-8')
    while True:

        msg = await redis.blpop('vwstats-req')
        rediscall = json.loads(msg[1])
        if rediscall['action'] == "getStats":
            print("\n##################################################")
            retrycpt = rediscall['retry']
            callwhen = str(datetime.now())
            print(callwhen + " Received call")
            print("--------------------------------------------------")
            results = {}
            try:
                vehicles = vwc.search_vehicles()
                if (vehicles and len(vehicles) > 0) and retrycpt >0:
                    print('Trying to get stats ({} tries left)'.format(retrycpt))
                    print('Found {} vehicles'.format(len(vehicles)))
                    vin = vehicles[0]['vin']
                    #results['tech'] = vwc.load_car_details(vin)
                    results['details'] = vwc.get_vehicle_details(vin)
                    #results['latest_report'] = vwc.get_latest_report()[0]
                    results['latest_trip_stat'] = vwc.get_latest_trip_statistics()
                    results['last_refuel_trip_stat'] = vwc.get_last_refuel_trip_statistics()
                    #results['vsr'] = vwc.get_vsr()
                    #results['psp_status'] = vwc.get_psp_status()
                    results['location'] = vwc.get_location()
                    results['emanager'] = vwc.get_emanager()
                    #results['get_shutdown'] = vwc.get_shutdown()

                    results['action'] = 'VWStats'
                    results['datetime'] = callwhen
                print(str(datetime.now()) + " Done, returning stats")
                send_status(redis, 'vwstats', results)
            except Exception as e:
                retrycpt -= 1
                if retrycpt >0:
                    errormsg = "Error, Retrying " + str(retrycpt) + " times left ... " + str(e)
                    print(str(datetime.now()) + " Logout/Login to WeConnect ...")
                    try:
                        vwc.logout()
                        vwc.login(VWUSER,VWPASS)
                    except Exception as ee:
                        pass
                    results['error'] = errormsg
                    print(errormsg)
                    results['retry'] = retrycpt
                    results['action'] = 'getStats'
                    send_status(redis, 'vwstats-req', results)
                else:
                    print("Too Many retries, stopping ...")
                    sys.exit(1)

            print("\n##################################################")

def send_status(redis, topic, message):
    return redis.rpush(topic, json.dumps(message))

sessionFile = "/app/weconnect.session"
if os.path.exists(sessionFile):
    print(" Removing Stale Session File : "+sessionFile)
    os.remove(sessionFile)
try :
    print(str(datetime.now()) + " Logging in WeConnect ...")
    vwc.login(VWUSER,VWPASS)
except Exception as e:
    print(str(e))
    print("Waiting "+str(waitTimeOnError)+" seconds ...")
    time.sleep(waitTimeOnError)
    sys.exit(2)
print(str(datetime.now()) + " -- Starting Work Loop ...")
loop = asyncio.get_event_loop()
loop.run_until_complete(main())

