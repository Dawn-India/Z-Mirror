FROM dawn001/z_mirror:main

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN pip3 install --break-system-packages --ignore-installed --no-cache-dir -r requirements.txt
RUN curl -L https://raw.githubusercontent.com/jsavargas/python-mkvpropedit/master/mkv-tools/mkv-tools.py -o /usr/local/bin/mkv-tools && chmod +x /usr/local/bin/mkv-tools

COPY . .

CMD ["bash", "start.sh"]
