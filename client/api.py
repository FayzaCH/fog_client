'''
    General purpose interface for using the REST API of the orchestrator, 
    providing methods that serve as a facade to hide the complexities of the 
    framework- and/or platform-specific API used. Currently supports Ryu API. 
    Methods of this interface should be redefined and/or extended for other 
    frameworks and/or platforms.

    Methods:
    --------
    get_config(): Send GET request to get the configuration of the protocol, 
    the simulation, etc.

    add_node(node): Send POST request to add node to the orchestrated topology.

    delete_node(id): Send DELETE request to delete node from the orchestrated 
    topology.

    update_node_specs(node): Send PUT request to update node specs (including 
    interface specs).

    add_request(req): Send POST request to add req to Requests database.

    add_iperf3_listeners(node): Send POST request to add iPerf3 listeners.

    get_iperf3_target(node, iface): Send GET request to get iPerf3 target for 
    given interface.

    delete_iperf3_listeners(node): Send DELETE request to delete iPerf3 
    listeners.
'''


# !!IMPORTANT!!
# This module relies on config that is only present AFTER the connect()
# method is called, so only import after


from os import getenv
from requests import get, post, put, delete
from html.parser import HTMLParser

from model import Node, Request, Interface
from common import SERVER_IP
from consts import HTTP_EXISTS, HTTP_SUCCESS
from logger import console, file
from utils import all_exit


try:
    API_PORT = int(getenv('SERVER_API_PORT', None))
except:
    console.error('Server API port invalid or missing')
    file.exception('Server API port invalid or missing')
    all_exit()


# ====================
#     MAIN METHODS
# ====================


def get_config():
    '''
        Send GET request to get the configuration of the protocol, the 
        simulation, etc.

        Returns (json, code, msg), where json is dict.
    '''

    return _ryu_get_config()


def add_node(node: Node):
    '''
        Send POST request to add node to the orchestrated topology.

        Returns (state, code, msg), where state is True if added, False if not.
    '''

    return _ryu_add_node(node)


def delete_node(node: Node):
    '''
        Send DELETE request to delete node from the orchestrated topology.

        Returns (state, code, msg), where state is True if deleted, False if 
        not.
    '''

    return _ryu_delete_node(node)


def update_node_specs(node: Node):
    '''
        Send PUT request to update node specs (including interface specs).

        Returns (state, code, msg), where state is True if updated, False if 
        not.
    '''

    return _ryu_update_node_specs(node)


def add_request(req: Request):
    '''
        Send POST request to add req to Requests database.

        Returns (state, code, msg), where state is True if added, False if not.
    '''

    return _ryu_add_request(req)


def add_iperf3_listeners(node: Node):
    '''
        Send POST request to add iPerf3 listeners.

        Returns (state, code, msg), where state is True if added, False if not.
    '''

    return _ryu_add_iperf3_listeners(node)


def get_iperf3_target(node: Node, iface: Interface):
    '''
        Send GET request to get iPerf3 target for given interface.

        Returns (json, code, msg), where json is dict.
    '''

    return _ryu_get_iperf3_target(node, iface)


def delete_iperf3_listeners(node: Node):
    '''
        Send DELETE request to delete iPerf3 listeners.

        Returns (state, code, msg), where state is True if deleted, False if 
        not.
    '''

    return _ryu_delete_iperf3_listeners(node)


# ===============
#     RYU API
# ===============


RYU_URL = 'http://' + SERVER_IP + ':' + str(API_PORT)
RYU_HEADERS = {'content-type': 'application/json'}


class _HTML(HTMLParser):
    text = ''

    def handle_data(self, data):
        self.text += data

    def get(self, text):
        self.feed(text)
        msg = self.text
        self.text = ''
        return msg


_html = _HTML()


def _ryu_request(method: str, path: str, data: dict = {}):
    try:
        url = RYU_URL + path
        method = method.upper()
        if method == 'GET':
            r = get(url, headers=RYU_HEADERS, json=data)
            code = r.status_code
            msg = _html.get(r.text)
            try:
                json = r.json()
            except:
                json = None
            return (json, code, msg) if (
                code == HTTP_SUCCESS) else (None, code, msg)
        elif method == 'POST':
            r = post(url, headers=RYU_HEADERS, json=data)
        elif method == 'PUT':
            r = put(url, headers=RYU_HEADERS, json=data)
        elif method == 'DELETE':
            r = delete(url, headers=RYU_HEADERS, json=data)
        code = r.status_code
        msg = _html.get(r.text)
        return ((code == HTTP_SUCCESS or code == HTTP_EXISTS), code, msg)
    except Exception as e:
        file.exception(e.__class__.__name__)
        return None, None, e.__class__.__name__


def _ryu_get_config():
    return _ryu_request('get', '/config')


def _ryu_add_node(node: Node):
    return _ryu_request('post', '/node', {
        'id': node.id,
        'state': node.state,
        'type': node.type.value,
        'label': node.label,
        'main_interface': node.main_interface,
        'threshold': node.threshold,
        'interfaces': [{
            'name': iface.name,
            'num': iface.num,
            'mac': iface.mac,
            'ipv4': iface.ipv4
        } for iface in node.interfaces.values()]
    })


def _ryu_delete_node(node: Node):
    return _ryu_request('delete', '/node/' + str(node.id))


def _ryu_update_node_specs(node: Node):
    return _ryu_request('put', '/node_specs/' + str(node.id), {
        'cpu_count': node.get_cpu_count(),
        'cpu_free': node.get_cpu_free(),
        'memory_total': node.get_memory_total(),
        'memory_free': node.get_memory_free(),
        'disk_total': node.get_disk_total(),
        'disk_free': node.get_disk_free(),
        'timestamp': node.get_timestamp(),
        'interfaces': [{
            'name': iface.name,
            'capacity': iface.get_capacity(),
            'bandwidth_up': iface.get_bandwidth_up(),
            'bandwidth_down': iface.get_bandwidth_down(),
            'tx_packets': iface.get_tx_packets(),
            'rx_packets': iface.get_rx_packets(),
            'tx_bytes': iface.get_tx_bytes(),
            'rx_bytes': iface.get_rx_bytes(),
            '_recv_bps': iface._recv_bps,
            'timestamp': iface.get_timestamp()
        } for iface in node.interfaces.values()]
    })


def _ryu_add_request(req: Request):
    from network import MY_IP
    return _ryu_request('post', '/request', {
        'id': req.id,
        'src': MY_IP,
        'cos_id': req.cos.id,
        'data': req.data.decode(),
        'result': req.result.decode() if req.result != None else None,
        'host': req.host,
        'state': req.state,
        'hreq_at': req.hreq_at,
        'dres_at': req.dres_at,
        'attempts': [{
            'attempt_no': attempt.attempt_no,
            'host': attempt.host,
            'state': attempt.state,
            'hreq_at': attempt.hreq_at,
            'hres_at': attempt.hres_at,
            'rres_at': attempt.rres_at,
            'dres_at': attempt.dres_at,
            'responses': [{
                'host': response.host,
                'cpu': response.cpu,
                'ram': response.ram,
                'disk': response.disk,
                'timestamp': response.timestamp,
            } for response in attempt.responses.values()]
        } for attempt in req.attempts.values()]
    })


def _ryu_add_iperf3_listeners(node: Node):
    listeners = {name: iface._iperf3_ip
                 for name, iface in node.interfaces.items()}
    listeners['_default_iperf3_ip'] = node._default_iperf3_ip
    return _ryu_request('post', '/iperf3/' + str(node.id), listeners)


def _ryu_get_iperf3_target(node: Node, iface: Interface):
    return _ryu_request('get',
                        '/iperf3/' + str(node.id) + '/' + str(iface.name))


def _ryu_delete_iperf3_listeners(node: Node):
    return _ryu_request('delete', '/iperf3/' + str(node.id))
