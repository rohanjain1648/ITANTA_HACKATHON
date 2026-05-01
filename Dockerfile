# ForgeAI — Hugging Face Spaces Dockerfile
# Uses the Docker SDK space type for full Python environment control.

FROM python:3.11-slim

# HF Spaces runs as a non-root user; set up a writable home
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR $HOME/app

# Install dependencies
COPY --chown=user forgeai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gradio>=4.0.0

# Copy application source
COPY --chown=user . .

# Ensure the generated project output dir exists and is writable
RUN mkdir -p $HOME/app/generated_project

# HF Spaces expects the app to listen on port 7860
EXPOSE 7860

CMD ["python", "app.py"]
