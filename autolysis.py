# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "seaborn",
#   "matplotlib",
#   "httpx",
#   "openai"
# ]
# ///

import os
import sys
import json
import logging
import base64
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
from typing import List, Dict, Any
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomatedAnalysis:
    def __init__(self, dataset_path: str):
        """
        Initialize the automated analysis with the given dataset.
        
        :param dataset_path: Path to the CSV file to analyze
        """
        try:
            logger.info(f"Initializing analysis for dataset: {dataset_path}")
            self.dataset_path = dataset_path
            
            # Validate CSV file
            if not os.path.exists(dataset_path):
                raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
            
            # Try multiple encodings
            encodings_to_try = [
                'utf-8', 
                'latin-1', 
                'iso-8859-1', 
                'cp1252', 
                'utf-16'
            ]
            
            for encoding in encodings_to_try:
                try:
                    self.df = pd.read_csv(dataset_path, encoding=encoding)
                    logger.info(f"Successfully loaded dataset using {encoding} encoding with {len(self.df)} rows")
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    logger.warning(f"Failed to read file with {encoding} encoding")
                    continue
            else:
                raise ValueError(f"Could not read the CSV file with any of the tried encodings")
            
            # Validate AI Proxy Token
            self.aiproxy_token = os.environ.get("AIPROXY_TOKEN")
            if not self.aiproxy_token:
                logger.error("AIPROXY_TOKEN environment variable is not set")
                raise ValueError("AIPROXY_TOKEN environment variable must be set")
        
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _generate_generic_analysis(self) -> Dict[str, Any]:
        """
        Perform generic data analysis.
        
        :return: Dictionary with analysis results
        """
        analysis = {
            "basic_info": {
                "total_rows": len(self.df),
                "total_columns": len(self.df.columns),
                "column_types": {col: str(dtype) for col, dtype in self.df.dtypes.items()}
            },
            "missing_values": self.df.isnull().sum().to_dict(),
            "descriptive_stats": {}
        }
        
        # Convert descriptive stats to dictionary with string representation
        try:
            desc_stats = self.df.describe()
            for col, stats in desc_stats.to_dict().items():
                analysis["descriptive_stats"][col] = {k: str(v) for k, v in stats.items()}
        except Exception as e:
            logger.warning(f"Could not generate descriptive statistics: {e}")
        
        # Try to find correlations if numeric columns exist
        numeric_columns = self.df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_columns) > 1:
            try:
                correlation_matrix = self.df[numeric_columns].corr()
                # Convert correlation matrix to dictionary with string representation
                analysis["correlation_matrix"] = {
                    str(col1): {str(col2): str(val) for col2, val in row.items()}
                    for col1, row in correlation_matrix.to_dict().items()
                }
            except Exception as e:
                logger.warning(f"Could not generate correlation matrix: {e}")
        
        return analysis
    
    def _call_llm(self, messages: List[Dict[str, str]], functions: List[Dict] = None):
        """
        Call the OpenAI-compatible LLM via AI Proxy with robust error handling.
        
        :param messages: List of message dictionaries
        :param functions: Optional list of function definitions
        :return: LLM response or fallback narrative
        """
        # List of potential AI Proxy endpoints
        endpoints = [
            "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        ]
        
        # Fallback narrative generator
        def generate_fallback_narrative(analysis):
            return f"""# Data Detective's Emergency Report

## Unexpected Narrative Generation Challenge

Our data storytelling mission encountered an unexpected roadblock. While our analytical engines are fully operational, our narrative generation system is temporarily offline.

### Preliminary Insights

**Dataset Snapshot:**
- Total Rows: {analysis.get('basic_info', {}).get('total_rows', 'N/A')}
- Total Columns: {analysis.get('basic_info', {}).get('total_columns', 'N/A')}

### Investigator's Notes

Despite the technical hiccup, our data analysis proceeded successfully. The visualizations and core insights remain intact.

**Recommended Next Steps:**
1. Verify AI Proxy configuration
2. Check network connectivity
3. Validate API tokens
4. Retry narrative generation

*Stay curious, stay analytical!*
"""
        
        try:
            for endpoint in endpoints:
                try:
                    logger.info(f"Attempting LLM call to {endpoint}")
                    
                    # Prepare request payload
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": messages,
                        "max_tokens": 1000,
                        "temperature": 0.7
                    }
                    
                    if functions:
                        payload["functions"] = functions
                    
                    # Make the API call
                    response = httpx.post(
                        endpoint, 
                        headers={
                            "Authorization": f"Bearer {self.aiproxy_token}",
                            "Content-Type": "application/json"
                        },
                        json=payload,
                        timeout=30.0  # 30-second timeout
                    )
                    
                    # Check response status
                    response.raise_for_status()
                    
                    # Parse and return response
                    result = response.json()
                    return result['choices'][0]['message']['content']
                
                except httpx.HTTPStatusError as http_err:
                    logger.warning(f"HTTP error with {endpoint}: {http_err}")
                    continue
                
                except httpx.RequestError as req_err:
                    logger.warning(f"Request error with {endpoint}: {req_err}")
                    continue
            
            # If all endpoints fail, log and return fallback
            logger.error("All LLM endpoints failed")
            return generate_fallback_narrative(self.analysis)
        
        except Exception as e:
            logger.error(f"Unexpected error in LLM call: {e}")
            logger.error(traceback.format_exc())
            return generate_fallback_narrative(self.analysis)
    
    def _create_visualizations(self, analysis: Dict[str, Any]):
        """
        Create visualizations based on the analysis.
        
        :param analysis: Dictionary containing analysis results
        """
        try:
            plt.figure(figsize=(16, 10))
            plt.subplots_adjust(hspace=0.4, wspace=0.4)
            
            # Visualization 1: Missing Values Storytelling
            plt.subplot(2, 2, 1)
            missing_values = pd.Series(analysis.get('missing_values', {}))
            missing_values = missing_values[missing_values > 0]
            
            if not missing_values.empty:
                missing_values.plot(kind='bar', color='steelblue', edgecolor='black')
                plt.title('Data Completeness: The Missing Pieces', fontsize=10, fontweight='bold')
                plt.xlabel('Columns', fontsize=8)
                plt.ylabel('Missing Values', fontsize=8)
                plt.xticks(rotation=45, ha='right', fontsize=7)
                plt.grid(axis='y', linestyle='--', alpha=0.7)
            else:
                plt.text(0.5, 0.5, 'No Missing Values\nPerfect Data Integrity', 
                         horizontalalignment='center', 
                         verticalalignment='center',
                         fontsize=10,
                         fontweight='bold',
                         color='darkgreen')
                plt.title('Data Completeness', fontsize=10)
            
            # Visualization 2: Distribution of Key Numeric Column
            plt.subplot(2, 2, 2)
            numeric_columns = [col for col, dtype in analysis['basic_info']['column_types'].items() 
                               if 'float' in dtype.lower() or 'int' in dtype.lower()]
            
            if numeric_columns:
                # Select the first numeric column for distribution
                first_numeric_col = numeric_columns[0]
                column_data = self.df[first_numeric_col]
                
                sns.histplot(column_data, kde=True, color='coral', edgecolor='black')
                plt.title(f'Distribution of {first_numeric_col}', fontsize=10, fontweight='bold')
                plt.xlabel(first_numeric_col, fontsize=8)
                plt.ylabel('Frequency', fontsize=8)
                plt.grid(axis='y', linestyle='--', alpha=0.7)
            else:
                plt.text(0.5, 0.5, 'No Numeric Columns\nInsufficient Data', 
                         horizontalalignment='center', 
                         verticalalignment='center',
                         fontsize=10,
                         fontweight='bold',
                         color='darkred')
                plt.title('Column Distribution', fontsize=10)
            
            # Visualization 3: Correlation Heatmap with Storytelling
            plt.subplot(2, 2, (3, 4))
            correlation_matrix = analysis.get('correlation_matrix', {})
            
            if correlation_matrix:
                # Convert correlation matrix to DataFrame with numeric values
                corr_df = pd.DataFrame({
                    col1: {col2: float(val) for col2, val in row.items()}
                    for col1, row in correlation_matrix.items()
                })
                
                plt.figure(figsize=(12, 8))
                sns.heatmap(corr_df, 
                            annot=True, 
                            cmap='coolwarm', 
                            center=0, 
                            square=True, 
                            linewidths=0.5, 
                            cbar_kws={"shrink": .8},
                            fmt=".2f",
                            annot_kws={"fontsize":6})
                plt.title('Correlation Landscape: Relationships Unveiled', fontsize=10, fontweight='bold')
                plt.xticks(rotation=45, ha='right', fontsize=7)
                plt.yticks(fontsize=7)
            else:
                plt.text(0.5, 0.5, 'No Correlation Data\nComplex Relationships', 
                         horizontalalignment='center', 
                         verticalalignment='center',
                         fontsize=10,
                         fontweight='bold',
                         color='darkblue')
                plt.title('Correlation Landscape', fontsize=10)
            
            # Save visualizations with high quality but reasonable size
            plt.tight_layout()
            plt.savefig('analysis_visualization.png', dpi=300, bbox_inches='tight')
            plt.close('all')
            
            logger.info("Visualizations created successfully")
        
        except Exception as e:
            logger.error(f"Error creating visualizations: {e}")
            logger.error(traceback.format_exc())
            
            # Fallback: Create a simple error visualization
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, f'Visualization Error:\n{str(e)}', 
                     horizontalalignment='center', 
                     verticalalignment='center')
            plt.title('Visualization Error')
            plt.axis('off')
            plt.savefig('analysis_visualization.png')
            plt.close('all')
    
    def generate_narrative(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a compelling narrative about the data analysis.
        
        :param analysis: Dictionary containing analysis results
        :return: Markdown narrative
        """
        try:
            # Prepare narrative prompt with storytelling elements
            prompt = f"""
You are a data storyteller, transforming raw numbers into a captivating narrative. 
Write an engaging story about this dataset that reads like a detective uncovering hidden truths.

Dataset Overview:
- Total Rows: {analysis['basic_info']['total_rows']}
- Total Columns: {analysis['basic_info']['total_columns']}
- Column Types: {json.dumps(analysis['basic_info']['column_types'], indent=2)}

Missing Data Landscape:
{json.dumps(analysis.get('missing_values', {}), indent=2)}

Descriptive Statistics Snapshot:
{json.dumps(analysis.get('descriptive_stats', {}), indent=2)}

Correlation Insights:
{json.dumps(analysis.get('correlation_matrix', {}), indent=2)}

Craft your narrative with these key elements:
1. HOOK: Start with an intriguing opening that captures the essence of the data
2. DATA DESCRIPTION: Briefly explain the dataset's origin and structure
3. DETECTIVE WORK: Describe the analytical journey and methods used
4. REVELATIONS: Share the most surprising and significant insights
5. IMPLICATIONS: Provide actionable recommendations
6. FUTURE OUTLOOK: Suggest potential next steps or further investigations

Write in a narrative style that would engage both data scientists and storytellers. 
Use markdown formatting, include headers, and make it read like a page-turning story.

IMPORTANT: Keep the tone professional yet conversational. 
Use metaphors, but avoid being overly dramatic.

Maximum length: 1000 words
"""
            
            # Call LLM to generate narrative
            narrative = self._call_llm([{"role": "user", "content": prompt}])
            
            # Enhance narrative with visualization references
            enhanced_narrative = f"""# Data Detective: Unraveling Hidden Insights

{narrative}

## Visualizations

Our investigation was supported by these key visual evidence:

1. **Missing Values Map**: Reveals the landscape of data completeness
   ![Missing Values Analysis](analysis_visualization.png)

2. **Correlation Heatmap**: Unveils the intricate relationships within the data
   ![Correlation Insights](analysis_visualization.png)

### Methodology

- **Analytical Approach**: Comprehensive, data-driven investigation
- **Tools**: Python, Pandas, Seaborn
- **Technique**: Multi-dimensional statistical analysis

**Note**: This narrative is an AI-generated interpretation of the data, designed to provide insights and provoke further exploration.
"""
            
            return enhanced_narrative
        
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            logger.error(traceback.format_exc())
            
            # Fallback narrative
            return f"""# Data Analysis Narrative

## Unexpected Journey

Our data detective encountered an unexpected challenge during the investigation.

**Case File**: Unable to generate complete narrative
**Investigator's Notes**: {str(e)}

### Preliminary Findings
- Total Rows: {analysis['basic_info']['total_rows']}
- Total Columns: {analysis['basic_info']['total_columns']}

*Further investigation required.*
"""
    
    def run_analysis(self):
        """
        Run the complete automated analysis workflow.
        """
        try:
            logger.info(f"Starting analysis for {self.dataset_path}")
            
            # Perform generic data analysis
            self.analysis = self._generate_generic_analysis()
            logger.info("Generic analysis completed")
            
            # Create visualizations
            self._create_visualizations(self.analysis)
            logger.info("Visualizations created")
            
            # Generate narrative
            narrative = self.generate_narrative(self.analysis)
            logger.info("Narrative generation completed")
            
            # Write README.md
            with open('README.md', 'w') as f:
                f.write(narrative)
            
            logger.info("Analysis complete. Check README.md and analysis_visualization.png")
        
        except Exception as e:
            logger.error(f"Analysis workflow error: {e}")
            logger.error(traceback.format_exc())
            
            # Fallback README generation
            fallback_readme = f"""# Data Analysis Emergency Report

## Workflow Interruption

An unexpected error occurred during the analysis of {self.dataset_path}:

**Error Details:**
```
{str(e)}
```

**Traceback:**
```
{traceback.format_exc()}
```

### Recommended Actions
1. Verify dataset integrity
2. Check script dependencies
3. Review error logs
4. Retry analysis

*Automated Analysis System*
"""
            
            with open('README.md', 'w') as f:
                f.write(fallback_readme)

def main():
    try:
        # Validate command-line arguments
        if len(sys.argv) != 2:
            logger.error("Incorrect usage. Please provide a CSV file.")
            print("Usage: uv run autolysis.py <dataset.csv>")
            sys.exit(1)
        
        # Validate file extension
        dataset_path = sys.argv[1]
        if not dataset_path.lower().endswith('.csv'):
            logger.error(f"Invalid file type: {dataset_path}. Must be a CSV file.")
            print("Error: Input must be a CSV file")
            sys.exit(1)
        
        # Determine output directory based on dataset name
        dataset_name = os.path.splitext(os.path.basename(dataset_path))[0]
        output_dir = dataset_name.lower()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Run analysis
        try:
            analyzer = AutomatedAnalysis(dataset_path)
            analyzer.run_analysis()
            logger.info("Analysis completed successfully")
            
            # Move outputs to dataset-specific directory
            readme_path = 'README.md'
            png_files = [f for f in os.listdir('.') if f.endswith('.png')]
            
            if os.path.exists(readme_path):
                os.rename(readme_path, os.path.join(output_dir, readme_path))
            
            for png_file in png_files:
                os.rename(png_file, os.path.join(output_dir, png_file))
            
            print(f"Analysis results saved in {output_dir} directory")
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            logger.error(traceback.format_exc())
            print(f"Error during analysis: {e}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
