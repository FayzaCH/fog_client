import subprocess
import os
import signal
import re
from logger import console, file
'''
classe iperf2_server(port_number, Daemon_Mode, UDP_protocol)
port_number : default "5001"
Daemon_Mode default "True"
UDP_protocole : default "False" (so TCP)
'''

class iperf2_server:
    def __init__(self, port=5001, daemon=True, udp=False):
        self.port = port
        self.daemon = daemon
        self.udp=udp

    def _is_iperf_running(self):
        """Search if iperf2 process is already running, then check if it runs in udp or tcp mode."""
        iperf2_tcp = False
        iperf2_udp= False
        try:
            # list all runinng processes
            process = subprocess.run(['ps', 'aux'], capture_output=True, text=True, check=True)
            lines = process.stdout.splitlines()

            # Filter only lines containing "iperf"
            lines_iperf = [line for line in lines if "iperf" in line]

            if lines_iperf:
                #console.info('Iperf Process found  :')
                for line in lines_iperf:
                    #print(line)
                    if "-u" in line:
                        #print("    -u option is used  (UDP mode).")
                        iperf2_udp= True
                    else:
                        #print("    -u option isn't used (TCP mode).")
                        iperf2_tcp= True
            else:
                console.info('    No iperf processes found. Launching iperf server')
                file.info('    No iperf processes found. Launching iperf server')
            return iperf2_tcp,iperf2_udp

        except subprocess.CalledProcessError as e:
            console.error('Error when  running ps: %s',str(e))
        except FileNotFoundError:
            console.error("ps command not found.")


    def launch(self):
        iperf2_tcp, iperf2_udp = self._is_iperf_running()
        #print("iperf2_tcp: ",iperf2_tcp, "iperf2_udp: ", iperf2_udp)

        try:
            cmd=["/bin/iperf","-s","-p",str(self.port),"-i","1"]
            if self.daemon:
                cmd.append("-D")
            if self.udp:
                cmd.append("-u")
            #check if iperf2 is already launched
            #output = subprocess.Popen(cmd,stdout=subprocess.PIPE)
            if self.udp and not iperf2_udp:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                my_pid = process.pid
                console.info('Iperf launched in udp mode on %s with pid %s', str(self.port),str(my_pid))
            else:
                if not iperf2_tcp:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    my_pid = process.pid
                    console.info('Iperf launched in udp mode on %s with pid %s', str(self.port),str(my_pid)) 

        except subprocess.CalledProcessError as e:
            console.error('Command failed with return code %s', str(e))


def iperf2_kill():

    try:
        check = subprocess.check_output(["pidof","iperf"],text=True)
        pids = re.findall(r'\d+', check)
        #print("****************",type(pids))
        #print("pids = ",str(pids))
        for p in pids:
            os.kill(int(p),signal.SIGTERM)
            console.info('iperf2 with pid  %s killed',str(p))
    except Exception as e:
        console.warning('iperf2 process not found %s',str(e))
        return

