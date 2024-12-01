'''
    Simulator for getting, checking, reserving and freeing resources for 
    network applications, as well as their execution based on the requirements 
    of their Classes of Service (CoS).
    
    It can also function as a proxy of monitor, applying a filter to real 
    measurements (of CPU, RAM, disk) to get simulated ones based on capacities 
    declared in conf.yml.

    Methods:
    --------
    get_resources(quiet): Returns tuple of free CPU, free RAM, and free disk.

    check_resources(request): Returns True if the current resources can satisfy 
    the requirements of request, False if not.
    
    reserve_resources(request): Subtract a quantity of resources to be reserved 
    for request from simulation variables.
    
    free_resources(request): Add back a quantity of resources reserved for 
    request to simulation variables.

    execute(data): Simulate the execution of network application by doing 
    sleeping for a determined period of time (by default randomly generated 
    between 0s and 1s).
'''


# !!IMPORTANT!!
# This module relies on config that is only present AFTER the connect()
# method is called, so only import after


from os import getenv
from threading import Lock
from random import uniform
from time import sleep, time

from .monitor import Monitor
from common import THRESHOLD, LIMIT, IS_RESOURCE
from model import Request
from logger import console, file
from utils import all_exit

from subprocess import run
from datetime import datetime, timedelta
from subprocess import run
import numpy as np
import random

try:
    MONITOR_PERIOD = float(getenv('MONITOR_PERIOD', None))
except:
    console.warning('MONITOR_PERIOD parameter invalid or missing from '
                    'received configuration. '
                    'Defaulting to 1s')
    file.warning('MONITOR_PERIOD parameter invalid or missing from received '
                 'configuration', exc_info=True)
    MONITOR_PERIOD = 1

MONITOR = Monitor(MONITOR_PERIOD)
MONITOR.start()
MEASURES = MONITOR.measures



# wait for monitor
while ('cpu_count' not in MEASURES
       or 'cpu_free' not in MEASURES
       or 'memory_total' not in MEASURES
       or 'memory_free' not in MEASURES
       or 'disk_total' not in MEASURES
       or 'disk_free' not in MEASURES):
    sleep(0.1)

_sim_on = getenv('SIMULATOR_ACTIVE', '').upper()
if _sim_on not in ('TRUE', 'FALSE'):
    console.warning('SIMULATOR:ACTIVE parameter invalid or missing from '
                    'received configuration. '
                    'Defaulting to False')
    file.warning('SIMULATOR:ACTIVE parameter (%s) invalid or missing from '
                 'received configuration', _sim_on)
    _sim_on = 'FALSE'
SIM_ON = _sim_on == 'TRUE'

_cpu = 0
_ram = 0
_disk = 0

if IS_RESOURCE:
    if SIM_ON:
        try:
            _cpu = int(getenv('HOST_CPU', None))
        except:
            console.error('CPU argument invalid or missing')
            file.exception('CPU argument invalid or missing')
            all_exit()
        try:
            _ram = float(getenv('HOST_RAM', None))
        except:
            console.error('RAM argument invalid or missing')
            file.exception('RAM argument invalid or missing')
            all_exit()
        try:
            _disk = float(getenv('HOST_DISK', None))
        except:
            console.error('Disk argument invalid or missing')
            file.exception('Disk argument invalid or missing')
            all_exit()
    else:
        _cpu = MEASURES['cpu_count']
        _ram = MEASURES['memory_total']
        _disk = MEASURES['disk_total']

CPU = _cpu
RAM = _ram
DISK = _disk
CPU_THRESHOLD = CPU * THRESHOLD
RAM_THRESHOLD = RAM * THRESHOLD
DISK_THRESHOLD = DISK * THRESHOLD

try:
    SIM_EXEC_MIN = float(getenv('SIMULATOR_EXEC_MIN', None))
    try:
        SIM_EXEC_MAX = float(getenv('SIMULATOR_EXEC_MAX', None))
        if SIM_EXEC_MAX < SIM_EXEC_MIN:
            console.warning('SIMULATOR:EXEC_MIN and SIMULATOR:EXEC_MAX '
                            'parameters invalid in received configuration. '
                            'Defaulting to [0s, 1s]')
            file.warning('SIMULATOR:EXEC_MIN and SIMULATOR:EXEC_MAX '
                         'parameters (%s and %s) invalid in received '
                         'configuration', str(SIM_EXEC_MIN), str(SIM_EXEC_MAX))
            SIM_EXEC_MIN = 0
            SIM_EXEC_MAX = 10
    except:
        console.warning('SIMULATOR:EXEC_MAX parameter invalid or missing from '
                        'received configuration. '
                        'Defaulting to [0s, 1s]')
        file.warning('SIMULATOR:EXEC_MAX parameter invalid or missing from '
                     'received configuration', exc_info=True)
        SIM_EXEC_MIN = 0
        SIM_EXEC_MAX = 10
except:
    console.warning('SIMULATOR:EXEC_MIN parameter invalid or missing from '
                    'received configuration. '
                    'Defaulting to [0s, 1s]')
    file.warning('SIMULATOR:EXEC_MIN parameter invalid or missing from '
                 'received configuration', exc_info=True)
    SIM_EXEC_MIN = 0
    SIM_EXEC_MAX = 10

# simulation variables of reserved resources
_reserved = {
    'cpu': 0.0,
    'ram': 0.0,  # in MB
    'disk': 0.0,  # in GB
}
_reserved_lock = Lock()  # for thread safety


def get_resources(quiet: bool = False, _all: bool = False):
    '''
        Returns tuple of free CPU, free RAM and free disk.
    '''

    cpu = ram = disk = 0.0
    if IS_RESOURCE:
        if SIM_ON:
            cpu = CPU - _reserved['cpu']
            ram = RAM - _reserved['ram']
            disk = DISK - _reserved['disk']
        else:
            cpu = MEASURES['cpu_free'] - _reserved['cpu']
            ram = MEASURES['memory_free'] - _reserved['ram']
            disk = MEASURES['disk_free'] - _reserved['disk']
            
    if _all:
        print('\nHost\'s real capacities')
        if not SIM_ON:
            print('    CPU COUNT  = %.2f (%.2f%s)\n'
                  '    CPU FREE   = %.2f (%.2f%s)\n'
                  '    RAM TOTAL  = %.2f MB\n'
                  '    RAM FREE   = %.2f MB\n'
                  '    DISK TOTAL = %.2f GB\n'
                  '    DISK FREE  = %.2f GB' % (MEASURES['cpu_count'],
                                                MEASURES['cpu_count']*100, '%',
                                                MEASURES['cpu_free'],
                                                MEASURES['cpu_free']*100, '%',
                                                MEASURES['memory_total'],
                                                MEASURES['memory_free'],
                                                MEASURES['disk_total'],
                                                MEASURES['disk_free']))
        else:
            print('Simulation is active, so real monitoring is unavailable')
        print()
        if IS_RESOURCE:
            print('!!!! Available for reservation !!!!!!!!! \n'
                  '    CPU  = %.2f (%.2f%s)\n'
                  '    RAM  = %.2f MB\n'
                  '    DISK = %.2f GB\n'
                  '(with an overall usage limit of %.2f%s)' % (cpu,
                                                               cpu*100, '%',
                                                               ram, disk,
                                                               LIMIT*100, '%'))
        else:
            print('No resources to offer in this mode')
        print()
    elif not quiet:
        console.info('current(cpu=%.2f, ram=%.2fMB, disk=%.2fGB)' %
                     (cpu, ram, disk))
    return cpu, ram, disk


def check_resources(req: Request, quiet: bool = False):
    '''
        Returns True if current resources can satisfy requirements of Request, 
        False if not.
    '''

    with _reserved_lock:
        min_cpu = req.get_min_cpu()
        min_ram = req.get_min_ram()
        min_disk = req.get_min_disk()
        if not quiet:
            console.info('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' %
                         (min_cpu, min_ram, min_disk))
        cpu, ram, disk = get_resources(quiet)
        return (cpu - min_cpu >= CPU_THRESHOLD
                and ram - min_ram >= RAM_THRESHOLD
                and disk - min_disk >= DISK_THRESHOLD)


def reserve_resources(req: Request):
    '''
        Add quantity of resources to be reserved for Request to simulation 
        variables.

        Returns True if reserved, False if not.
    '''

    with _reserved_lock:
        min_cpu = req.get_min_cpu()
        min_ram = req.get_min_ram()
        min_disk = req.get_min_disk()
        console.info('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' %
                     (min_cpu, min_ram, min_disk))
        cpu, ram, disk = get_resources(quiet=True)
        if (cpu - min_cpu >= CPU_THRESHOLD
                and ram - min_ram >= RAM_THRESHOLD
                and disk - min_disk >= DISK_THRESHOLD):
            _reserved['cpu'] += min_cpu
            _reserved['ram'] += min_ram
            _reserved['disk'] += min_disk
            get_resources()
            return True
        else:
            return False


def free_resources(req: Request):
    '''
        Subtract quantity of resources reserved for Request from simulation 
        variables.

        Returns True if freed, False if not.
    '''

    with _reserved_lock:
        _reserved['cpu'] -= req.get_min_cpu()
        if _reserved['cpu'] < 0:
            _reserved['cpu'] = 0.0
        _reserved['ram'] -= req.get_min_ram()
        if _reserved['ram'] < 0:
            _reserved['ram'] = 0.0
        _reserved['disk'] -= req.get_min_disk()
        if _reserved['disk'] < 0:
            _reserved['disk'] = 0.0
        get_resources()
        return True
def run_iperf2_cmd(cmd:str):
    print('cmd = %s',cmd)
    try:
        run(cmd)
    except FileNotFoundError:
        print('iperf not found.')

def execute(data: bytes, ip_src, cos_id):
    '''
        Simulate execution of network application by doing nothing for a 
        determined period of time (by default randomly generated between 0s 
        and 1s).

        Returns result.
    '''
    console.info(' exeute cos_id id  %s  with ip_src  %s', str(cos_id), str(ip_src))
    #console.info('in exeute Min = %s  Max = %s', str(SIM_EXEC_MIN), str(SIM_EXEC_MAX))

    #sleep(uniform(SIM_EXEC_MIN, SIM_EXEC_MAX))
    console.info('starting IPERF MESSAGE EXCHANGE ')
    ## depending on the cos_id value, launch an ipref exchange between this host and req_host reproducing closely the intendend class of service
    if cos_id == 1:
    #best_effort - download a web page of 3MB (maximum size of web page) under a limited bandwidth (e.g 100K bandwidth limit)
        #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host ,'-R', '-b', '100K', '-n', '3M', '-l', '12800']
        run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c' , ip_src, '-b', '100K', '-n', '3M', '-l', '12800','-i', '5'])

    elif cos_id == 2:
    #Send an image (a person’s face) of about 5MB, run the image recognition program (process of about 500 ms) and receive the result (about 500K data)
    #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-u', '-n', '5M']
        run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src,'-R', '-u', '-n', '1M','-i','5'])
        sleep(random.randinit(5,10)) #image processing lasts less than a few seconds
        #cmd=['/home/ubuntu/bin/iperf', '-c', req.host, '-u', '-R', '-n', '500K']
        run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-u', '-n', '500K','-i', '5'])

    elif cos_id == 3:
        #streaming : downloading video file of 200m under a convenient bandwidth (10m, for example)
        #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-R', '-u', '--isochronous=60:10m,1m', '-n', '200m', '-l', '1400']
        run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-u', '--isochronous=60:10m,1m', '-n', '200m', '-l', '1400','-i','5'])

    elif cos_id == 4:
         #conversational (VoIP) send and receive voip data during a time period  (4 mn is the average call duration)
         #each speaker talks for a period of 10 to 20 sec, between two consecutive speaking we apply a period of silence (0-2 sec)
         end_time = datetime.now() + timedelta(minutes=4) #current time plus 4 minutes
         while datetime.now() < end_time:
             speech_time = np.random.uniform(10,20)
             #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-u', '-S', '0xC0', '-l', '200', '-t', str(speech_time), '-b', '200k']
             run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-R', '-u', '-S', '0xC0', '-l', '200', '-t', str(speech_time), '-b', '200k','-i', '10'])
             sleep(np.random.uniform(0,2)) #delay between two consecutive messages
             speech_time = np.random.uniform(10,20)
             #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-u','-R', '-S', '0xC0', '-l', '200', '-t', str(speech_time), '-b', '200k']
             run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-u', '-S', '0xC0', '-l', '200', '-t', str(speech_time), '-b', '200k', '-i','10'])
             sleep(np.random.uniform(0,2))
    elif cos_id == 5:
         #interactive Example IpTV/WebTV
         #surfing time : 0 to 1mn, channel changing between 1 to 4 seconds
         surf_time = np.random.uniform(10,60)
         end_surf_time = datetime.now() + timedelta(seconds = surf_time)
         while datetime.now() < end_surf_time:
             change_time = np.random.uniform(1,4)
             #Interactive-Video (AF41) – ToS value 0x88
             #cmd = ['/home/ubuntu/bin/iperf','-u', '-c', req.host, '-R', '-S', '0x88', '-t', str(change_time)]
             run_iperf2_cmd(['/home/ubuntu/bin/iperf','-u', '-c', ip_src, '-S', '0x88', '-t', str(change_time),'-i','10'])
             #visualization time  : 1 mn to 1 hour
             visualization_time = np.random.uniform(60,3600) #(60,90) pour les tests
             #cmd = ['/home/ubuntu/bin/iperf', '-u', '-c', req.host, '-R', '-S', '0x88', '-t', str(visualization_time)]
             run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-u', '-c', ip_src, '-S', '0x88', '-t', str(visualization_time),'-i','10'])

    elif cos_id == 6:
             #real-time - video game example : within a long period of time (average time of a game : 1 hour) consequently exchange data (average 
             # size 100MB=100000 MB) between the client and the server (a message each 10 s) , size of the message 100000/(3600s/10s) = 277 KB
             end_time = datetime.now() + timedelta(hours=1) #current time plus 1 hour
             while datetime.now() < end_time :
                 #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-u', '-n', '100K']
                 run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-R','-u', '-n', '100K','-i','10'])
                 sleep(np.random.uniform(1,5))
                 #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-R', '-u', '-n', '100K']
                 run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-u', '-n', '100K','-i','10'])
                 sleep(np.random.uniform(5,10))

    elif cos_id == 7:
                    # mission_critical example (e-health)  During a time period (30 seconds in this example) periodically sends short messages from client node
                    # to server node, representing the patient’s vital signs.  Then randomly receive or not a recommendation from the server (we set the 
                    # probability to receive recommendations to the value of 0.1, since a recommendation means applying changes or triggering some actions on 
                    # the care protocol)
                    t_end = time() + 60 * 10 #experience duration 10 mn
                    while time() < t_end:
                        send_recommendation = np.random.choice([True, False],10, p=[0.1, 0.9])  #10 probability the sent value triggers a recommendation send-back
                        for i in range (10):
                            #cmd = ['/home/ubuntu/bin/iperf', '-c', req.host, '-n', '2K']
                            run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-R','-n', '2K','-i','10'])
                            if send_recommendation[i] :
                                #cmd  = ['/home/ubuntu/bin/iperf', '-c', req.host, '-R', '-l', '500K']
                                run_iperf2_cmd(['/home/ubuntu/bin/iperf', '-c', ip_src, '-l', '500K','-i','10'])
                        sleep(30)
    else:
        console.warning("cos_id not between 1 and 7")

    console.info('ending IPERF MESSAGES EXCHANGE')


    #sleep(uniform(SIM_EXEC_MIN, SIM_EXEC_MAX))
    return b'result'
