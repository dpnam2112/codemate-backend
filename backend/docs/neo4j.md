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
