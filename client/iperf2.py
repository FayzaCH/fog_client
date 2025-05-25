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
        self.iperf_process = None
        self.iperf_pid = None

    def _is_iperf_running(self):
        """Search if iperf2 process is already running, then check if it runs in udp or tcp mode."""
        try:
            # list all runinng processes
            output = subprocess.check_output(f"netstat -tulnp | grep :{self.port} | grep iperf", shell=True, text=True)
            if "iperf" in output:
                return True, True
            return False, False
        except subprocess.CalledProcessError:
            return False, False
 
    def launch(self):
        iperf2_tcp, iperf2_udp = self._is_iperf_running()
        if self.udp and iperf2_udp:
            console.info('Iperf UDP is already running on port %s.', self.port)
            return
        elif not self.udp and iperf2_tcp:
            console.info('Iperf TCP is already runnin on port %s', self.port)
            return

        cmd=["iperf","-s","-p",str(self.port),"-i","1"]
        if self.daemon:
            cmd.append("-D")
        if self.udp:
            cmd.append("-u")
            
        try:
            if self.daemon:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = process.communicate()
                self.iperf_pid = process.pid
                if out:
                    console.info(f"Iperf daemon output: {out.strip()}")
                if err:
                    console.warning(f"Iper daemon stderr: {err.strip()}")             
            else:
                process = subprocess.Popen(cmd)
                self.iperf_process = process
                self.iperf_pid = process.pid
            mode = "UDP" if self.udp else "TCP"
            console.info('Iperf %s server launched on port %s with pid %s', mode, self.port, self.iperf_pid) 

        except FileNotFoundError:
            console.error(f"Error Iperf command not found")
            self.iperf_process = None
            self.iperf_pid = None
        except Exception as e:
            console.error(f"Error when launching iperf on port {self.port} : {e}")
            self.iperf_process = None
            self.iperf_pid = None    
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

