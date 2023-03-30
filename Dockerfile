FROM ubuntu:latest

# Prevent packages from prompting interactive input
ENV DEBIAN_FRONTEND=noninteractive

# Install apt packages
RUN apt update && apt install -y nano iptables wget unzip git python3 python3-pip python2 libmariadb3 libmariadb-dev iputils-ping iproute2 nmap openssl && rm -rf /var/lib/apt/lists/*

# Install pip2
RUN wget https://bootstrap.pypa.io/pip/2.7/get-pip.py && python2 get-pip.py && rm get-pip.py

# Install Go (apt only installs up to Go 1.13)
RUN wget https://go.dev/dl/go1.19.4.linux-amd64.tar.gz && tar -xvf go1.19.4.linux-amd64.tar.gz && mv go /usr/local && rm go1.19.4.linux-amd64.tar.gz
ENV GOROOT=/usr/local/go
ENV GOPATH=$HOME/go
ENV PATH=$GOPATH/bin:$GOROOT/bin:$PATH

# Install ndodeJS
RUN wget https://deb.nodesource.com/setup_lts.x -O install_node.sh && bash install_node.sh && apt install nodejs && rm install_node.sh

# Install yarn
RUN npm install -g yarn

# Install Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt install -y ./google-chrome-stable_current_amd64.deb libxss1 && rm google-chrome-stable_current_amd64.deb

# Install Chrome Driver
RUN wget https://chromedriver.storage.googleapis.com/110.0.5481.77/chromedriver_linux64.zip && unzip chromedriver_linux64.zip && mv chromedriver /usr/local/sbin && rm chromedriver_linux64.zip

# Install gobuster
RUN go install github.com/OJ/gobuster/v3@latest

# Install subfinder (must be executed once so that it configures itself)
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN subfinder || :

# Install subjack
RUN go install github.com/haccer/subjack@latest

# Install gau
RUN go install github.com/lc/gau/v2/cmd/gau@latest

# Install sqlmap
RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /usr/lib/sqlmap && sed -i "s/#!\/usr\/bin\/env python/#!\/usr\/bin\/env python3/" /usr/lib/sqlmap/sqlmap.py && ln -s /usr/lib/sqlmap/sqlmap.py /usr/local/sbin/sqlmap

# Install dalfox
RUN go install github.com/hahwul/dalfox/v2@latest

# Install crlfuzz
RUN GO111MODULE=on go install github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest

# Install wappalyzer
RUN git clone https://github.com/AliasIO/wappalyzer.git /usr/lib/wappalyzer && cd /usr/lib/wappalyzer && yarn install && yarn run link && ln -s /usr/lib/wappalyzer/src/drivers/npm/cli.js /usr/local/sbin/wappalyzer

# Install linkfinder
RUN git clone https://github.com/GerbenJavado/LinkFinder.git /usr/lib/linkfinder && cd /usr/lib/linkfinder && python3 setup.py install && sed -i "s/#!\/usr\/bin\/env python/#!\/usr\/bin\/env python3/" /usr/lib/linkfinder/linkfinder.py && ln -s /usr/lib/linkfinder/linkfinder.py /usr/local/sbin/linkfinder

# Download SecLists used
RUN mkdir /usr/lib/SecLists && mkdir /usr/lib/SecLists/Discovery && mkdir /usr/lib/SecLists/Discovery/DNS/ && mkdir /usr/lib/SecLists/Discovery/Web-Content
RUN wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt -O /usr/lib/SecLists/Discovery/DNS/subdomains-top1million-5000.txt
RUN wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -O /usr/lib/SecLists/Discovery/Web-Content/common.txt

# Install codeql
RUN wget https://github.com/github/codeql-action/releases/latest/download/codeql-bundle-linux64.tar.gz && tar -xvzf codeql-bundle-linux64.tar.gz -C /usr/lib/ && rm codeql-bundle-linux64.tar.gz && ln -s /usr/lib/codeql/codeql /usr/local/sbin/codeql

# Install unwebpack_sourcemap
RUN git clone https://github.com/rarecoil/unwebpack-sourcemap /tmp/unwebpack-sourcemap && pip3 install -r /tmp/unwebpack-sourcemap/requirements.txt && cp /tmp/unwebpack-sourcemap/unwebpack_sourcemap.py /usr/local/sbin/unwebpack_sourcemap && rm -rf /tmp/unwebpack-sourcemap

# Create temporal directories
RUN mkdir /tmp/screenshots /tmp/scripts /tmp/files/

# Copy src files and set workdir
COPY src/ /root/bagley
WORKDIR /root/bagley

# Install requirements
RUN pip3 install -r  requirements.txt

# Run supervisord
ENTRYPOINT ["python3", "bagley.py"]
