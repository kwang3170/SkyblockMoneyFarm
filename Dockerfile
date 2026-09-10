FROM python:3.12-slim
WORKDIR /app
COPY backend /app/backend
COPY deploy /app/deploy
RUN pip install --no-cache-dir -c backend/requirements.lock ./backend
ENV PYTHONUNBUFFERED=1 DATABASE_URL=sqlite:////data/bazaar.db
EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && exec bazaar serve"]
