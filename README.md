A Streamlit-based web application that analyzes Power BI (.pbix) files to detect used Measures and Columns from report visuals.

User Uploads .PBIT
        │
        ▼
Save File to Disk
        │
        ▼
Extract ZIP Contents
        │
        ▼
Load DataModelSchema (Model Metadata)
        │
        ├── Extract Tables
        ├── Extract Columns
        ├── Extract Measures
        └── Extract Relationships
        │
        ▼
Load Report Layout (Visual Metadata)
        │
        ├── Scan Sections
        ├── Scan Filters
        ├── Scan Visual Queries
        └── Extract Used Fields
        │
        ▼
Identify Direct Usage
        │
        ▼
Build Dependency Graph (DAX Parsing)
        │
        ├── Goal:
        │       Create a structure that tells:
        │       "Which object depends on which other objects?"
        │
        ├── Collect all DAX expressions
        │
        ├── Clean expressions
        │
        ├── Extract table[column] references
        │
        ├── Extract measure references
        │
        └── Store in dictionary → dependency_graph
        │
        ▼
Recursive Dependency Propagation
        │
        ├── Start from directly used fields
        │
        ├── Look up their dependencies
        │
        ├── Add dependencies to used set
        │
        ├── Repeat until no new items are added
        │
        └── Final set = Full Used Lineage
        │
        ▼
Categorization
        │
        ├── Direct Columns
        ├── Indirect Columns
        ├── Relationship Columns
        ├── Direct Measures
        ├── Indirect Measures
        ├── Unused Columns
        └── Unused Measures
        │
        ▼
Dashboard Display
        │
        ▼
Excel Export

