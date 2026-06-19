FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x start.sh

EXPOSE 7860

CMD ["bash", "start.sh"]