# codex

## Crawler

Downloading data:

```sh
cd crawler/data/raw

wget https://zenodo.org/records/7752615/files/unarXive_230324_open_subset.tar.xz?download=1
mkdir ./unarXive_230324_open_subset

tar -xf unarXive_230324_open_subset.tar.xz?download=1 -C ./unarXive_230324_open_subset
```

### Clean research papers

- [ ] Whatever is necessary
  - [ ] Labeled sections
  - [ ] Figures and tables are interpretable/ignorable

### Fact extraction prompt

- [ ] **Paper -> entities**
- [ ] **Essential entities**
  - [ ] Paper
  - [ ] Task
  - [ ] Method
  - [ ] Results
  - [ ] Dataset
  - [ ] Models
  - [ ] Libraries
- [ ] Non-essential entities
  - [ ] Languages (natural)
  - [ ] License
  - [ ] Authors
  - [ ] Affiliations
- [ ] **Other information to collect**
  - [ ] Date

### Entity resolution prompt

- [ ] **Group/Merge entities**

### Graph building

- [ ] **Defining relationships between entities.**

### Article construction prompt

- [ ] **Collection of facts about a given entity (of a specific type) -> Article**

### Endpoints for client

- [ ] **Search**

## Client

### Search / Graph View

- [ ] **Search bar**
- [ ] Graph view
  - [ ] Nodes
    - [ ] Entity
    - [ ] Type
  - [ ] Edges
    - [ ] Relationship
    - [ ] Type

### Article view

- [ ] Page preceding article generation
  - [ ] See how many facts you have about a topic
  - [ ] See relationships between entities
- [x] **Client side article generation with API Key**
- [ ] **Essential Article types**
  - [ ] Task
    - [ ] Name
    - [ ] Description
    - [ ] Methods & Associated Results
  - [ ] Method
- [ ] Non-essential Article types
  - [ ] Paper
  - [ ] Dataset
  - [ ] Models
  - [ ] Libraries
  - [ ] Authors
  - [ ] Affiliations
  - [ ] Languages
  - [ ] License

### Extras

- [ ] Subscribe
