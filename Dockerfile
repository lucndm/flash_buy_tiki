FROM python:3
WORKDIR /app/
COPY . /app/
ADD https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2 /tmp/
RUN tar jxf /tmp/phantomjs-2.1.1-linux-x86_64.tar.bz2 -C /tmp/
RUN cp /tmp/phantomjs-2.1.1-linux-x86_64/bin/phantomjs /app/drivers/ \
    && pip install -r ./requirements.txt
RUN python main.py
#CMD ['python', 'main.py']