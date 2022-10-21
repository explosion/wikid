<!-- SPACY PROJECT: AUTO-GENERATED DOCS START (do not remove) -->

# 🪐 spaCy Project: wikid

[![Azure Pipelines](https://img.shields.io/azure-devops/build/explosion-ai/public/32/main.svg?logo=azure-pipelines&style=flat-square&label=build)](https://dev.azure.com/explosion-ai/public/_build?definitionId=32)
[![spaCy](https://img.shields.io/static/v1?label=made%20with%20%E2%9D%A4%20and&message=spaCy&color=09a3d5&style=flat-square)](https://spacy.io)
<br/>
_No REST for the `wikid`_ :jack_o_lantern: - generate a SQLite database from Wikipedia & Wikidata dumps.


## 📋 project.yml

The [`project.yml`](project.yml) defines the data assets required by the
project, as well as the available commands and workflows. For details, see the
[spaCy projects documentation](https://spacy.io/usage/projects).

### ⏯ Commands

The following commands are defined by the project. They
can be executed using [`spacy project run [name]`](https://spacy.io/api/cli#project-run).
Commands are only re-run if their inputs have changed.

| Command | Description |
| --- | --- |
| `parse` | Parse Wiki dumps. This can take a long time if you're not using the filtered dumps! |
| `clean` | Deletes SQLite database generated in step parse_wiki_dumps with data parsed from Wikidata and Wikipedia dump. |

### ⏭ Workflows

The following workflows are defined by the project. They
can be executed using [`spacy project run [name]`](https://spacy.io/api/cli#project-run)
and will run the specified commands in order. Commands are only re-run if their
inputs have changed.

| Workflow | Steps |
| --- | --- |
| `all` | `parse` |

### 🗂 Assets

The following assets are defined by the project. They can
be fetched by running [`spacy project assets`](https://spacy.io/api/cli#project-assets)
in the project directory.

| File | Source | Description |
| --- | --- | --- |
| `assets/wikidata_entity_dump.json.bz2` | URL | Wikidata entity dump. Download can take a long time! |
| `assets/wikipedia_dump.xml.bz2` | URL | Wikipedia dump. Download can take a long time! |
| `assets/wikidata_entity_dump_filtered.json.bz2` | URL | Filtered Wikidata entity dump for demo purposes (English only). |
| `assets/wikipedia_dump_filtered.xml.bz2` | URL | Filtered Wikipedia dump for demo purposes (English only). |

<!-- SPACY PROJECT: AUTO-GENERATED DOCS END (do not remove) -->
