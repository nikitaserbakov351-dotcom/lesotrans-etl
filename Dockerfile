FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python -m unittest discover -s tests -p "test_*.py"
ENTRYPOINT ["python", "-m", "lesotrans_etl.cli"]
