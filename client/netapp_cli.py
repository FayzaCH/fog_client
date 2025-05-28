'''
    CLI adapted from the old netapp_sim application.
'''

from threading import Thread
from consts import MODE_RESOURCE
from iperf2 import iperf2_server, iperf2_kill
import time

def _list_cos(cos_names: dict):
    print()
    for id, name in cos_names.items():
        print(' ', id, '-', name, end=' ')
        if id == 1:
            print('(default)', end='')
        print()
    print()


def _send_request(send_request, cos_names, cos_id: int, data: bytes):
    print(send_request(cos_id=cos_id, data=data))
    _list_cos(cos_names)


def netapp_cli(mode: str, send_request, cos_names: dict):
    print('\nChoose a Class of Service and click ENTER to send a request')
    if mode == MODE_RESOURCE:
        print('Or wait to receive requests')
    _list_cos(cos_names)
    while True:
        cos_id = input()
        if cos_id == '':
            cos_id = 1
        try:
            cos_id = int(cos_id)
        except:
            print('Invalid CoS ID')
            _list_cos(cos_names)
        else:
            if cos_id not in cos_names:
                print('This CoS doesn\'t exist')
                _list_cos(cos_names)
            else:
                #lauch TCP and UDP iperf2 server before sending data exchange request
                iperf2_server_tcp = iperf2_server(port = 5001, udp = False, daemon = False)
                iperf2_server_udp = iperf2_server(port = 5002,udp = True, daemon = True)
                iperf2_server_tcp.launch()
                iperf2_server_udp.launch()

                t = Thread(target=_send_request,
                       args=(send_request, cos_names,
                             cos_id, b'data + program'), daemon=True)
                t.start()
                t.join()
                iperf2_kill()
                time.sleep(10)    
        