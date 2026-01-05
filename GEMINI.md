# Project Overview

This project, "Belief Dispersion Sentiment Analysis for Stock News," is a research endeavor focused on analyzing sentiment patterns and belief heterogeneity in financial news. It leverages natural language processing (NLP) techniques, particularly Google's Gemini model for sentiment analysis, to understand how different news sources interpret stock-related information and its relationship with market movements.

**Key Technologies:**

*   **Python 3.8+**: The primary programming language.
*   **Jupyter Notebook**: For interactive analysis and development (`main.ipynb`).
*   **Hugging Face `datasets`**: For accessing the Financial News Dataset.
*   **Google Gemini API**: For performing sentiment analysis.
*   **pandas**: For data manipulation and analysis.
*   **nltk**: For natural language processing tasks.
*   **`python-dotenv`**: For managing environment variables.

**Architecture:**
The core analysis is performed within a Jupyter notebook (`main.ipynb`), which orchestrates data loading, preprocessing, sentiment analysis, belief dispersion metric calculation, and visualization.

# Building and Running

## Prerequisites
*   Python 3.8+
*   pip
*   Git
*   Google Cloud account (for Gemini API access)

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AminFiroozi/Belief-Dispersion.git
    cd Belief-Dispersion
    ```

2.  **Create and activate a virtual environment:**
    *   **On Windows:**
        ```bash
        python -m venv .venv
        .venv\Scripts\activate
        ```
    *   **On Unix/MacOS:**
        ```bash
        python -m venv .venv
        source .venv/bin/activate
        ```

3.  **Install required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the project root with your Google API key:
    ```
    GOOGLE_API_KEY=your_api_key_here
    ```

## Usage

1.  **Start Jupyter Notebook:**
    ```bash
    jupyter notebook
    ```

2.  **Open `main.ipynb`** to begin the analysis.

3.  **Follow the notebook cells** to:
    *   Load and preprocess the data.
    *   Perform sentiment analysis using Google's Gemini model.
    *   Calculate belief dispersion metrics.
    *   Generate visualizations.

# Development Conventions

## Contributing
If you'd like to contribute to this research project:

1.  Fork the repository.
2.  Create a feature branch.
3.  Submit a pull request with a detailed description of your changes.

## License
This project is licensed under the MIT License.

## Citation
If you use this research in your work, please cite:
```
@software{belief_dispersion_analysis,
  author = {Your Name},
  title = {Belief Dispersion Sentiment Analysis for Stock News},
  year = {2024},
  url = {https://github.com/AminFiroozi/Belief-Dispersion}
}
```