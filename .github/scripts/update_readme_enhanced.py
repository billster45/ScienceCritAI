#!/usr/bin/env python3
"""
Enhanced script to parse HTML files and update README with organized links, metadata,
and LLM-powered categorization and descriptions.
"""

import os
import glob
import json
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
import re
from typing import Dict, List, Any, Optional

# Try to import OpenAI for LLM features
try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Refined categories (no General Science bucket)
CATEGORIES = [
    "AI & Machine Learning",
    "Neuroscience & Brain Research", 
    "Cardiovascular Health",
    "Cancer Research",
    "Infectious Diseases & Epidemiology",
    "Exercise & Sports Science",
    "Nutrition & Metabolism",
    "Psychology & Mental Health",
    "Environmental Health",
    "Aging & Longevity",
    "Genetics & Genomics",
    "Public Health & Healthcare Systems",
    "Pharmacology & Drug Discovery",
    "Sleep & Circadian Biology",
    "Education & Learning Sciences"
]

# Cache file for storing LLM results
CACHE_FILE = '.llm_cache.json'

def load_cache():
    """Load existing LLM results cache"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    """Save LLM results cache"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)

def extract_metadata_from_html(html_file):
    """Extract title, authors, journal, and institution from HTML file."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract from paper-metadata div
        metadata_div = soup.find('div', class_='paper-metadata')
        if metadata_div:
            title_elem = metadata_div.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            authors_elem = metadata_div.find('div', class_='authors')
            authors = authors_elem.get_text(strip=True) if authors_elem else None
            
            journal_elem = metadata_div.find('div', class_='journal')
            journal = journal_elem.get_text(strip=True) if journal_elem else None
            
            institution_elem = metadata_div.find('div', class_='institution')
            institution = institution_elem.get_text(strip=True) if institution_elem else None
        else:
            # Fallback to title tag
            title_elem = soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else None
            authors = None
            journal = None
            institution = None
        
        return {
            'title': title,
            'authors': authors,
            'journal': journal,
            'institution': institution
        }
    except Exception as e:
        print(f"Error parsing {html_file}: {e}")
        return None

def extract_date_from_filename(filename):
    """Extract date from filename pattern like 'name_YYYYMMDD_HHMMSS.html'"""
    match = re.search(r'_(\d{8})_\d{6}\.html$', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            pass
    return None

def extract_text_from_html(html_file, max_chars=2000):
    """Extract first portion of HTML content for LLM analysis"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        # Clean up whitespace
        text = ' '.join(text.split())
        return text[:max_chars]
        
    except Exception as e:
        print(f"Error extracting text from {html_file}: {e}")
        return ""

async def categorize_and_describe_paper(
    filename: str,
    metadata: Dict,
    html_content: str,
    openai_client: AsyncOpenAI,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """Use LLM to categorize paper and generate description"""
    
    # Build context from metadata and content
    context_parts = []
    
    if metadata:
        if metadata.get('title'):
            context_parts.append(f"Title: {metadata['title']}")
        if metadata.get('authors'):
            context_parts.append(f"Authors: {metadata['authors']}")
        if metadata.get('journal'):
            context_parts.append(f"Journal: {metadata['journal']}")
        if metadata.get('institution'):
            context_parts.append(f"Institution: {metadata['institution']}")
    
    if html_content:
        context_parts.append(f"\nPaper excerpt:\n{html_content}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""Analyze this scientific paper and provide:
1. The most appropriate category from this list: {', '.join(CATEGORIES)}
2. A brief 2-3 sentence description of why this paper is worth reading, highlighting its key findings or significance.

Paper information:
{context}

Please respond in JSON format:
{{
    "category": "selected category from the list",
    "description": "2-3 sentence description of why this paper is worth reading"
}}"""

    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a scientific paper categorization expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate category
        if result.get('category') not in CATEGORIES:
            # Find closest match or default
            result['category'] = "AI & Machine Learning"  # Default fallback
        
        return result
        
    except Exception as e:
        print(f"Error calling OpenAI API for {filename}: {e}")
        return {
            "category": "AI & Machine Learning",  # Default
            "description": "This paper presents important research findings in its field."
        }

def categorize_papers_legacy(papers):
    """Legacy categorization using keyword matching"""
    categories = {
        'AI & Machine Learning': [],
        'Health & Medicine': [],
        'Exercise & Fitness': [],
        'Nutrition & Diet': [],
        'Psychology & Mental Health': [],
        'General Science': []
    }
    
    # Keywords for categorization
    ai_keywords = ['_ai_', 'llm_', 'gpt', '_ml_', 'machine_learning', 'deepseekr1', 'chatgpt', 'claude', 'notebooklm', 'transformer']
    health_keywords = ['covid', 'dementia', 'alzheimers', 'cvd_', 'ldl_', 'hospital', 'medical', 'diagnosis', 'cancer', '_brain_', 'aging', 'mortality', 'insulin', 'diabetes', 'warburg', 'glioblastoma', 'microplastics', 'plastics', 'appointment', 'nursing_home', 'taxi_ambulance']
    exercise_keywords = ['exercise', 'fitness', 'hiit', 'training', 'aerobic', 'strength', 'muscle', 'workout', 'physical', 'resistance_training', 'weekend_warrior', 'massage_gun', 'pomegranate_sport']
    nutrition_keywords = ['diet', 'nutrition', 'protein', 'vitamin', 'omega', 'cocoa', 'coffee', 'tea', 'creatine', 'food', '_eat', '_fat', 'carragean', 'whey_protein', 'oreo_cookie', 'junk_food', 'restricted_eating', 'fruit_veg', 'nuts_', 'upf_', 'macrontrients', 'energy_intake']
    psychology_keywords = ['depression', 'mental_health', 'stress', 'therapy', 'cbt', '_sleep', 'mood', 'psychology', 'npd', 'suicide', 'spiritual', 'autism', 'leaving_science', 'transcranial', 'multivitamin_stress']
    
    for paper in papers:
        filename_lower = paper['filename'].lower()
        
        # Check categories in order of specificity
        if any(keyword in filename_lower for keyword in ai_keywords):
            categories['AI & Machine Learning'].append(paper)
        elif any(keyword in filename_lower for keyword in exercise_keywords):
            categories['Exercise & Fitness'].append(paper)
        elif any(keyword in filename_lower for keyword in nutrition_keywords):
            categories['Nutrition & Diet'].append(paper)
        elif any(keyword in filename_lower for keyword in psychology_keywords):
            categories['Psychology & Mental Health'].append(paper)
        elif any(keyword in filename_lower for keyword in health_keywords):
            categories['Health & Medicine'].append(paper)
        else:
            categories['General Science'].append(paper)
    
    return categories

async def categorize_papers_with_llm(papers: List[Dict], openai_api_key: str):
    """Categorize papers using LLM, with caching to avoid repeat API calls"""
    
    # Load cache
    cache = load_cache()
    
    # Identify new papers that need LLM processing
    new_papers = []
    for paper in papers:
        if paper['filename'] not in cache:
            new_papers.append(paper)
    
    print(f"Found {len(new_papers)} new papers to process with LLM out of {len(papers)} total")
    
    if new_papers and openai_api_key and HAS_OPENAI:
        try:
            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=openai_api_key)
            
            # Process new papers in batches
            batch_size = 3  # Conservative to avoid rate limits
            
            for i in range(0, len(new_papers), batch_size):
                batch = new_papers[i:i+batch_size]
                print(f"Processing LLM batch {i//batch_size + 1}/{(len(new_papers) + batch_size - 1)//batch_size}")
                
                tasks = []
                for paper in batch:
                    # Extract HTML content
                    html_content = extract_text_from_html(paper['filename'])
                    
                    # Create categorization task
                    task = categorize_and_describe_paper(
                        paper['filename'],
                        paper.get('metadata', {}),
                        html_content,
                        client
                    )
                    tasks.append((paper, task))
                
                # Process batch
                batch_results = await asyncio.gather(*[task for _, task in tasks])
                
                # Store results in cache
                for (paper, _), result in zip(tasks, batch_results):
                    cache[paper['filename']] = result
                    print(f"  Processed: {paper['filename']} -> {result['category']}")
                
                # Save cache after each batch
                save_cache(cache)
                
                # Small delay between batches
                if i + batch_size < len(new_papers):
                    await asyncio.sleep(2)
        
        except Exception as e:
            print(f"Error during LLM processing: {e}")
            print("Falling back to legacy categorization")
    
    # Assign categories and descriptions to all papers
    categorized_papers = {cat: [] for cat in CATEGORIES}
    
    for paper in papers:
        llm_result = cache.get(paper['filename'], {
            'category': 'AI & Machine Learning',
            'description': 'This paper presents important research findings in its field.'
        })
        
        paper['llm_category'] = llm_result.get('category', 'AI & Machine Learning')
        paper['llm_description'] = llm_result.get('description', 'This paper presents important research findings in its field.')
        
        categorized_papers[paper['llm_category']].append(paper)
    
    return categorized_papers

def clean_title_for_link(title):
    """Clean title by removing newlines and extra whitespace for use in markdown links."""
    if not title:
        return title
    # Replace newlines with spaces and collapse multiple spaces into one
    cleaned = re.sub(r'\s+', ' ', title.strip())
    return cleaned

def generate_readme_content(categories, base_url="https://billster45.github.io/ScienceCritAI", use_llm=True):
    """Generate README content with organized paper links."""
    content = [
        "# ScienceCritAI",
        "",
        "A collection of AI-automated scientific paper peer reviews posted on X/Twitter at [@ScienceCrit_AI](https://x.com/ScienceCrit_AI).",
        "",
        "Learn how this project works on Medium: [From PDFs to Tweets: How tools like ScienceCritAI could transform scientific peer review](https://medium.com/@billcockerill/from-pdfs-to-tweets-how-tools-like-sciencecritai-could-transform-scientific-peer-review-142786283ecf)",
        "",
        "## Table of Contents",
        ""
    ]
    
    category_list = CATEGORIES if use_llm else list(categories.keys())
    
    for category in category_list:
        if categories.get(category, []):
            content.append(f"- [{category}](#{category.lower().replace(' ', '-').replace('&', '')})")
    
    content.extend(["", "---", ""])
    
    # Add papers by category
    for category in category_list:
        papers = categories.get(category, [])
        if not papers:
            continue
            
        content.extend([
            f"## {category}",
            "",
            "[↑ Back to top](#sciencecritai)",
            ""
        ])
        
        # Sort papers by date (newest first)
        papers_with_dates = []
        for paper in papers:
            date = extract_date_from_filename(paper['filename'])
            papers_with_dates.append((paper, date))
        
        papers_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
        
        for paper, date in papers_with_dates:
            metadata = paper['metadata']
            url = f"{base_url}/{paper['filename']}"
            
            # Create paper entry
            if metadata and metadata.get('title'):
                title = clean_title_for_link(metadata['title'])
            else:
                title = os.path.splitext(paper['filename'])[0].replace('_', ' ').title()
            
            content.append(f"### [{title}]({url})")
            
            # Add LLM description if available
            if use_llm and paper.get('llm_description'):
                content.append(f"**Why read this:** {paper['llm_description']}")
                content.append("")
            
            # Add metadata in specific order: Date, Journal, Institution, Authors
            if date:
                content.append(f"**Date:** {date.strftime('%Y-%m-%d')}")
            
            if metadata:
                if metadata.get('journal'):
                    content.append(f"**Journal:** {metadata['journal']}")
                if metadata.get('institution'):
                    content.append(f"**Institution:** {metadata['institution']}")
                if metadata.get('authors'):
                    content.append(f"**Authors:** {metadata['authors']}")
            
            content.extend(["", "---", ""])
    
    # Add footer
    content.extend([
        "",
        f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        f"*Total papers: {sum(len(papers) for papers in categories.values())}*"
    ])
    
    return '\n'.join(content)

async def main():
    """Main function to update README."""
    # Find all HTML files in the root directory
    html_files = glob.glob('*.html')
    
    if not html_files:
        print("No HTML files found in root directory")
        return
    
    print(f"Found {len(html_files)} HTML files")
    
    # Extract metadata from each file
    papers = []
    for html_file in html_files:
        print(f"Processing {html_file}...")
        metadata = extract_metadata_from_html(html_file)
        papers.append({
            'filename': html_file,
            'metadata': metadata
        })
    
    # Get OpenAI API key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if openai_api_key and HAS_OPENAI:
        print("Using enhanced LLM categorization and descriptions")
        # Categorize papers with LLM
        categories = await categorize_papers_with_llm(papers, openai_api_key)
        use_llm = True
    else:
        print("Using legacy keyword-based categorization")
        # Fall back to legacy categorization
        categories = categorize_papers_legacy(papers)
        use_llm = False
    
    # Generate README content
    readme_content = generate_readme_content(categories, use_llm=use_llm)
    
    # Write to README.md
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"Successfully updated README.md with {len(papers)} papers")
    
    # Print summary
    for category, papers in categories.items():
        if papers:
            print(f"  {category}: {len(papers)} papers")

def main_sync():
    """Synchronous wrapper for main function"""
    asyncio.run(main())

if __name__ == '__main__':
    main_sync()