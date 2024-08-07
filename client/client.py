'''
    Main module of the client component. It can be launched through CLI or used 
    programmatically through the connect(...) method. It requests the joining 
    of a node in the orchestrated topology in one of three modes: client, 
    resource, or switch.

    In all modes, the -s/--server option is required to specify the server's 
    IP and API port. Verbosity can also be activated using the -v/--verbose 
    option, so a detailed output will be produced on the console.

    Client mode means the node participates in the orchestration but only to 
    request resources; it has no resources of its own to offer.

    Resource mode includes client mode, but the node also offers its resources 
    for use by other clients and resources.

    If the mode is 'client' or 'resource', it is possible to specify a custom 
    node ID and/or label through -i/--id and -l/--label options respectively 
    (this is useful, and sometimes necessary to avoid conflicts, in simulations 
    and/or emulations like Mininet).

    If the mode is 'resource', the usage limit can be specified through the 
    -m/--limit option (as a percentage %). Furthermore, if the simulation is 
    active, it is possible to specify simulated values for CPU, RAM, and disk 
    through the -c/--cpu, -r/--ram, and -d/--disk options respectively.

    Switch mode can be used when a switch's particular implementation is not 
    fully recognized by the controller (example: using VxLAN to establish 
    links).

    If the mode is 'switch', --dpid (-d) must be specified.

    If launched through CLI, an interface for test-sending network application 
    hosting requests would also be started, configured according to the 
    settings received from the server upon connection establishment.
'''


from os import environ
from threading import Thread
from argparse import ArgumentParser
from atexit import register as at_exit
from signal import signal, SIGINT
from logging import getLogger, INFO, WARNING
from flask import cli
from ipaddress import ip_address

from manager import Manager
from model import Node, CoS
from utils import all_exit
from netapp_cli import netapp_cli
from logger import console, file
from consts import (MODE_CLIENT, MODE_RESOURCE, MODE_SWITCH,
                    SEND_TO_BROADCAST, SEND_TO_ORCHESTRATOR)
from time import sleep

# disable flask console messages
getLogger('werkzeug').disabled = True
cli.show_server_banner = lambda *_: None

# cli options parser
parser = ArgumentParser()


def _parse_arguments():
    subparsers = parser.add_subparsers(dest='mode')
    # switch mode
    s_parser = subparsers.add_parser(MODE_SWITCH, help='Connect as switch.')
    s_parser.add_argument('-d', '--dpid', metavar='dpid', required=True,
                          help='Bridge datapath ID (in hexadecimal).')
    s_parser.add_argument('-s', '--server', metavar='server', required=True,
                          help='Server IP and API port. Format is IP:PORT.')
    s_parser.add_argument('-p3', '--iperf3', metavar='iperf3', default=None,
                          help='iPerf3 (client, server, dual).')
    s_parser.add_argument('-v', '--verbose', metavar='verbose', default=False,
                          nargs='?', const=True,
                          help='Detailed output on the console.')
    # client mode
    c_parser = subparsers.add_parser(MODE_CLIENT, help='Connect as client.')
    c_parser.add_argument('-s', '--server', metavar='server', required=True,
                          help='Server IP and API port. Format is IP:PORT.')
    c_parser.add_argument('-i', '--id', metavar='id', default=None,
                          help='Custom node ID (for simulations).')
    c_parser.add_argument('-l', '--label', metavar='label', default=None,
                          help='Custom node label (for simulations).')
    c_parser.add_argument('-p3', '--iperf3', metavar='iperf3', default=None,
                          help='iPerf3 (client, server, dual).')
    c_parser.add_argument('-v', '--verbose', metavar='verbose', default=False,
                          nargs='?', const=True,
                          help='Detailed output on the console.')
    # resource mode
    r_parser = subparsers.add_parser(
        MODE_RESOURCE, help='Connect as resource.')
    r_parser.add_argument('-s', '--server', metavar='server', required=True,
                          help='Server IP and API port. Format is IP:PORT.')
    r_parser.add_argument('-i', '--id', metavar='id', default=None,
                          help='Custom node ID (for simulations).')
    r_parser.add_argument('-l', '--label', metavar='label', default=None,
                          help='Custom node label (for simulations).')
    r_parser.add_argument('-m', '--limit', metavar='limit', default=None,
                          help='Resource usage limit percentage (%).')
    r_parser.add_argument('-c', '--cpu', metavar='cpu', default=None,
                          help='Number of simulated CPUs.')
    r_parser.add_argument('-r', '--ram', metavar='ram', default=None,
                          help='Size of simulated RAM (in MB).')
    r_parser.add_argument('-d', '--disk', metavar='disk', default=None,
                          help='Size of simulated disk (in GB).')
    r_parser.add_argument('-p3', '--iperf3', metavar='iperf3', default=None,
                          help='iPerf3 (client, server, dual).')
    r_parser.add_argument('-v', '--verbose', metavar='verbose', default=False,
                          nargs='?', const=True,
                          help='Detailed output on the console.')
    return parser.parse_args()


def connect(mode: str, server: str, node: Node = None, verbose: bool = False,
            **kwargs):
    '''
        Request the joining of a node in the orchestrated topology in one of 
        three modes: client, resource, or switch.

        Client mode means the node participates in the orchestration but only 
        to request resources; it has no resources of its own to offer.

        Resource mode includes client mode, but the node also offers its 
        resources for use by other clients and resources.

        If the mode is 'client' or 'resource', it is possible to specify a 
        custom node ID and/or label through 'id' and 'label' kwargs 
        respectively (this is useful, and sometimes necessary to avoid 
        conflicts, in simulations and/or emulations like Mininet).

        If the mode is 'resource', the usage limit can be specified through 
        the 'limit' kwarg (as a percentage %). Furthermore, if the simulation 
        is active, it is possible to specify simulated values for CPU, RAM, 
        and disk through the 'cpu', 'ram', and 'disk' kwargs respectively.

        Switch mode can be used when a switch's particular implementation is 
        not fully recognized by the controller (example: using VxLAN to 
        establish links).

        If the mode is 'switch', 'dpid' kwarg must be specified.

        By default, the Node object is automatically built from the node's real 
        data, but a custom Node object can be passed as an argument (which can 
        be useful for simulations and/or testing).

        If verbose is True, a detailed output will be produced on the console.

        Returns the Manager object.
    '''

    if mode not in (MODE_CLIENT, MODE_RESOURCE, MODE_SWITCH):
        parser.print_help()
        all_exit()

    # config console logger level
    console.setLevel(INFO if verbose else WARNING)

    try:
        server_ip, server_api_port = server.split(':')
        environ['SERVER_IP'] = ip_address(server_ip).exploded
        environ['SERVER_API_PORT'] = str(int(server_api_port))
    except:
        console.error('Server format must be IP:PORT')
        file.exception('Server format must be IP:PORT')
        all_exit()

    if mode == MODE_RESOURCE:
        environ['IS_RESOURCE'] = 'True'
        environ['RESOURCE_LIMIT'] = str(kwargs['limit'])
        environ['HOST_CPU'] = str(kwargs['cpu'])
        environ['HOST_RAM'] = str(kwargs['ram'])
        environ['HOST_DISK'] = str(kwargs['disk'])

    if mode == MODE_SWITCH:
        environ['IS_SWITCH'] = 'True'

    iperf3 = kwargs['iperf3']
    if iperf3:
        if iperf3 in ('client', 'server', 'dual'):
            environ['IPERF3_MODE'] = iperf3
        else:
            console.error('iPerf3 option must be client, server, or dual')
            all_exit()

    environ['PROTOCOL_VERBOSE'] = str(verbose)

    mgr = Manager(node, verbose)

    # disconnect at exit
    def _signal_handler(*_):
        at_exit(mgr.disconnect)
        all_exit()
    signal(SIGINT, _signal_handler)

    mgr.connect(mode, **kwargs)
    return mgr


if __name__ == '__main__':
    args = _parse_arguments()
    mode = args.mode

    if mode == MODE_CLIENT:
        connect(mode, args.server, verbose=args.verbose != False,
                id=args.id, label=args.label, iperf3=args.iperf3)
    elif mode == MODE_RESOURCE:
        connect(mode, args.server, verbose=args.verbose != False,
                id=args.id, label=args.label, limit=args.limit, cpu=args.cpu,
                ram=args.ram, disk=args.disk, iperf3=args.iperf3)
    elif mode == MODE_SWITCH:
        connect(mode, args.server, verbose=args.verbose != False,
                dpid=args.dpid, iperf3=args.iperf3)
    else:
        parser.print_help()
        all_exit()

    if mode in (MODE_CLIENT, MODE_RESOURCE):
        from protocol import PROTO_SEND_TO
        if PROTO_SEND_TO in (SEND_TO_BROADCAST, SEND_TO_ORCHESTRATOR):
            from network import MY_IP
            from resources import get_resources
            from protocol import send_request
            from gui import app

            # start gui
            app.logger.disabled = True
            Thread(target=app.run, args=('0.0.0.0',), daemon=True).start()
            console.info('GUI started at http://' + MY_IP + ':8050')

            # show host resources
            sleep(10)
            get_resources(_all=True)

            # start cli
            netapp_cli(mode, send_request, {
                cos[0]: cos[1] for cos in sorted(
                    CoS.select(fields=('id', 'name'), as_obj=False))})
