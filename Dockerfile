FROM python:3.12

RUN useradd -u 1000 -s /bin/bash -d /app -M app

RUN mkdir /app && chown -R 1000:1000 /app && chmod -R 755 /app

ADD https://astral.sh/uv/install.sh /tmp/uv.sh

RUN chown app /tmp/uv.sh

USER app

WORKDIR /app

RUN sh /tmp/uv.sh && rm /tmp/uv.sh

COPY --chown=app:app pyproject.toml requirements.txt README.md run.sh ./

RUN mkdir -p src/librechat_stats && \
    touch src/librechat_stats/__init__.py && \
    chmod +x run.sh

RUN /app/.cargo/bin/uv venv && \
    /app/.cargo/bin/uv pip sync --no-cache requirements.txt

COPY --chown=app:app src ./

CMD ["/app/run.sh"]
