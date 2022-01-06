FROM mariadb:latest

ENV MYSQL_ROOT_PASSWORD=test

# Prevent packages from prompting interactive input
ENV DEBIAN_FRONTEND=noninteractive

# Install apt packages
RUN apt update && apt install -y nano wget unzip git python3 python3-pip python2 libmariadb3 libmariadb-dev && rm -rf /var/lib/apt/lists/*

# Install pip2
RUN wget https://bootstrap.pypa.io/pip/2.7/get-pip.py && python2 get-pip.py && rm get-pip.py

# Install Go (apt only installs up to Go 1.13)
RUN wget https://dl.google.com/go/go1.16.4.linux-amd64.tar.gz && tar -xvf go1.16.4.linux-amd64.tar.gz && mv go /usr/local && rm go1.16.4.linux-amd64.tar.gz
ENV GOROOT=/usr/local/go
ENV GOPATH=$HOME/go
ENV PATH=$GOPATH/bin:$GOROOT/bin:$PATH

# Install ndodeJS
RUN wget https://deb.nodesource.com/setup_lts.x -O install_node.sh && bash install_node.sh && apt install nodejs && rm install_node.sh

# Install yarn
RUN npm install -g yarn

# Install Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && dpkg -f google-chrome-stable_current_amd64.deb && rm google-chrome-stable_current_amd64.deb

# Install Chrome Driver
RUN wget https://chromedriver.storage.googleapis.com/97.0.4692.71/chromedriver_linux64.zip && unzip chromedriver_linux64.zip && mv chromedriver /usr/local/sbin && rm chromedriver_linux64.zip

# Install gobuster
RUN go install github.com/OJ/gobuster/v3@latest

# Install subfinder
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Install subjack
RUN go get github.com/haccer/subjack

# Install sqlmap
RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /usr/lib/sqlmap && sed -i "s/#!\/usr\/bin\/env python/#!\/usr\/bin\/env python3/" /usr/lib/sqlmap/sqlmap.py && ln -s /usr/lib/sqlmap/sqlmap.py /usr/local/sbin/sqlmap

# Install dalfox
RUN go install github.com/hahwul/dalfox/v2@latest

# Install crlfuzz
RUN GO111MODULE=on go install github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest

# Install tplmap
RUN git clone https://github.com/epinna/tplmap /usr/lib/tplmap && sed -i "s/#!\/usr\/bin\/env python/#!\/usr\/bin\/env python2/" /usr/lib/tplmap/tplmap.py && ln -s /usr/lib/tplmap/tplmap.py /usr/local/sbin/tplmap && pip2 install -r /usr/lib/tplmap/requirements.txt

# Install wappalyzer
RUN git clone https://github.com/AliasIO/wappalyzer.git /usr/lib/wappalyzer && cd /usr/lib/wappalyzer && yarn install && yarn run link && ln -s /usr/lib/wappalyzer/src/drivers/npm/cli.js /usr/local/sbin/wappalyzer

# Download SecLists used
RUN mkdir /usr/lib/SecLists && mkdir /usr/lib/SecLists/Discovery && mkdir /usr/lib/SecLists/Discovery/DNS/ && mkdir /usr/lib/SecLists/Discovery/Web-Content
RUN wget -c https://github.com/danielmiessler/SecLists/blob/master/Discovery/DNS/subdomains-top1million-110000.txt -O /usr/lib/SecLists/Discovery/DNS/subdomains-top1million-110000.txt
RUN wget -c https://github.com/danielmiessler/SecLists/blob/master/Discovery/Web-Content/directory-list-2.3-big.txt -O /usr/lib/SecLists/Discovery/Web-Content/directory-list-2.3-big.txt

# Copy init script in docker-entrypoint-initdb.d so it gets executed on startup (https://hub.docker.com/_/mariadb/)
COPY sql/ /docker-entrypoint-initdb.d

# Copy src files
COPY src/ /root/bagley
WORKDIR /root/bagley

# Install requirements
RUN pip3 install -r  requirements.txt

# Run bagley when running docker
ENTRYPOINT [ "bagley.py" ]