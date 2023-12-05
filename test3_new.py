#!/usr/bin/python

'This example creates a simple network topology with 1 AP and 2 stations'

from containernet.net import Containernet
from containernet.node import DockerSta, Docker
from containernet.link import TCLink
from mininet.node import RemoteController
from containernet.cli import CLI
from containernet.term import makeTerm
from mininet.log import info, setLogLevel



def topology():
    ryu_ip = '192.168.56.117'
    #ryu_ip = '30.0.3.226'
    #ryu_ip = '30.0.3.79'
    ryu_port = 6633

    net = Containernet(topo=None, ipBase='10.20.0.0/8', autoPinCpus=True)

    # autoPinCpus=True for enabling cpus param in addDocker function


    info('*** Adding docker containers\n')

    sta2_1 = net.addStation('sta2_1', mac="00:00:00:00:20:11", ip='10.20.0.11', cls=DockerSta, dimage="fayzach/fog_client:containernet", position='225.0,421.0,0', cpu_period=20000, cpu_quota=15000)
    sta2_2 = net.addStation('sta2_2', mac='00:00:00:00:20:12', ip='10.20.0.12', cls=DockerSta, dimage="fayzach/fog_client:containernet", position='576.0,414.0,0', cpu_period=50000, cpu_quota=25000)

    h2 = net.addHost("h2", ip='10.20.0.10/8', mac="00:00:00:00:20:10", cls=Docker, dimage="fayzach/fog_client:containernet", cpu_period=50000, cpu_quota=25000)

    ap2 = net.addAccessPoint('ap2', mac='00:00:00:00:20:00', dpid='20', ssid="ap2-ssid", protocols='OpenFlow13', mode="g", channel="5", position='385.0,313.0,0')

    info('*** Adding controller\n')
    c2 = net.addController('c2', controller=RemoteController, ip=ryu_ip, port=ryu_port)

    info('*** Configuring WiFi nodes\n')
    net.configureWifiNodes()

    #connect stations to ap
    sta2_1.cmd('iw dev sta2_1-wlan0 connect ap2-ssid')
    sta2_2.cmd('iw dev sta2_2-wlan0 connect ap2-ssid')

    info('*** Creating links\n')
    #net.addLink(ap2, h2, cls=TCLink, delay="5ms", bw=1000, loss=2)
    net.addLink(h2, ap2, cls=TCLink, bw=10)

    net.addNAT(name='nat0', connect=ap2, ip='10.20.0.254').configDefault()

    c2.start()
    ap2.start([c2])
    info('***  Starting network\n')
    net.start()

    info("*** Configuring vxlan \n")
    ap2.cmd('ovs-vsctl add-port ap2 b2')
    ap2.cmd('ovs-vsctl set interface b2 type=vxlan options:remote_ip=172.16.20.132')

    ap2.cmd('ovs-vsctl set bridge ap2 protocols=OpenFlow10,OpenFlow11,OpenFlow12,OpenFlow13')

    #######scenario 1
    #info("*** Configuring ap2 to scenario1 : controller is kept only for monitoring purpose, stp enabled, actions NORMAL and action flood to arp protocol  \n")
    ###ap2.cmd('ovs-vsctl del-controller ap2')
    #ap2.cmd('ovs-ofctl add-flow ap2 actions=NORMAL')
    #ap2.cmd('ovs-vsctl set bridge ap2 stp_enable=true')
    #ap2.cmd('ovs-ofctl add-flow ap2 dl_type=0x806,nw_proto=1,actions=flood')


    #####scenario 3
    info("*** Configuring ap2 to scenario3 : controller is monitoring host and path selection, stp disabled, action flood to arp protocol?  \n")
    #keep controller 
    ap2.cmd('ovs-ofctl del-flows ap2')
    ap2.cmd('ovs-vsctl set bridge ap2 stp_enable=false')
    #ap2.cmd('ovs-ofctl add-flow ap2 dl_type=0x806,nw_proto=1,actions=flood')


    #adding default route to host and stations (for internet access to install sim-app dependencies)
    #h2.cmd('route add default gw 172.17.0.1')
    h2.cmd('route add default gw 10.20.0.254')
    #sta2_1.cmd('route add default gw 172.17.0.1')
    #sta2_2.cmd('route add default gw 172.17.0.1')


    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
