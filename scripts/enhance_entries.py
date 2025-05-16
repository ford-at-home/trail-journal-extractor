import re
from pathlib import Path
from typing import Dict, Callable, Optional, List, Set
import json
import time
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import tempfile
import shutil

def log_message(message: str, level: str = "INFO") -> None:
    """Print a timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def parse_entry_metadata(entry_text: str) -> Dict:
    """Extract metadata from a journal entry."""
    metadata = {}
    
    # Extract date and destination from header
    header_match = re.search(r'# (.*?) — (.*?)$', entry_text, re.MULTILINE)
    if header_match:
        date_str = header_match.group(1).strip()
        metadata['destination'] = header_match.group(2).strip()
        # Convert date from "Thursday, January 21, 2010" to "2010-01-21"
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%A, %B %d, %Y")
            metadata['date'] = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            log_message(f"Could not parse date '{date_str}'", "WARNING")
    
    # Extract start location
    start_match = re.search(r'\*\*Start Location:\*\* (.*?)$', entry_text, re.MULTILINE)
    if start_match:
        metadata['start_location'] = start_match.group(1).strip()
    
    # Extract miles
    miles_match = re.search(r'\*\*Miles Today:\*\* ([\d.]+)', entry_text)
    total_match = re.search(r'\*\*Trip Miles:\*\* ([\d.]+)', entry_text)
    if miles_match:
        metadata['miles_hiked'] = float(miles_match.group(1))
    if total_match:
        metadata['total_miles'] = float(total_match.group(1))
    
    return metadata

def get_trail_context_bedrock(metadata: Dict, client, model_id: str) -> str:
    """Get AI-generated context about the trail section using AWS Bedrock."""
    prompt = f"""
    
You are an experienced and opinionated Appalachian Trail guru.
Given the following hiking information, provide a brief paragraph (2-3 sentences) describing what this section of the Appalachian Trail might have been like on {metadata['date']}:

Start Location: {metadata['start_location']}
Destination: {metadata['destination']}
Miles Hiked: {metadata['miles_hiked']}
Total Trip Miles: {metadata['total_miles']}

Focus on what would a northbound AT thru-huker have seen, smelled, heard, felt, experienced?

2. Otherwise, what's interesting/memorable about this hiking trail section?

Keep the response concise & factual with a touch of poetry."""
    
    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        }
    ]
    try:
        response = client.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={"maxTokens": 2000, "temperature": 0.7, "topP": 0.9},
        )
        return response["output"]["message"]["content"][0]["text"]
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return ""

def get_trail_facts_bedrock(metadata: Dict, client, model_id: str) -> str:
    """Get AI-generated facts about significant landmarks and features of this trail section."""
    prompt = f"""You are an Appalachian Trail expert with deep knowledge of every landmark, shelter, and significant feature.

Given this section of the AT from {metadata['start_location']} to {metadata['destination']} on {metadata['date']}, provide a concise paragraph (2-3 sentences) highlighting the most notable and meaningful aspects of this section.

Focus on:
1. Specific landmarks (summits, shelters, hostels, road crossings)
2. Historical or cultural significance
3. Unique features that make this section memorable
4. Insider knowledge that only experienced hikers would know

Keep it factual but engaging, like a trail veteran sharing wisdom. Include specific names and details that would matter to a thru-hiker."""
    
    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        }
    ]
    try:
        response = client.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={"maxTokens": 2000, "temperature": 0.7, "topP": 0.9},
        )
        return response["output"]["message"]["content"][0]["text"]
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return ""

def save_progress(progress_file: Path, processed_entries: Set[int], enhanced_entries: List[str]) -> None:
    """Save progress to a temporary file and then atomically move it into place."""
    # Create a temporary file in the same directory as the progress file
    temp_file = progress_file.with_suffix('.tmp')
    
    # Save both the processed entries and the enhanced content
    progress_data = {
        'processed_entries': sorted(list(processed_entries)),
        'enhanced_entries': enhanced_entries
    }
    
    # Write to temp file first
    with temp_file.open('w') as f:
        json.dump(progress_data, f)
    
    # Atomically move the temp file into place
    shutil.move(str(temp_file), str(progress_file))
    log_message(f"Progress saved: {len(processed_entries)} entries processed")

def load_progress(progress_file: Path) -> tuple[Set[int], List[str]]:
    """Load progress from the progress file."""
    if not progress_file.exists():
        return set(), []
    
    try:
        with progress_file.open('r') as f:
            progress_data = json.load(f)
        processed_entries = set(progress_data['processed_entries'])
        enhanced_entries = progress_data['enhanced_entries']
        log_message(f"Loaded progress: {len(processed_entries)} entries previously processed")
        return processed_entries, enhanced_entries
    except (json.JSONDecodeError, KeyError) as e:
        log_message(f"Error loading progress file: {e}", "WARNING")
        return set(), []

def get_entry_key(metadata: Dict) -> str:
    """Generate a unique key for an entry based on its metadata."""
    return f"{metadata['date']}_{metadata['start_location']}_{metadata['destination']}"

def enhance_journal(
    input_file: Path,
    output_file: Path,
    bedrock_client: Optional[Callable] = None,
    cache_file: Optional[Path] = None,
    mode: str = "both",
    resume: bool = True
) -> None:
    """Enhance a journal with AI-generated trail context and facts using AWS Bedrock."""
    log_message(f"Starting journal enhancement (mode: {mode})")
    log_message(f"Input file: {input_file}")
    log_message(f"Output file: {output_file}")
    if cache_file:
        log_message(f"Using cache file: {cache_file}")
    
    # Set up progress tracking
    progress_file = output_file.with_suffix('.progress.json')
    processed_entries, enhanced_entries = load_progress(progress_file) if resume else (set(), [])
    
    # Create a mapping of entry keys to their enhanced content
    processed_entry_map = {}
    if enhanced_entries:
        for i, entry in enumerate(enhanced_entries, 1):
            if i in processed_entries:
                try:
                    metadata = parse_entry_metadata(entry)
                    if metadata:
                        key = get_entry_key(metadata)
                        processed_entry_map[key] = entry
                except Exception as e:
                    log_message(f"Error parsing processed entry {i}: {e}", "WARNING")
    
    # Initialize Bedrock client if not provided
    if bedrock_client is None:
        import os
        region = os.getenv("AWS_REGION", "us-east-1")
        model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        log_message(f"Initializing Bedrock client (region: {region}, model: {model_id})")
        client = boto3.client("bedrock-runtime", region_name=region)
        bedrock_client = lambda metadata, mode: (
            get_trail_facts_bedrock(metadata, client, model_id) if mode == "facts"
            else get_trail_context_bedrock(metadata, client, model_id)
        )
    
    # Load cache if provided
    cache = {}
    if cache_file and cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
            log_message(f"Loaded {len(cache)} cached responses")
        except json.JSONDecodeError:
            log_message("Cache file exists but is invalid JSON, starting with empty cache", "WARNING")
            cache = {}
    
    # Read and process the journal
    content = input_file.read_text()
    entries = content.split('\n---\n')
    log_message(f"Found {len(entries)} journal entries to process")
    
    # Reset progress if the input file has changed
    if enhanced_entries and len(enhanced_entries) != len(entries):
        log_message("Progress file entries don't match input file, starting fresh", "WARNING")
        processed_entries = set()
        enhanced_entries = []
        processed_entry_map = {}
    
    # Process each entry
    for i, entry in enumerate(entries, 1):
        if not entry.strip():
            continue
        
        metadata = parse_entry_metadata(entry)
        if not metadata:
            log_message(f"Skipping entry {i}: Could not parse metadata", "WARNING")
            enhanced_entries.append(entry)
            processed_entries.add(i)
            save_progress(progress_file, processed_entries, enhanced_entries)
            continue
        
        # Check if this entry has already been processed
        entry_key = get_entry_key(metadata)
        if entry_key in processed_entry_map:
            log_message(f"Skipping already processed entry {i}/{len(entries)}: {metadata['date']} - {metadata['start_location']} to {metadata['destination']}")
            enhanced_entries.append(processed_entry_map[entry_key])
            processed_entries.add(i)
            save_progress(progress_file, processed_entries, enhanced_entries)
            continue
        
        log_message(f"Processing entry {i}/{len(entries)}: {metadata['date']} - {metadata['start_location']} to {metadata['destination']}")
        enhanced_entry = entry.strip()
        
        try:
            # Generate both context and facts if mode is "both"
            if mode in ["both", "context"]:
                # Create cache key for context
                context_key = f"context_{entry_key}"
                
                # Get or generate context
                if context_key in cache:
                    log_message(f"Using cached context for entry {i}")
                    context = cache[context_key]
                else:
                    log_message(f"Generating new context for entry {i}")
                    try:
                        context = bedrock_client(metadata, "context")
                        if context:
                            cache[context_key] = context
                            if cache_file:
                                cache_file.write_text(json.dumps(cache, indent=2))
                                log_message(f"Updated cache with new context for entry {i}")
                    except Exception as e:
                        log_message(f"Error getting trail context for entry {i}: {e}", "ERROR")
                        context = ""
                    time.sleep(1)  # Rate limiting
                
                if context:
                    enhanced_entry += f"\n\nTrail Context: {context}"
            
            if mode in ["both", "facts"]:
                # Create cache key for facts
                facts_key = f"facts_{entry_key}"
                
                # Get or generate facts
                if facts_key in cache:
                    log_message(f"Using cached facts for entry {i}")
                    facts = cache[facts_key]
                else:
                    log_message(f"Generating new facts for entry {i}")
                    try:
                        facts = bedrock_client(metadata, "facts")
                        if facts:
                            cache[facts_key] = facts
                            if cache_file:
                                cache_file.write_text(json.dumps(cache, indent=2))
                                log_message(f"Updated cache with new facts for entry {i}")
                    except Exception as e:
                        log_message(f"Error getting trail facts for entry {i}: {e}", "ERROR")
                        facts = ""
                    time.sleep(1)  # Rate limiting
                
                if facts:
                    enhanced_entry += f"\n\nTrail Facts: {facts}"
            
            # Save this entry's progress
            enhanced_entries.append(enhanced_entry)
            processed_entries.add(i)
            processed_entry_map[entry_key] = enhanced_entry
            save_progress(progress_file, processed_entries, enhanced_entries)
            log_message(f"Completed entry {i}/{len(entries)}")
            
        except Exception as e:
            log_message(f"Error processing entry {i}: {e}", "ERROR")
            # Don't save progress for this entry since it failed
            raise
    
    # Write final enhanced journal
    output_file.write_text('\n---\n'.join(enhanced_entries))
    log_message(f"Successfully wrote enhanced journal to {output_file}")
    
    # Clean up progress file if everything completed successfully
    if progress_file.exists():
        progress_file.unlink()
        log_message("Cleaned up progress file")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhance a trail journal with AI-generated content using AWS Bedrock')
    parser.add_argument('input_file', type=Path, help='Path to the input journal file')
    parser.add_argument('--output', type=Path, help='Path to the output file (default: input_file_enhanced.txt)')
    parser.add_argument('--cache', type=Path, help='Path to cache file for API responses')
    parser.add_argument('--mode', choices=['context', 'facts', 'both'], default='both',
                      help='Enhancement mode: context, facts, or both (default)')
    parser.add_argument('--no-resume', action='store_true',
                      help='Do not resume from previous progress')
    
    args = parser.parse_args()
    
    if not args.output:
        suffix = "_enhanced.txt"  # Always use _enhanced.txt since we might have both
        args.output = args.input_file.parent / f"{args.input_file.stem}{suffix}"
    
    try:
        enhance_journal(args.input_file, args.output, cache_file=args.cache, 
                       mode=args.mode, resume=not args.no_resume)
    except Exception as e:
        log_message(f"Fatal error during enhancement: {e}", "ERROR")
        log_message("Progress has been saved. Run the script again to resume.", "INFO")
        raise 