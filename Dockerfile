FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git libssl-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Build/load the matching liboqs shared library during image creation.
RUN python -c "import oqs; print('liboqs version:', oqs.oqs_version()); print('liboqs-python version:', oqs.oqs_python_version())"

COPY benchmark.py plot_results.py README.md ./
RUN mkdir -p /app/results

CMD ["python", "benchmark.py"]
