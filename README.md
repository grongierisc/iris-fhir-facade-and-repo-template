# iris-fhir-facade-and-repo-template
This repository is a template to build an FHIR facade an/or repository for IRIS for Health

## Build a FHIR Repository

in docker-compose.yml, set the environment variable FHIR_SERVER_ENABLE to "1"

can use also :

- FHIR_SERVER_VERSION : R4 or R5 (default R4)
- FHIR_SERVER_PATH : /fhir (default /fhir)
- FHIR_SERVER_STRATEGY : FHIR.Python.InteractionsStrategy or HS.FHIRServer.Storage.JsonAdvSQL.InteractionsStrategy or HS.FHIRServer.Storage.Json.InteractionsStrategy (default FHIR.Python.InteractionsStrategy)

```
  fhir-server:
    build: 
      context: .
      dockerfile: dockerfile
    environment:
      - FHIR_SERVER_ENABLE=1
      - FHIR_SERVER_VERSION=R4
      - FHIR_SERVER_PATH=/fhir
```
