## How to run docker instance

- Create directory at the project's root:
```bash
(edumind-api-py3.12) ➜  backend git:(backend-workflow-full) ✗ mkdir neo4j-data/data/ neo4j-data/plugins/
```

- Run the following command:
```bash
docker run -d \
    -p 7474:7474 -p 7687:7687 \
    -v $PWD/neo4j-data/data:/data \
    -v $PWD/neo4j-data/plugins:/plugins \
    --name neo4j \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    neo4j:latest
```

k

## How to dump the database

- Stop the container (since Neo4j requires the database to be shut down before dumping):
```bash
(edumind-api-py3.12) ➜  backend git:(backend-workflow-full) ✗ docker stop neo4j         
neo4j
```

- Create a folder for storing backup files
```bash
(edumind-api-py3.12) ➜  backend git:(backend-workflow-full) ✗ mkdir neo4j-data/backups
```

- Run the `neo4j-admin` container in interactive mode:
```bash
(edumind-api-py3.12) ➜  backend git:(backend-workflow-full) ✗ docker run --network host --name neo4j-admin -it \
-v /$PWD/neo4j-data/backups/:/var/lib/neo4j/backups \
-v /$PWD/neo4j-data/data/:/var/lib/neo4j/data \
-v /$PWD/neo4j-data/plugins/:/var/lib/neo4j/plugins \
neo4j/neo4j-admin /bin/bash;
bash: /root/.bashrc: Permission denied
neo4j@nam-laptop:/var/lib/neo4j$
```

- Create a folder inside the container for storing backup files:
```bash
neo4j@nam-laptop:/var/lib/neo4j$ mkdir backups
```

- Dump the database
```bash
neo4j@nam-laptop:/var/lib/neo4j$ neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/backups;
2025-01-20 18:01:50.752+0000 INFO  [o.n.c.d.DumpCommand] Starting dump of database 'neo4j'
Done: 44 files, 261.0MiB processed in 0.732 seconds.
2025-01-20 18:01:52.009+0000 INFO  [o.n.c.d.DumpCommand] Dump completed successfully
neo4j@nam-laptop:/var/lib/neo4j$ 
```

- Quit the container and verify the operation:
```bash
neo4j@nam-laptop:/var/lib/neo4j$ exit
exit
(edumind-api-py3.12) ➜  backend git:(backend-workflow-full) ✗ ls neo4j-data/backups 
neo4j.dump
(edumind-api-py3.12) ➜  backend git:(backend-workflow-full) ✗ 
```

## How to load the database

- Assume that the dump file exists.

- Follow the guide in the above section to create the container `neo4j-admin`.

- Load the database:
```bash
root@nam-laptop:/var/lib/neo4j# neo4j-admin database load --from-path=/var/lib/neo4j/backups/ --overwrite-destination=true neo4j
Done: 44 files, 261.0MiB processed in 0.534 seconds.
```

## Synchronize with Postgres

- Run the following SQL statements:
```sql
INSERT INTO users (
    id, 
    name, 
    email, 
    avatar_url, 
    created_at, 
    role, 
    updated_at
) VALUES (
    gen_random_uuid(), -- Generates a unique UUID for the user
    'John Doe', 
    'johndoe@example.com', 
    'https://example.com/avatar/johndoe.png', -- Example avatar URL
    NOW(), 
    'professor', 
    NOW()
);


INSERT INTO courses (
    id, 
    name, 
    professor_id, 
    learning_outcomes, 
    start_date, 
    end_date, 
    status, 
    image_url, 
    created_at, 
    updated_at
) VALUES (
    '78bccebd-3eb1-4068-a786-0058323f0076', 
    'Introduction to Python', 
    (SELECT id FROM users WHERE email = 'johndoe@example.com'), -- Reference the professor's ID
    ARRAY['Understand basic Python syntax', 'Write simple Python scripts', 'Understand loops and conditionals'], 
    NULL, 
    NULL, 
    'new', 
    NULL, 
    NOW(), 
    NOW()
);

INSERT INTO lessons (
    id, 
    course_id, 
    title, 
    description, 
    "order", 
    learning_outcomes
) VALUES
    ('d65af666-2742-4ca1-9c51-2d57aa483c37', '78bccebd-3eb1-4068-a786-0058323f0076', 
     'Python Basics', 'Learn the foundational syntax and structure of Python programming.', 
     1, ARRAY['Learn to declare and use variables', 'Understand Python''s basic syntax and structure', 'Identify and use different data types']),
    ('053d7d8f-b30a-4295-bd29-9370a805ccdf', '78bccebd-3eb1-4068-a786-0058323f0076', 
     'Control Flow', 'Understand decision-making in Python with conditional statements and loops.', 
     2, ARRAY['Learn the importance of proper indentation', 'Understand and implement loops', 'Write programs using conditional statements']),
    ('7bbc3089-d1fa-4a0e-964b-653ece200a5f', '78bccebd-3eb1-4068-a786-0058323f0076', 
     'Functions', 'Learn how to write reusable blocks of code with Python functions.', 
     3, ARRAY['Write reusable and modular code', 'Understand the purpose and structure of functions', 'Learn to use parameters and return values']),
    ('03099933-88d9-40f0-bcc7-516d4d88d3c4', '78bccebd-3eb1-4068-a786-0058323f0076', 
     'Data Structures', 'Explore Python''s built-in data structures for efficient data manipulation.', 
     4, ARRAY['Differentiate between mutable and immutable structures', 'Understand and use Python''s built-in data structures', 'Learn how to manipulate data with lists and dictionaries']),
    ('9adec80f-d867-47de-a889-a7b788ea9c13', '78bccebd-3eb1-4068-a786-0058323f0076', 
     'File Handling', 'Learn to read and write files using Python.', 
     5, ARRAY['Understand file modes and their purposes', 'Handle file-related errors', 'Open, read, and write files in Python']),
    ('486fc529-5bae-4fd9-9e90-af5d3f740061', '78bccebd-3eb1-4068-a786-0058323f0076', 
     'Error Handling', 'Handle errors gracefully in your Python programs.', 
     6, ARRAY['Learn to identify and handle exceptions', 'Write robust programs that handle edge cases', 'Use try-except blocks to manage errors']);
```
