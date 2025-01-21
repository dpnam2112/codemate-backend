### Usage Instructions:

1. **Build the Docker Image**:
   Save the `Dockerfile` to a directory and run:
   ```bash
   docker build -t postgres-pgvector -f docker/postgres.Dockerfile .
   ```

2. **Run the Container**:
   You can configure the username, password, and database by passing environment variables:
   ```bash
   docker run -d \
       --name my-postgres-pgvector \
       -e POSTGRES_USER=nam \
       -e POSTGRES_PASSWORD=thangcho \
       -e POSTGRES_DB=codemate \
       -p 5432:5432 \
       postgres-pgvector
   ```

3. **Access the Database**:
   You can connect to the database using `psql` or any PostgreSQL client:
   ```bash
   psql -h localhost -U nam -d codemate
   ```

4. **Verify `pgvector` Extension**:
   Inside the database, enable and verify `pgvector`:
   ```sql
   CREATE EXTENSION vector;
   SELECT * FROM pg_available_extensions WHERE name = 'vector';
   ```
