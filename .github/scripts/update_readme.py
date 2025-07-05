#!/usr/bin/env python3
"""
Script to parse HTML files and update README with organized links and metadata.
"""

import os
import glob
from bs4 import BeautifulSoup
from datetime import datetime
import re

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

def categorize_papers(papers):
    """Categorize papers by topic based on filename patterns."""
    categories = {
        'AI & Machine Learning': [],
        'Health & Medicine': [],
        'Exercise & Fitness': [],
        'Nutrition & Diet': [],
        'Psychology & Mental Health': [],
        'General Science': []
    }
    
    # Keywords for categorization - use more specific patterns to avoid false matches
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

def clean_title_for_link(title):
    """Clean title by removing newlines and extra whitespace for use in markdown links."""
    if not title:
        return title
    # Replace newlines with spaces and collapse multiple spaces into one
    cleaned = re.sub(r'\s+', ' ', title.strip())
    return cleaned

def generate_readme_content(categories, base_url="https://billster45.github.io/ScienceCritAI"):
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
    
    for category in categories:
        if categories[category]:
            content.append(f"- [{category}](#{category.lower().replace(' ', '-').replace('&', '')})")
    
    content.extend(["", "---", ""])
    
    # Add papers by category
    for category, papers in categories.items():
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
                # Clean the title to remove newlines for the link
                title = clean_title_for_link(metadata['title'])
            else:
                # Fallback to filename without extension
                title = os.path.splitext(paper['filename'])[0].replace('_', ' ').title()
            
            content.append(f"### [{title}]({url})")
            
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

def main():
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
    
    # Categorize papers
    categories = categorize_papers(papers)
    
    # Generate README content
    readme_content = generate_readme_content(categories)
    
    # Write to README.md
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"Successfully updated README.md with {len(papers)} papers")
    
    # Print summary
    for category, papers in categories.items():
        if papers:
            print(f"  {category}: {len(papers)} papers")

if __name__ == '__main__':
    main()