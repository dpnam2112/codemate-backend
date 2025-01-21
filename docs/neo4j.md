# Managing Neo4j Docker Instance and Database

## Environment Setup

Define the following environment variables for reuse:
```bash
export NEO4J_DATA_DIR=~/docker/volumes/codemate-backend/neo4j/data
export NEO4J_PLUGINS_DIR=~/docker/volumes/codemate-backend/neo4j/plugins
export NEO4J_DUMPS_DIR=~/docker/volumes/codemate-backend/neo4j/dumps
```

## How to Run a Docker Instance

Run the following command to start the Neo4j container:
```bash
docker run -d \       
    -p 7474:7474 -p 7687:7687 \
    -v $NEO4J_DATA_DIR:/data \
    -v $NEO4J_PLUGINS_DIR:/plugins \
    --name neo4j \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    neo4j:latest
```

## How to Dump the Database

### Step 1: Stop the Container

Stop the Neo4j container to ensure the database is not active during the dump:
```bash
docker stop neo4j
```

### Step 2: Run the `neo4j-admin` Container

Run a temporary `neo4j-admin` container in interactive mode:
```bash
docker run --network host --name neo4j-admin -it \
-v $NEO4J_DUMPS_DIR:/var/lib/neo4j/dumps \
-v $NEO4J_DATA_DIR:/var/lib/neo4j/data \
-v $NEO4J_PLUGINS_DIR:/var/lib/neo4j/plugins \
neo4j/neo4j-admin /bin/bash
```

### Step 3: Dump the Database

Within the `neo4j-admin` container, dump the database:
```bash
neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/dumps
```

## How to Load the Database

### Step 1: Ensure the Dump File Exists

Ensure the dump file (e.g., `neo4j.dump`) is located in the `$NEO4J_DUMPS_DIR` directory. If necessary, create the directory and copy the dump file:
```bash
mkdir -p $NEO4J_DUMPS_DIR
cp dumps/neo4j.dump $NEO4J_DUMPS_DIR
```

### Step 2: Run the `neo4j-admin` Container

Follow the same process as in the **Dump the Database** section to create and run the `neo4j-admin` container.

### Step 3: Load the Database

Within the `neo4j-admin` container, load the database:
```bash
neo4j-admin database load --from-path=/var/lib/neo4j/dumps/ --overwrite-destination=true neo4j
```

## Synchronize with Postgres

- Run the following SQL statements:
```sql
INSERT INTO users (id, name, email, avatar_url, created_at, role, updated_at) VALUES
('317066c9-7c31-4b0a-90a1-04c5ca6e9c33', 'John Doe', 'johndoe@example.com', 'https://example.com/avatar/johndoe.png', NOW(), 'professor', NOW()),
('c9413c07-5e88-4f04-a3f5-21890b8ef053', 'Harry Potter', 'harrypotter@example.com', 'https://example.com/avatar/johndoe.png', NOW(), 'student', NOW());

INSERT INTO courses (id, name, professor_id, learning_outcomes, start_date, end_date, status, image_url, created_at, updated_at) VALUES 
('78bccebd-3eb1-4068-a786-0058323f0076', 'Introduction to Python', (SELECT id FROM users WHERE email = 'johndoe@example.com'), ARRAY['Understand basic Python syntax', 'Write simple Python scripts', 'Understand loops and conditionals'], NULL, NULL, 'new', NULL, NOW(), NOW());

INSERT INTO lessons (id, course_id, title, description, "order", learning_outcomes) VALUES
('d65af666-2742-4ca1-9c51-2d57aa483c37', '78bccebd-3eb1-4068-a786-0058323f0076', 'Python Basics', 'Learn the foundational syntax and structure of Python programming.', 1, ARRAY['Learn to declare and use variables', 'Understand Python''s basic syntax and structure', 'Identify and use different data types']),
('053d7d8f-b30a-4295-bd29-9370a805ccdf', '78bccebd-3eb1-4068-a786-0058323f0076', 'Control Flow', 'Understand decision-making in Python with conditional statements and loops.', 2, ARRAY['Learn the importance of proper indentation', 'Understand and implement loops', 'Write programs using conditional statements']),
('7bbc3089-d1fa-4a0e-964b-653ece200a5f', '78bccebd-3eb1-4068-a786-0058323f0076', 'Functions', 'Learn how to write reusable blocks of code with Python functions.', 3, ARRAY['Write reusable and modular code', 'Understand the purpose and structure of functions', 'Learn to use parameters and return values']),
('03099933-88d9-40f0-bcc7-516d4d88d3c4', '78bccebd-3eb1-4068-a786-0058323f0076', 'Data Structures', 'Explore Python''s built-in data structures for efficient data manipulation.', 4, ARRAY['Differentiate between mutable and immutable structures', 'Understand and use Python''s built-in data structures', 'Learn how to manipulate data with lists and dictionaries']),
('9adec80f-d867-47de-a889-a7b788ea9c13', '78bccebd-3eb1-4068-a786-0058323f0076', 'File Handling', 'Learn to read and write files using Python.', 5, ARRAY['Understand file modes and their purposes', 'Handle file-related errors', 'Open, read, and write files in Python']),
('486fc529-5bae-4fd9-9e90-af5d3f740061', '78bccebd-3eb1-4068-a786-0058323f0076', 'Error Handling', 'Handle errors gracefully in your Python programs.', 6, ARRAY['Learn to identify and handle exceptions', 'Write robust programs that handle edge cases', 'Use try-except blocks to manage errors']);
```
