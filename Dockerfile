FROM dawn001/z_mirror:main

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN python3 -m venv zee_env

COPY requirements.txt .
RUN zee_env/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
