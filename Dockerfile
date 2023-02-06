FROM dawn001/z_mirror:latest
# FROM dawn001/z_mirror:arm64
# FROM dawn001/z_mirror:armv7
# FROM dawn001/z_mirror:s390x
# Select based on your device's arch. Default is amd64(latest)

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]