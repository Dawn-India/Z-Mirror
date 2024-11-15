FROM dawn001/z_mirror:main

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN curl -o mkvtoolnix_88.0.orig.tar.xz https://mkvtoolnix.download/sources/mkvtoolnix-88.0.tar.xz
RUN tar xJf mkvtoolnix_88.0.orig.tar.xz
RUN cd mkvtoolnix-88.0
RUN cp -R packaging/debian debian
RUN dpkg-buildpackage -b --no-sign

COPY requirements.txt .
RUN pip3 install --break-system-packages --ignore-installed --no-cache-dir -r requirements.txt
RUN curl -L https://raw.githubusercontent.com/jsavargas/python-mkvpropedit/master/mkv-tools/mkv-tools.py -o /usr/local/bin/mkv-tools && chmod +x /usr/local/bin/mkv-tools

COPY . .

CMD ["bash", "start.sh"]
