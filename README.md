# IU Data Engineering Portfolio – Task 1 (Batch)
E-commerce Analytics + Feature Warehouse (Docker + Microservices)

## Overview
This project implements a reproducible batch data pipeline for e-commerce transaction data.
It loads raw CSV files into PostgreSQL and generates curated analytics + ML-ready features.

## Architecture
- **postgres**: PostgreSQL warehouse (tables: retail_raw, daily_metrics, top_products_daily, customer_features_quarterly)
- **ingestion**: Python service that reads CSVs in chunks and loads into `retail_raw`
- **processing**: Python service that runs batch SQL transforms and populates analytics tables

Data flow:
CSV files → ingestion → `retail_raw` → processing → curated tables

## Prerequisites
- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Kaggle dataset extracted into `dataset/raw/`

## Project Structure
