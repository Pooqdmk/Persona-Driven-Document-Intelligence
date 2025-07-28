# Persona-Driven-Document-Intelligence

## Introduction

This project delivers an intelligent system designed to transform static PDF documents into dynamic, interactive experiences. It provides a comprehensive solution for understanding document structure, extracting key insights, and acting as a powerful research and analysis tool.

## Methodology

Our methodology for achieving persona-driven document intelligence proceeds through a series of integrated stages:

### Stage 1: Structured Document Outline Extraction

This initial stage focuses on accurately extracting the hierarchical structure of a PDF document.
* **Goal:** To automatically generate a structured outline (Title, Headings H1, H2, H3 with their respective levels and page numbers).
* **Approach:** The system utilizes robust PDF parsing techniques to analyze font sizes, styles (e.g., bold, black, demi), and spatial properties (e.g., vertical spacing, indentation). A heuristic scoring mechanism evaluates these visual and textual cues, alongside content patterns (e.g., all-caps, title case, numbered lists), to precisely identify and classify headings and the document's main title. The output is a JSON representation of this structural outline.

### Stage 2: Contextual Document Analysis and Intelligence

Building upon the structural understanding from Stage 1, this stage deepens the analysis by incorporating contextual relevance.
* **Goal:** To analyze a collection of documents, identify the most relevant sections, and refine information based on a specific user persona and their "job-to-be-done."
* **Approach:**
    * **Section Content Extraction:** For each identified heading in the document outline, the system extracts the full textual content corresponding to that section, spanning until the subsequent heading or the end of the document.
    * **Persona and Task Understanding:** The system processes external inputs defining the user's "persona" (role, expertise) and "job-to-be-done" (specific task). Key terms and concepts are extracted from these definitions to establish the analytical context.
    * **Relevance Scoring and Ranking:** Each extracted document section is assigned a relevance score based on its alignment with the established persona and job-to-be-done. This involves evaluating keyword overlap and applying heuristics related to text properties and content length. Sections are then ranked by their importance.
    * **Sub-section Refinement:** For the top-ranked sections, the system generates concise, "refined text" summaries. The current basic implementation extracts key content from the section; future iterations aim to incorporate more advanced extractive summarization techniques for deeper granular insights.
* **Output:** The final output is a comprehensive JSON report, including metadata (e.g., input documents, persona, task, processing timestamp), a list of ranked `extracted_sections`, and detailed `sub_section_analysis` with refined text.

## Technologies and Libraries

* **Core Language:** Python
* **PDF Processing:** `pdfplumber`
* **Standard Libraries:** `os`, `json`, `re`, `collections`, `datetime` (for file system operations, JSON handling, regular expressions, data structures, and timestamps).

## Technical Constraints & Considerations

The solution is engineered with specific technical constraints in mind to ensure efficient and reliable deployment:
* **CPU Architecture:** `amd64` (x86\_64).
* **No GPU Dependencies:** The system operates without requiring Graphics Processing Unit acceleration.
* **Offline Operation:** All processing occurs locally within the deployed environment, with no reliance on external network access or internet connectivity during runtime. All necessary dependencies and any models are self-contained within the application's package.
* **Resource Management:** Optimized for efficient use of memory and processing time.

## Execution Steps

### Prerequisites
* Docker Desktop installed and running on your system.
* PowerShell (recommended for Windows; Bash for Linux/macOS) terminal.

### Project Structure
Ensure your project directory is organized as follows:
```
├── Persona-Driven-Document-Intelligence/
│   ├── main.py                  # Main application logic
│   ├── Dockerfile               # Docker image definition
│   ├── .dockerignore            # Files/folders to exclude from Docker build
│   ├── requirements.txt         # Python dependencies
│   ├── README.md                # This file
│
│   ├── input/                   # Directory for input files
│   │   ├── document1.pdf        # Input PDF documents (3–10 related PDFs)
│   │   ├── document2.pdf
│   │   ├── persona.txt          # Defines the user persona (role/expertise)
│   │   └── job_to_be_done.txt   # Defines the user's task (goal/action)
│
│   └── output/                  # Directory for generated JSON results
│       └── challenge1b_output.json
```
### 1. Place Input Files
* Place all your PDF documents (e.g., `LLMs in Finance.pdf`, `Grounding LLMs.pdf`), the `persona.txt` file (containing the persona description), and the `job_to_be_done.txt` file (containing the job description) into the `input/` directory within your project's root.

### 2. Navigate to Project Root
* Open your PowerShell (or Bash) terminal.
* Navigate to the root directory of your project (the folder containing `Dockerfile`, `main.py`, `input/`, `output/`):
    ```powershell
    Set-Location C:\Path\To\Your\Project\Folder 
    # Example for Windows: Set-Location C:\Users\YourName\Documents\Persona-Driven-Document-Intelligence
    # Example for Linux/macOS Bash: cd /path/to/your/project/folder
    ```

### 3. Build the Docker Image
* This command compiles your application and its dependencies into a Docker image.
    ```powershell
    docker build --platform linux/amd64 -t persona-driven-document-intelligence:latest .
    ```
    *Replace `persona-driven-document-intelligence:latest` with a suitable unique image name and tag for your solution.*

### 4. Run the Docker Container
* This command executes your Docker image as a container, mounting your local `input` and `output` folders, and critically, disabling network access.
    ```powershell
    docker run --rm -v "$(Get-Location)/input:/app/input" -v "$(Get-Location)/output:/app/output" --network none persona-driven-document-intelligence:latest
    ```
    *Ensure the image name and tag `persona-driven-document-intelligence:latest` exactly matches the one you used in the build command.*

Upon successful completion, a JSON file containing the processed analysis will be generated in your local `output/` directory.
