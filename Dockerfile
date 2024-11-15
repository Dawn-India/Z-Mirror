FROM dawn001/z_mirror:main

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

#RUN apt-get update && apt-get upgrade -y

COPY requirements.txt .
RUN chmod 777 pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
