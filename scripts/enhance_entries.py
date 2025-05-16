import re
from pathlib import Path
from typing import Dict, Callable, Optional
import anthropic
from datetime import datetime
import json
import time

def parse_entry_metadata(entry_text: str) -> Dict:
    """Extract metadata from a journal entry."""
    metadata = {}
    
    # Extract date
    date_match = re.search(r'Date: (\d{4}-\d{2}-\d{2})', entry_text)
    if date_match:
        metadata['date'] = date_match.group(1)
    
    # Extract destination and start location
    dest_match = re.search(r'Destination: (.*?)$', entry_text, re.MULTILINE)
    start_match = re.search(r'Start Location: (.*?)$', entry_text, re.MULTILINE)
    if dest_match:
        metadata['destination'] = dest_match.group(1).strip()
    if start_match:
        metadata['start_location'] = start_match.group(1).strip()
    
    # Extract miles
    miles_match = re.search(r'Miles Hiked: ([\d.]+)', entry_text)
    total_match = re.search(r'Total Trip Miles: ([\d.]+)', entry_text)
    if miles_match:
        metadata['miles_hiked'] = float(miles_match.group(1))
    if total_match:
        metadata['total_miles'] = float(total_match.group(1))
    
    return metadata

def get_trail_context(metadata: Dict, client: anthropic.Client) -> str:
    """Get AI-generated context about the trail section."""
    prompt = f"""Given the following hiking information, provide a brief paragraph (2-3 sentences) describing what this section of the Appalachian Trail might have been like on {metadata['date']}:

Start Location: {metadata['start_location']}
Destination: {metadata['destination']}
Miles Hiked: {metadata['miles_hiked']}
Total Trip Miles: {metadata['total_miles']}

Focus on:
1. Typical terrain and features of this section
2. What the weather and conditions might have been like at this time of year
3. Any notable landmarks or challenges in this section

Keep the response concise and factual."""
    
    try:
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=150,
            temperature=0.7,
            system="You are a helpful assistant that provides factual information about the Appalachian Trail.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error getting trail context: {e}")
        return ""

def enhance_journal(
    input_file: Path,
    output_file: Path,
    claude_client: Optional[Callable] = None,
    cache_file: Optional[Path] = None
) -> None:
    """Enhance a journal with AI-generated trail context."""
    # Initialize Claude client if not provided
    if claude_client is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        client = anthropic.Client(api_key=api_key)
        claude_client = lambda metadata: get_trail_context(metadata, client)
    
    # Load cache if provided
    cache = {}
    if cache_file and cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            cache = {}
    
    # Read and process the journal
    content = input_file.read_text()
    entries = content.split('\n---\n')
    enhanced_entries = []
    
    for entry in entries:
        if not entry.strip():
            continue
            
        metadata = parse_entry_metadata(entry)
        if not metadata:
            enhanced_entries.append(entry)
            continue
        
        # Create cache key
        cache_key = f"{metadata['date']}_{metadata['start_location']}_{metadata['destination']}"
        
        # Get or generate context
        if cache_key in cache:
            context = cache[cache_key]
        else:
            context = claude_client(metadata)
            if context:
                cache[cache_key] = context
                if cache_file:
                    cache_file.write_text(json.dumps(cache, indent=2))
            time.sleep(1)  # Rate limiting
        
        # Add context to entry
        if context:
            enhanced_entry = f"{entry.strip()}\n\nTrail Context: {context}\n"
        else:
            enhanced_entry = entry
            
        enhanced_entries.append(enhanced_entry)
    
    # Write enhanced journal
    output_file.write_text('\n---\n'.join(enhanced_entries))

if __name__ == '__main__':
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhance a trail journal with AI-generated context')
    parser.add_argument('input_file', type=Path, help='Path to the input journal file')
    parser.add_argument('--output', type=Path, help='Path to the output file (default: input_file_enhanced.txt)')
    parser.add_argument('--cache', type=Path, help='Path to cache file for API responses')
    
    args = parser.parse_args()
    
    if not args.output:
        args.output = args.input_file.parent / f"{args.input_file.stem}_enhanced{args.input_file.suffix}"
    
    enhance_journal(args.input_file, args.output, cache_file=args.cache)
    print(f"Enhanced journal written to: {args.output}") 