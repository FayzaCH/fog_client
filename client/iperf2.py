import subprocess
import os
import signal
import re

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
                #print("Processus iperf trouvés :")
                for line in lines_iperf:
                    print(line)
                    if "-u" in line:
                        #print("    L'option -u est utilisée (mode UDP).")
                        iperf2_udp= True
                    else:
                        #print("    L'option -u n'est pas utilisée (mode TCP ou autre).")
                        iperf2_tcp= True
            else:
                print("Aucun processus iperf trouvé.")
            return iperf2_tcp,iperf2_udp

        except subprocess.CalledProcessError as e:
            print(f"Error when  running ps: {e}")
        except FileNotFoundError:
            print("ps command not found.")


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
                my_pid, err = process.communicate()
                print("erreur :",str(err))
                print("server iperf2 udp  launched on", str(self.port),"with pid", str(my_pid))
            else:
                if not iperf2_tcp:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    my_pid, err = process.communicate()
                    print("erreur :",str(err))
                    print("server iperf2 tcp launched on", str(self.port),"with pid", str(my_pid))  

        except subprocess.CalledProcessError as e:
            print(f"Command failed with return code {e.returncode}")


def iperf2_kill():

    try:
        check = subprocess.check_output(["pidof","iperf"],text=True)
        pids = re.findall(r'\d+', check)
        #print("****************",type(pids))
        #print("pids = ",str(pids))
        for p in pids:
            os.kill(int(p),signal.SIGTERM)
            print("iperf2 with pid =",str(p),"killed")
    except Exception as e:
        print("iperf2 process not found", str(e))
        return

