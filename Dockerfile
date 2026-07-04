# We COPY requirements.txt and pip install before copying the rest of the code. Why? Docker caches each step. Your dependencies change rarely but your code changes constantly — doing deps first means rebuilds after a code edit skip re-installing everything. That's the single most important Docker efficiency habit

# 1. Base image: Python 3.14 on slim Debian - matches local Python
FROM python:3.14-slim
# FROM python:3.14-slim — every Dockerfile starts FROM something. This pulls a ready-made image that already has Python 3.14 installed on a minimal Linux.

# 2. Python behaviour tweaks for containers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# PYTHONDONTWRITEBYTECODE=1 → don't litter .pyc files (useless in a throwaway container).
# PYTHONUNBUFFERED=1 → important — makes Python print logs immediately instead of buffering them. Without it, docker logs can look empty/frozen and you'll think the app hung when it's actually just holding output. This will save you debugging pain in step 2.

# 3. The working directory inside the container
WORKDIR /app
# WORKDIR /app — creates /app inside the container and cds into it. Every following command runs from there

# 4. Copy ONLY requirements first - the chache trick mentioned at the top
COPY requirements.txt .
# COPY requirements.txt . then RUN pip install then COPY . . — this is the cache ordering you just flagged. Deps first (rarely change → stays cached), code last (changes constantly)

# 5. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir tells pip not to keep its download cache → smaller image

# 6. Now copy the rest of your source code
COPY . .

# 7. Collect all static files into STATIC_ROOT, compressed + hashed by WhiteNoise
RUN python manage.py collectstatic --noinput
# Why here: It must come after COPY . . because it needs your actual code and static/ files present in the image. It comes before CMD because we want the static files baked into the image at build time, so the running container already has them ready to serve (no work at startup).
# collectstatic — walks every app's static/ folder + your STATICFILES_DIRS, and copies everything into STATIC_ROOT (staticfiles/). Because of the WhiteNoise storage backend you just configured, it also compresses and hashes each file during this step.
# --noinput — collectstatic normally asks "You have requested to collect static files... proceed? [y/N]". There's no human in a build, so --noinput auto-confirms. (Same reason we'll use --noinput on migrations later.)

# 7. Tell docker the app listens on port 8000
EXPOSE 8000
# EXPOSE 8000 — mostly documentation; it signals "this app talks on 8000."

# 8. What runs when the container starts
CMD python manage.py migrate --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
# CMD [...] — the start command. Two things to notice:
# config.wsgi:application — that's your WSGI entrypoint (config/wsgi.py, the application object). This is why I checked your structure.
# --bind 0.0.0.0:8000 — critical. Inside a container, 127.0.0.1 would mean "only reachable from inside the container itself" — you'd never be able to open it in your browser. 0.0.0.0 means "listen on all interfaces," which is what makes the port reachable from outside
