# SCORM Package Inspector

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://os-scorm-inspector.streamlit.app/)

A web application built with Streamlit to parse, validate, and inspect SCORM 1.2 and SCORM 2004 packages. This tool is designed for instructional designers, LMS administrators, and e-learning developers who need a quick way to diagnose potential issues with SCORM content before uploading it to a Learning Management System (LMS).

## Live Application

You can use the live, deployed version of this tool here:

**[https://os-scorm-inspector.streamlit.app/](https://os-scorm-inspector.streamlit.app/)**

## Features

*   **Parse SCORM Manifest:** Reads the `imsmanifest.xml` file to display the complete structure of the course.
*   **Package Validation:** Automatically checks for common issues that can cause errors in an LMS, such as:
    *   Broken links between items and resources.
    *   File references that point to files missing from the `.zip` package.
*   **Metadata Extraction:** Pulls key metadata from the manifest, including:
    *   Course Title and Description
    *   Passing/Mastery Score
    *   Launch File
    *   SCORM Version (1.2 or 2004)
*   **Component Analysis:** Identifies and counts the number of trackable Shareable Content Objects (SCOs) versus non-trackable Assets.
*   **Multiple Data Views:** Presents the analysis in several useful formats:
    *   **Summary & Metadata:** An at-a-glance profile of the course.
    *   **Validation Report:** A clear, color-coded list of any potential problems.
    *   **Content Map:** A flattened table view of all course items (downloadable as a CSV).
    *   **Hierarchical View:** A collapsible JSON tree representing the course structure.
    *   **Raw Manifest:** The full `imsmanifest.xml` content for deep dives.

## How to Use the Deployed App

This tool is optimized for a workflow common in LMS environments like Brightspace/D2L, where direct links to content are not available.

1.  **Download from your LMS:**
    *   Navigate to your course's content management area (e.g., in Brightspace, go to **Course Admin** > **Manage Files**).
    *   Locate the SCORM `.zip` file you wish to inspect and **Download** it to your computer.

2.  **Open the Inspector Tool:**
    *   Navigate to the [SCORM Inspector app](https://os-scorm-inspector.streamlit.app/).

3.  **Upload and Analyze:**
    *   On the inspector tool's page, use the **"Upload a local file"** option.
    *   Select the `.zip` file you just downloaded from your LMS.
    *   The tool will automatically analyze the package and display the results.

## Screenshot

<img width="1863" height="885" alt="image" src="https://github.com/user-attachments/assets/a4294225-583f-48d0-b983-1bc1c7cd9f06" />





## Running Locally (For Developers)

If you want to run this application on your local machine for development purposes:

**1. Prerequisites:**
*   Python 3.8 or higher installed.

**2. Clone the Repository:**
bash

   git clone https://github.com/your-username/scorm-inspector-app.git
   cd scorm-inspector-app

**3. Create and Activate a Virtual Environment (Recommended):**

    Windows:

Bash

```python -m venv venv```
```venv\Scripts\activate```

macOS / Linux:

Bash

    ```python3 -m venv venv```
    ```source venv/bin/activate```

4. Install Dependencies:

Bash

```pip install -r requirements.txt```

5. Run the App:

Bash

```streamlit run scorm_app_v12.py```

The application will open in a new tab in your default web browser.

.
├── scorm_app_v12.py    # The main Streamlit application script.
├── requirements.txt      # Python dependencies for the project.
└── README.md           # This file.


License

This project is open source and available under the MIT License.
