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

import logging
from vw_utilities import read_config, json_loads
from vw_vehicle import Vehicle
import vw_connection

from aiohttp import ClientSession

logging.basicConfig(level=logging.DEBUG)

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




COMPONENTS = {
    'sensor': 'sensor',
    'binary_sensor': 'binary_sensor',
    'lock': 'lock',
    'device_tracker': 'device_tracker',
    'switch': 'switch',
    'climate': 'climate'
}

RESOURCES = [
    'position',
    'distance',
    'electric_climatisation',
    'combustion_climatisation',
    'window_heater',
    'combustion_engine_heating',
    'charging',
    'adblue_level',
    'battery_level',
    'fuel_level',
    'service_inspection',
    'oil_inspection',
    'last_connected',
    'charging_time_left',
    'electric_range',
    'combustion_range',
    'combined_range',
    'charge_max_ampere',
    'climatisation_target_temperature',
    'external_power',
    'parking_light',
    'climatisation_without_external_power',
    'door_locked',
    'trunk_locked',
    'request_in_progress',
    'windows_closed',
    'sunroof_closed',
    'trip_last_average_speed',
    'trip_last_average_electric_consumption',
    'trip_last_average_auxillary_consumption',
    'trip_last_average_fuel_consumption',
    'trip_last_duration',
    'trip_last_length'
]

def is_enabled(attr):
    """Return true if the user has enabled the resource."""
    return attr in RESOURCES

async def getstats():
    """Main method."""
    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = vw_connection.Connection(session, VWUSER, VWPASS, country="fr")
        if await connection.doLogin():
            if await connection.update():
                # Print overall state
                # pprint(connection._state)

                # Print vehicles
                for vehicle in connection.vehicles:
                    pprint(vehicle)

                # get all instruments
                instruments = set()
                for vehicle in connection.vehicles:
                    dashboard = vehicle.dashboard(mutable=True)

                    for instrument in (
                            instrument
                            for instrument in dashboard.instruments
                            if instrument.component in COMPONENTS
                            and is_enabled(instrument.slug_attr)):

                        instruments.add(instrument)

                # Output all supported instruments
                res = {}
                for instrument in instruments:
                    print(f'name: {instrument.full_name}')
                    print(f'str_state: {instrument.str_state}')
                    print(f'state: {instrument.state}')
                    print(f'supported: {instrument.is_supported}')
                    print(f'attr: {instrument.attr}')
                    print(f'attributes: {instrument.attributes}')
                    res[instrument.attr] = instrument.state
                return res


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
                vwloop = asyncio.get_event_loop()
                # loop.run(main())
                results = {}
                results = vwloop.run_until_complete(asyncio.gather(getstats()))
                vwloop.close()
                results['action'] = 'VWStats'
                results['datetime'] = callwhen
                print(str(datetime.now()) + " Done, returning stats")
                send_status(redis, 'vwstats', results)
            except Exception as e:
                print(str(e))
                retrycpt -= 1
                if retrycpt >0:
                    results['retry'] = retrycpt
                    results['action'] = 'getStats'
                    send_status(redis, 'vwstats-req', results)
                else:
                    print("Too Many retries, stopping ...")
                    sys.exit(1)

            print("\n##################################################")

def send_status(redis, topic, message):
    return redis.rpush(topic, json.dumps(message))

print(str(datetime.now()) + " -- Starting Work Loop ...")
loop = asyncio.get_event_loop()
loop.run_until_complete(main())

