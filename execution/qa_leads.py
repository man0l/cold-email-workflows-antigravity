#!/usr/bin/env python3
"""
Quality Assurance Tool for Lead Scraping Results

Analyzes scraped leads against target keywords to determine if the quality
meets the threshold before proceeding with a full scrape.

Usage:
    python execution/qa_leads.py .tmp/test_leads.json --keywords "copywriting,content writing,copywriter"
    python execution/qa_leads.py .tmp/test_leads.json --keywords "PPC,paid ads" --threshold 80
"""

import json
import argparse
import sys
from typing import List, Dict, Tuple


def analyze_leads(leads: List[Dict], target_keywords: List[str]) -> Tuple[int, List[str], List[Dict]]:
    """
    Analyze leads against target keywords.
    
    Returns:
        Tuple of (matches_count, non_matching_companies, detailed_results)
    """
    matches = 0
    non_matches = []
    detailed_results = []
    
    for i, lead in enumerate(leads, 1):
        company = lead.get('company_name', 'N/A')
        keywords = (lead.get('keywords') or '').lower()
        description = (lead.get('company_description') or '').lower()
        
        # Check if ANY target keyword appears in keywords OR description
        matched_terms = [term for term in target_keywords if term.lower() in keywords or term.lower() in description]
        has_match = len(matched_terms) > 0
        
        result = {
            'index': i,
            'company': company,
            'matched': has_match,
            'matched_terms': matched_terms
        }
        detailed_results.append(result)
        
        if has_match:
            matches += 1
        else:
            non_matches.append(company)
    
    return matches, non_matches, detailed_results


def print_results(leads_count: int, matches: int, non_matches: List[str], 
                 detailed_results: List[Dict], target_keywords: List[str], 
                 threshold: int, verbose: bool = False):
    """Print formatted quality analysis results."""
    
    match_rate = (matches / leads_count * 100) if leads_count > 0 else 0
    
    print(f'\n{"="*60}')
    print(f'LEAD QUALITY ANALYSIS')
    print(f'{"="*60}')
    print(f'Total leads analyzed: {leads_count}')
    print(f'Target keywords: {", ".join(target_keywords)}')
    print(f'Quality threshold: {threshold}%')
    print(f'\n{"="*60}')
    print(f'RESULTS')
    print(f'{"="*60}')
    
    # Print summary for each lead
    if verbose:
        print('\nDetailed Analysis:')
        for result in detailed_results:
            status = '✓' if result['matched'] else '✗'
            matched_info = f" (matched: {', '.join(result['matched_terms'])})" if result['matched_terms'] else ""
            print(f"{result['index']:2d}. {status} {result['company']}{matched_info}")
    else:
        print('\nQuick Summary:')
        for result in detailed_results:
            status = '✓' if result['matched'] else '✗'
            print(f"{result['index']:2d}. {status} {result['company']}")
    
    # Print match statistics
    print(f'\n{"="*60}')
    print(f'MATCH STATISTICS')
    print(f'{"="*60}')
    print(f'Matches: {matches}/{leads_count} ({match_rate:.1f}%)')
    
    # Determine pass/fail
    if match_rate >= threshold:
        print(f'✓ PASS - Quality threshold met (≥{threshold}%)')
        print(f'\n✅ Proceed with full scrape')
        exit_code = 0
    elif match_rate >= threshold - 20:  # Marginal zone (e.g., 60-79% if threshold is 80%)
        print(f'⚠ MARGINAL - Quality below threshold but close ({match_rate:.1f}% vs {threshold}%)')
        print(f'\n⚠️  Ask user for approval or refine criteria')
        exit_code = 1
    else:
        print(f'✗ FAIL - Quality well below threshold ({match_rate:.1f}% vs {threshold}%)')
        print(f'\n❌ STOP - Refine search criteria before full scrape')
        exit_code = 2
    
    # Show examples of non-matches if failed
    if match_rate < threshold and non_matches:
        print(f'\n{"="*60}')
        print(f'NON-MATCHING COMPANIES (examples)')
        print(f'{"="*60}')
        for company in non_matches[:5]:
            print(f'  - {company}')
    
    # Provide recommendations if failed
    if match_rate < threshold:
        print(f'\n{"="*60}')
        print(f'RECOMMENDATIONS')
        print(f'{"="*60}')
        print('Consider these adjustments:')
        print('  1. Broaden keywords: Add related terms')
        print('     Example: "copywriting" → "copywriting,content writing,copywriter"')
        print('  2. Add job titles: Target specific roles')
        print('     Example: --job-titles "Copywriter,Content Writer"')
        print('  3. Remove restrictive filters: Try without --size or --industries')
        print('  4. Check keyword spelling: Ensure keywords match industry terminology')
    
    print(f'\n{"="*60}\n')
    
    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description='Quality assurance tool for lead scraping results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic usage with default 80% threshold
  python execution/qa_leads.py .tmp/test_leads.json --keywords "copywriting,content writing"
  
  # Custom threshold
  python execution/qa_leads.py .tmp/test_leads.json --keywords "PPC,paid ads" --threshold 70
  
  # Verbose output showing matched terms
  python execution/qa_leads.py .tmp/test_leads.json --keywords "SaaS,software" --verbose
        '''
    )
    
    parser.add_argument('input_file', help='Path to JSON file containing scraped leads')
    parser.add_argument('--keywords', required=True, 
                       help='Comma-separated list of target keywords to match against')
    parser.add_argument('--threshold', type=int, default=80,
                       help='Quality threshold percentage (default: 80)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output including matched terms')
    
    args = parser.parse_args()
    
    # Parse keywords
    target_keywords = [k.strip() for k in args.keywords.split(',')]
    
    # Load leads
    try:
        with open(args.input_file, 'r') as f:
            leads = json.load(f)
    except FileNotFoundError:
        print(f'Error: File not found: {args.input_file}')
        sys.exit(3)
    except json.JSONDecodeError:
        print(f'Error: Invalid JSON in file: {args.input_file}')
        sys.exit(3)
    
    if not leads:
        print('Error: No leads found in file')
        sys.exit(3)
    
    # Analyze leads
    matches, non_matches, detailed_results = analyze_leads(leads, target_keywords)
    
    # Print results and exit with appropriate code
    exit_code = print_results(
        len(leads), matches, non_matches, detailed_results, 
        target_keywords, args.threshold, args.verbose
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
