# E-commerce Data Pipeline

## Overview  
This project implements a batch-processing backend for an e-commerce analytics/ML application. It ingests raw transaction data, processes it, and stores results in a PostgreSQL database, using a **microservices architecture** with Docker for reproducibility. The pipeline includes:  
- **Ingestion Service:** Reads transactions (e.g. from a CSV or API) and forwards them for processing.  
- **Processing Service:** Cleans and aggregates the data, computing features/metrics needed by the ML model.  
- **PostgreSQL Database:** Stores raw and processed data tables.

This design ensures reliability and scalability: each component runs in its own Docker container, so we can scale or restart them independently:contentReference[oaicite:21]{index=21}:contentReference[oaicite:22]{index=22}. Using Docker means the same environment is reproduced on any machine:contentReference[oaicite:23]{index=23}:contentReference[oaicite:24]{index=24}.

## Architecture  
The system uses independent microservices connected via Docker Compose:  
- **Docker Compose** orchestrates containers: one container for the ingestion service, one for processing, and one running PostgreSQL.  
- Data flow: Ingestion service reads the dataset and either pushes data to a queue or directly calls the processing service. The processing service then writes to the Postgres database.  
- Each service is *stateless* beyond its container, allowing multiple instances for load, and ensures *fault isolation* (a failure in one container doesn’t bring down the others):contentReference[oaicite:25]{index=25}.  
- Configuration (e.g. database credentials) is managed via environment variables and Docker volumes for persistence.

## Prerequisites  
- **Docker** and **Docker Compose** installed (Docker Desktop or similar). Docker is required to run and isolate each service:contentReference[oaicite:26]{index=26}:contentReference[oaicite:27]{index=27}.  
- (Optional) **Python** or another runtime if you plan to run services directly, but not necessary if using only containers.  
- **Git** for version control (the repository contains all code, Dockerfiles, and configs).  
- A sufficiently large e-commerce dataset (≥1M rows) placed in the project directory or accessible path.

## How to Run  
1. **Clone the repository:**  
   ```bash
   git clone https://github.com/YourUsername/YourRepoName.git
   cd YourRepoName
