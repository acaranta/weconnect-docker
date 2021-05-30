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

logging.basicConfig(level=logging.ERROR)

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
    'nickname',
    'model',
    'model_image',
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
    'trip_last_length',
    'outside_temperature'
]

def is_enabled(attr):
    """Return true if the user has enabled the resource."""
    return attr in RESOURCES


async def forceRefresh():
    """Main method."""
    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = vw_connection.Connection(session, VWUSER, VWPASS, country=COUNTRY_LANG)
        if await connection.doLogin():
            if await connection.update():
                res = {}
                # Print overall state
                # pprint(connection._state)

                # Print vehicles
                for vehicle in connection.vehicles:
                    await connection.setRefresh(vehicle.vin)
                    res[vehicle.vin]['action'] = 'RefreshResponse'

            return res


async def getstats():
    """Main method."""
    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = vw_connection.Connection(session, VWUSER, VWPASS, country=COUNTRY_LANG)
        if await connection.doLogin():
            if await connection.update():
                res = {}
                # Print overall state
                # pprint(connection._state)

                # Print vehicles
                for vehicle in connection.vehicles:
                    res[vehicle.vin] = {}
                    res[vehicle.vin]['vin'] = vehicle.vin
                    res[vehicle.vin]['nickname'] = vehicle.nickname
                    res[vehicle.vin]['model'] = vehicle.model
                    res[vehicle.vin]['model_year'] = vehicle.model_year
                    res[vehicle.vin]['model_image'] = vehicle.model_image
                    res[vehicle.vin]['datetime'] = str(datetime.now())
                    vehicle.setRefresh
#                    res[vehicle.vin]['trip_stats'] = vehicle.attrs.get('tripstatistics', {})

                # get all instruments
                instruments = set()
                for vehicle in connection.vehicles:
                    dashboard = vehicle.dashboard(mutable=True)

                    for instrument in (
                            instrument
                            for instrument in dashboard.instruments
                            if instrument.component in COMPONENTS):
                            #and is_enabled(instrument.slug_attr)):

                        instruments.add(instrument)

                # Output all supported instruments
                for instrument in instruments:
                    # print(f'name: {instrument.full_name}')
                    # print(f'str_state: {instrument.str_state}')
                    # print(f'state: {instrument.state}')
                    # print(f'supported: {instrument.is_supported}')
                    # print(f'attr: {instrument.attr}')
                    # print(f'attributes: {instrument.attributes}')
                    if instrument.attr == "position":
                        res[vehicle.vin]['latitude'] = instrument.state[0]
                        res[vehicle.vin]['longitude'] = instrument.state[1]
                    else:
                        res[vehicle.vin][instrument.attr] = instrument.state
                res[vehicle.vin]['action'] = 'VWStats'
                return res


async def main():
    # Get messages from REDIS queue
    redis = await aioredis.create_redis('redis://'+redisserver+'/0', encoding='utf-8')
    while True:

        msg = await redis.blpop('vwstats-req')
        rediscall = json.loads(msg[1])
        if rediscall['action'] == "getStats":
            print("\n##################Get Stats#######################")
            retrycpt = rediscall['retry']
            callwhen = str(datetime.now())
            print(callwhen + " Received call")
            print("--------------------------------------------------")
            results = {}
            res = await asyncio.gather(getstats())
            results = res[0]
#            pprint(results)
            print(str(datetime.now()) + " Done, returning stats")
            send_status(redis, 'vwstats', results)
            print("\n##################################################")

        if rediscall['action'] == "forceRefresh":
            print("\n#################Force Refresh####################")
            callwhen = str(datetime.now())
            print(callwhen + " Received call")
            print("--------------------------------------------------")
            results = {}
            res = await asyncio.gather(forceRefresh())
            results = res[0]
            print(str(datetime.now()) + " Done Requesting Data Refresh")
            send_status(redis, 'vwstats', results)
            print("\n##################################################")

def send_status(redis, topic, message):
    return redis.rpush(topic, json.dumps(message))

print(str(datetime.now()) + " -- Starting Work Loop ...")
loop = asyncio.get_event_loop()
loop.run_until_complete(main())

