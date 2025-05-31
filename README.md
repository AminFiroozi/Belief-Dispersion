# Belief Dispersion Sentiment Analysis for Stock News

## Overview
This research project focuses on analyzing belief dispersion in stock market news through sentiment analysis. The project aims to understand how different news sources and market participants interpret and report on stock-related information, potentially revealing market sentiment and belief heterogeneity.

## Research Goals
- Analyze sentiment patterns in stock market news across different sources
- Measure belief dispersion among market participants through news sentiment
- Investigate the relationship between sentiment dispersion and market movements
- Develop quantitative metrics for belief heterogeneity in financial news

## Dataset
This project uses the Financial News Dataset from Hugging Face, which contains over 1.8 million financial news articles. The dataset includes:
- Headlines
- Article URLs
- Publisher information
- Publication dates
- Stock symbols

You can access the dataset here: [Financial News Dataset](https://huggingface.co/datasets/ashraq/financial-news)

To use the dataset:
```python
from datasets import load_dataset
dataset = load_dataset("ashraq/financial-news")
```

## Project Structure
```
.
├── main.ipynb          # Main analysis notebook
├── requirements.txt    # Project dependencies
├── .gitignore         # Git ignore file
└── .env              # Environment variables (not tracked in git)
```

## Setup and Installation

### Prerequisites
- Python 3.8+
- pip (Python package installer)
- Git
- Google Cloud account (for Gemini API access)

### Dependencies
The project requires the following packages:

#### Core Dependencies
- pandas: For data manipulation and analysis
- nltk: For natural language processing
- datasets: For accessing the Hugging Face dataset
- google-generativeai: For using Google's Gemini model
- python-dotenv: For managing environment variables

#### Additional Dependencies
- protobuf==4.23.4
- websockets==8.1
- tensorboard==2.15.1
- tensorflow-intel==2.15.0
- tradermade==0.5.0
- jupyter: For running Jupyter notebooks
- ipykernel: For Jupyter notebook support

### Installation
1. Clone the repository:
```bash
git clone https://github.com/AminFiroozi/Belief-Dispersion.git
cd belief-dispersion
```

2. Create and activate a virtual environment (recommended):
```bash
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On Unix/MacOS
python -m venv .venv
source .venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with your Google API key:
```
GOOGLE_API_KEY=your_api_key_here
```

## Dataset Usage
The project uses the Financial News Dataset from Hugging Face. To get started:

1. Install the required packages (see Installation section)
2. Access the dataset using the Hugging Face datasets library:
```python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("ashraq/financial-news")

# The dataset contains the following columns:
# - headline: The news headline
# - url: Source URL of the article
# - publisher: Name of the news publisher
# - date: Publication date
# - stock_symbol: Associated stock symbol
```

## Usage
1. Start Jupyter Notebook:
```bash
jupyter notebook
```

2. Open `main.ipynb` to begin the analysis
3. Follow the notebook cells to:
   - Load and preprocess the data
   - Perform sentiment analysis using Google's Gemini model
   - Calculate belief dispersion metrics
   - Generate visualizations

## Research Methodology
The project employs advanced natural language processing (NLP) techniques to:
1. Collect and preprocess financial news data
2. Perform sentiment analysis using Google's Gemini model
3. Calculate belief dispersion metrics
4. Analyze temporal patterns and correlations with market data

## Contributing
This is a research project. If you'd like to contribute:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with a detailed description of your changes

## License
This project is licensed under the MIT License - see the LICENSE file for details.

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

## Contact
For questions or collaborations, please open an issue in the repository or contact [afiroozi83@gmail.com]. 