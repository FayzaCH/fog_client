FROM python:3.10-slim-bookworm
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y libpcap0.8 iperf3 iperf 
WORKDIR /fog_client
COPY . .
RUN pip install -r requirements.txt
ENV IS_CONTAINER yes

EXPOSE 5001/tcp 5001/udp
CMD /bin/iperf -s -D && /bin/iperf -s -u -D
