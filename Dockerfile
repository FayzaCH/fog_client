FROM python:3.10-slim-bookworm
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y libpcap0.8 iperf3 git build-essential

RUN git clone https://git.code.sf.net/p/iperf2/code iperf2-code \
    && cd iperf2-code \
    && git checkout 2-2-1 \
    && ./configure --prefix=/usr/ \
    && make && make install

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/*  \
    && rm -rf /iperf2-code
    
WORKDIR /fog_client
COPY . .
RUN pip install -r requirements.txt
ENV IS_CONTAINER=yes

EXPOSE 5001/tcp 5001/udp
#CMD /bin/iperf -s -D && /bin/iperf -s -u -D
