-- Создание пользователя и базы данных для Docker
CREATE DATABASE english_bot;
CREATE USER english_user WITH PASSWORD 'password123';
GRANT ALL PRIVILEGES ON DATABASE english_bot TO english_user;

-- Расширения для PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";