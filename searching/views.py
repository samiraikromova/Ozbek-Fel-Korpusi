import os
import re
from collections import Counter
import chardet
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Article

# ——————————————————————————————
# CUSTOM UZBEK SCRIPT CONVERTER
# ——————————————————————————————

# Uzbek Cyrillic to Latin alphabet mapping
CYRILLIC_TO_LATIN = {
    'а': 'a', 'А': 'A',
    'б': 'b', 'Б': 'B',
    'в': 'v', 'В': 'V',
    'г': 'g', 'Г': 'G',
    'д': 'd', 'Д': 'D',
    'е': 'e', 'Е': 'E',
    'ё': 'yo', 'Ё': 'Yo',
    'ж': 'j', 'Ж': 'J',
    'з': 'z', 'З': 'Z',
    'и': 'i', 'И': 'I',
    'й': 'y', 'Й': 'Y',
    'к': 'k', 'К': 'K',
    'л': 'l', 'Л': 'L',
    'м': 'm', 'М': 'M',
    'н': 'n', 'Н': 'N',
    'о': 'o', 'О': 'O',
    'п': 'p', 'П': 'P',
    'р': 'r', 'Р': 'R',
    'с': 's', 'С': 'S',
    'т': 't', 'Т': 'T',
    'у': 'u', 'У': 'U',
    'ф': 'f', 'Ф': 'F',
    'х': 'x', 'Х': 'X',
    'ц': 's', 'Ц': 'S',
    'ч': 'ch', 'Ч': 'Ch',
    'ш': 'sh', 'Ш': 'Sh',
    'щ': 'sh', 'Щ': 'Sh',
    'ъ': "'", 'Ъ': "'",
    'ы': 'i', 'Ы': 'I',
    'ь': "'", 'Ь': "'",
    'э': 'e', 'Э': 'E',
    'ю': 'yu', 'Ю': 'Yu',
    'я': 'ya', 'Я': 'Ya',
    'ў': "o'", 'Ў': "O'",
    'ғ': "g'", 'Ғ': "G'",
    'қ': 'q', 'Қ': 'Q',
    'ҳ': 'h', 'Ҳ': 'H'
}

# Create reverse mapping (Latin to Cyrillic)
LATIN_TO_CYRILLIC = {}
for cyr, lat in CYRILLIC_TO_LATIN.items():
    if lat not in LATIN_TO_CYRILLIC:
        LATIN_TO_CYRILLIC[lat] = []
    LATIN_TO_CYRILLIC[lat].append(cyr)


def cyrillic_to_latin_converter(text):
    """Convert Uzbek Cyrillic text to Latin using custom mapping"""
    if not text:
        return text

    result = ''
    for char in text:
        result += CYRILLIC_TO_LATIN.get(char, char)
    return result


def latin_to_cyrillic_converter(text):
    """Convert Uzbek Latin text to Cyrillic using custom mapping"""
    if not text:
        return text

    result = text
    # Sort by length (longest first) to handle multi-character mappings correctly
    sorted_latin_keys = sorted(LATIN_TO_CYRILLIC.keys(), key=len, reverse=True)

    for latin_char in sorted_latin_keys:
        cyrillic_options = LATIN_TO_CYRILLIC[latin_char]
        if cyrillic_options:
            # Use lowercase version by default, but preserve case
            cyrillic_char = next((c for c in cyrillic_options if c.islower()), cyrillic_options[0])

            # Create regex pattern, escaping special characters
            pattern = re.escape(latin_char)
            regex = re.compile(pattern, re.IGNORECASE)

            def replace_func(match):
                matched = match.group(0)
                if matched.isupper():
                    return cyrillic_char.upper() if cyrillic_char.islower() else cyrillic_char
                elif matched.istitle():
                    return cyrillic_char.capitalize() if cyrillic_char.islower() else cyrillic_char
                else:
                    return cyrillic_char.lower() if cyrillic_char.isupper() else cyrillic_char

            result = regex.sub(replace_func, result)

    return result


def get_style_priority(style_key):
    """
    Get priority for Uzbek corpus text styles.
    Lower numbers = higher priority (displayed first)

    Args:
        style_key (str): Style key from your STYLES dictionary

    Returns:
        int: Priority value (lower = higher priority)
    """
    # Define style priority mapping using your style keys
    style_priorities = {
        "badiiy": 1,
        "badiiy_uslub": 1,

        # Official/formal styles
        "rasmiy": 2,
        "rasmiy_uslub": 2,

        # Publicistic/journalistic style
        "publitsistik": 3,
        "publitsistik_uslub": 3,

        # Ilmiy uslub should be first (highest priority)
        "ilmiy": 4,
        "ilmiy_uslub": 4,


    }

    # Normalize input
    if not style_key:
        return 999  # Unknown/empty styles go last

    normalized_style = style_key.lower().strip()

    # Return priority or default high number for unknown styles
    return style_priorities.get(normalized_style, 100)


class SearchResult:
    """Represents a search result with style information"""

    def __init__(self, title, content, style, matched_term, document_id, count=1):
        self.title = title
        self.content = content
        self.style = style
        self.matched_term = matched_term
        self.document_id = document_id
        self.count = count
        self.priority = get_style_priority(style)

    def __lt__(self, other):
        """Enable sorting by priority"""
        return self.priority < other.priority


def sort_search_results(results):
    """
    Sort search results by style priority (Ilmiy first)

    Args:
        results (list): List of SearchResult objects or dictionaries

    Returns:
        list: Sorted results with Ilmiy uslub first
    """
    if not results:
        return []

    # Convert dictionaries to SearchResult objects if needed
    processed_results = []
    for result in results:
        if isinstance(result, dict):
            processed_results.append(SearchResult(
                title=result.get('title', ''),
                content=result.get('content', ''),
                style=result.get('style', ''),
                matched_term=result.get('matched_term', ''),
                document_id=result.get('document_id', ''),
                count=result.get('count', 1)
            ))
        else:
            processed_results.append(result)

    # Sort by priority (lower number = higher priority)
    return sorted(processed_results, key=lambda x: x.priority)


def group_results_by_style(results):
    """
    Group search results by style and sort by priority

    Args:
        results (list): List of search results

    Returns:
        dict: Dictionary with styles as keys, sorted by priority
    """
    from collections import defaultdict

    grouped = defaultdict(list)

    # Group results by style
    for result in results:
        style = result.style if hasattr(result, 'style') else result.get('style', 'Unknown')
        grouped[style].append(result)

    # Sort styles by priority and return ordered dict
    sorted_styles = sorted(grouped.keys(), key=get_style_priority)

    return {style: grouped[style] for style in sorted_styles}



def detect_script_type(text):
    """Detect if text is primarily Cyrillic, Latin, or mixed"""
    if not text:
        return 'unknown'

    cyrillic_count = len(re.findall(r'[а-яёўғқҳ]', text, re.IGNORECASE))
    latin_count = len(re.findall(r'[a-z\']', text, re.IGNORECASE))

    total = cyrillic_count + latin_count
    if total == 0:
        return 'unknown'

    cyrillic_ratio = cyrillic_count / total

    if cyrillic_ratio > 0.7:
        return 'cyrillic'
    elif cyrillic_ratio < 0.3:
        return 'latin'
    else:
        return 'mixed'


def generate_search_variants(search_term):
    """Generate both Cyrillic and Latin variants of search term"""
    if not search_term:
        return [search_term]

    variants = [search_term]
    script_type = detect_script_type(search_term)

    if script_type in ['cyrillic', 'mixed']:
        latin_variant = cyrillic_to_latin_converter(search_term)
        if latin_variant != search_term:
            variants.append(latin_variant)

    if script_type in ['latin', 'mixed']:
        cyrillic_variant = latin_to_cyrillic_converter(search_term)
        if cyrillic_variant != search_term:
            variants.append(cyrillic_variant)

    return list(set(variants))  # Remove duplicates


# ——————————————————————————————
# STYLES
# ——————————————————————————————
STYLES = {
    'badiiy': 'Badiiy uslub',
    'ilmiy': 'Ilmiy uslub',
    'publitsistik': 'Publitsistik uslub',
    'rasmiy': 'Rasmiy uslub',
}

common_suffixes = {
    'di', 'gan', 'yap', 'moq', 'adi', 'ing', 'ar', 'ib', 'mi', 'chi', 'lik', 'lar',
    'da', 'dan', 'ga', 'ni', 'ning', 'si', 'siz', 'cha', 'dagi', 'man', 'san',
    'miz', 'ding', 'dik', 'dilar', 'mish', 'madi', 'mas', 'a', 'ajak', 'ay', 'ala',
    'asi', 'b', 'v', 'ver', 'gaz', 'kaz', 'qaz', "gʻaz", 'kar',
    'gani', 'kani', 'qani', 'gancha', 'ganicha', 'guncha', 'kuncha', 'quncha',
    'gach', 'kach', 'qach', 'gi', 'giz', 'gin', 'guvchi', 'gulik', 'gur', 'gusi',
    "gʻusi", 'digan', 'dir'
}

def detect_encoding(file_path):
    """Detect file encoding"""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']


def search_results(request):
    """Enhanced search with cross-script support, pagination, and proper template integration"""
    # Start timer for search performance measurement
    start_time = timezone.now()

    # Get and clean search parameters
    raw_q = request.GET.get('q', '').strip()
    search_ty = request.GET.get('type', 'word')
    style_filt = request.GET.get('style', '')

    # Initialize empty results if no query
    if not raw_q:
        return render(request, 'results.html', {
            'query': raw_q,
            'search_type': search_ty,
            'style_filter': style_filt,
            'found': 0,
            'page_obj': None,
            'frequency_data': [],
            'search_time': 0,
            'style_name': '',
        })

    # Normalize apostrophes in query
    raw_q = _normalize_apostrophes(raw_q)

    # Generate all script variants of the search query
    search_variants = generate_search_variants(raw_q)

    # Apply style filter if specified
    qs = Article.objects.all()
    if style_filt in STYLES:
        qs = qs.filter(style=style_filt)

    hits = []
    CONTEXT = 50  # Characters to show around matches

    # Search through all filtered articles
    for art in qs:
        path = os.path.join(settings.MEDIA_ROOT, art.file.name)
        if not os.path.exists(path):
            continue

        try:
            # Read file content with proper encoding
            original_content = read_file_content(path)
            if not original_content or not original_content.strip():
                continue

            # Determine original script of the file
            original_script = detect_script_type(original_content)

            # Clean metadata
            author_clean = art.author.lstrip('—– -').strip() if art.author else ''
            title_clean = art.title.lstrip('—– -').strip() if art.title else ''

            # Track unique matches to avoid duplicates
            matches_found = set()

            for variant in search_variants:
                if not variant.strip():
                    continue

                # Create appropriate search pattern
                if search_ty == 'word':
                    # Modified pattern to match word and its suffixes
                    pattern = rf'\b{re.escape(variant)}([^\W\d_]{{0,6}})?\b'  # Matches word + up to 6 letter suffix
                else:  # suffix search
                    pattern = rf'{re.escape(variant)}\b'

                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    # Search in original content
                    for match in regex.finditer(original_content):
                        start, end = match.span()
                        matched_word = match.group(0)

                        # Create unique match identifier
                        match_id = f"{start}_{end}_{matched_word.lower()}"

                        # Skip duplicates or near-duplicates
                        if match_id in matches_found:
                            continue
                        matches_found.add(match_id)

                        # Extract context around match
                        context_start = max(0, start - CONTEXT)
                        context_end = min(len(original_content), end + CONTEXT)
                        context = original_content[context_start:context_end].strip()

                        if not context:
                            continue

                        # Calculate match position within context
                        match_start_in_context = start - context_start
                        match_end_in_context = end - context_start

                        # Create highlighted excerpts
                        excerpt_original = (
                                context[:match_start_in_context] +
                                f'<span class="highlight">{context[match_start_in_context:match_end_in_context]}</span>' +
                                context[match_end_in_context:]
                        )

                        # Generate alternate script version
                        if original_script == 'cyrillic':
                            excerpt_lat = cyrillic_to_latin_converter(excerpt_original)
                            excerpt_cyr = excerpt_original
                        elif original_script == 'latin':
                            excerpt_cyr = latin_to_cyrillic_converter(excerpt_original)
                            excerpt_lat = excerpt_original
                        else:
                            excerpt_lat = excerpt_cyr = excerpt_original

                        # Add hit to results
                        hits.append({
                            'author': author_clean,
                            'title': title_clean,
                            'style_key': art.style,
                            'style_name': STYLES.get(art.style, art.style),
                            'excerpt_lat': excerpt_lat.strip(),
                            'excerpt_cyr': excerpt_cyr.strip(),
                            'original_script': original_script,
                            'match_position': start,
                            'search_variant': variant,
                            'matched_word': matched_word,
                            'doc_id': art.id,
                        })

                except re.error as e:
                    print(f"Regex error with variant '{variant}': {e}")
                    continue
                except Exception as e:
                    print(f"Error searching with variant '{variant}': {e}")
                    continue

        except Exception as e:
            print(f"Error processing article {art.id}: {e}")
            continue

    # Remove near-duplicate hits
    unique_hits = []
    seen_contexts = set()

    for hit in hits:
        content_signature = (
            hit['author'],
            hit['title'],
            hit['excerpt_lat'][:100],  # First 100 chars for comparison
            hit.get('match_position', 0) // 20  # Group nearby positions
        )

        if content_signature not in seen_contexts:
            seen_contexts.add(content_signature)
            unique_hits.append(hit)

    hits = unique_hits

    # Sort results by author, title, then position
    hits.sort(key=lambda x: (

        get_style_priority(x['style_key']),  # PRIMARY: Style priority
        x['author'] or '',  # Secondary: Author
        x['title'] or '',  # Tertiary: Title
        x.get('match_position', 0)  # Final: Position
    ))

    # Calculate style frequency data for chart
    counts = Counter(h['style_key'] for h in hits)
    frequency_data = [
        {
            'style': STYLES[k],
            'count': counts.get(k, 0),
            'percentage': (counts.get(k, 0) / len(hits) * 100) if hits else 0
        }
        for k in STYLES
    ]

    # Paginate results
    paginator = Paginator(hits, 20)  # 20 results per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate search time
    search_time = (timezone.now() - start_time).total_seconds()

    # Prepare final context
    context = {
        'query': raw_q,
        'search_type': search_ty,
        'style_filter': style_filt,
        'style_name': STYLES.get(style_filt, ''),
        'found': len(hits),
        'page_obj': page_obj,
        'frequency_data': frequency_data,
        'search_time': search_time,
        'search_variants': search_variants,
    }

    return render(request, 'results.html', context)# ——————————————————————————————
# HELPER FUNCTIONS
# ——————————————————————————————


def read_file_content(file_path):
    """Read file content with proper encoding detection"""
    try:
        # Try UTF-8 first
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        try:
            # Try cp1251 (common for Cyrillic)
            with open(file_path, 'r', encoding='cp1251') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            try:
                # Try latin-1 as last resort
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return content
            except Exception as e:
                print(f"Could not read file {file_path}: {e}")
                return ""
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""


def is_cyrillic_text(text):
    """Determine if text is primarily Cyrillic (legacy function for compatibility)"""
    return detect_script_type(text) == 'cyrillic'


def _normalize_apostrophes(text):
    """Normalize different types of apostrophes"""
    apostrophe_variants = [''', ''', '`', '´', '′']
    for variant in apostrophe_variants:
        text = text.replace(variant, "'")
    return text


# ——————————————————————————————
# INDEX VIEW
# ——————————————————————————————
def index(request):
    total_words = 0
    for art in Article.objects.all():
        fp = os.path.join(settings.MEDIA_ROOT, art.file.name)
        if not os.path.exists(fp):
            continue
        content = read_file_content(fp)
        total_words += len(re.findall(r'\w+', content, re.UNICODE))

    context = {
        'total_word_count': total_words,
        'doc_count': Article.objects.count(),
        'last_updated': timezone.now(),
        'styles': STYLES,
    }
    return render(request, 'index.html', context)


# ——————————————————————————————
# STATISTICS VIEW
# ——————————————————————————————
def statistics_view(request):
    # Get counts per style (preserved existing functionality)
    counts = {k: Article.objects.filter(style=k).count() for k in STYLES}

    # NEW: Calculate word counts per style
    style_word_counts = {}
    for style in STYLES:
        word_count = 0
        articles = Article.objects.filter(style=style)
        for article in articles:
            file_path = os.path.join(settings.MEDIA_ROOT, article.file.name)
            if os.path.exists(file_path):
                content = read_file_content(file_path)
                word_count += len(re.findall(r'\w+', content, re.UNICODE))
        style_word_counts[style] = word_count

    # Calculate totals (NEW)
    total_words = sum(style_word_counts.values())
    total_texts = Article.objects.count()
    total_authors = Article.objects.values('author').distinct().count()

    # Preserved existing lists
    nasriy_list = Article.objects.filter(genre='nasriy').order_by('author')
    sheriy_list = Article.objects.filter(genre='sheriy').order_by('author')

    return render(request, 'statistics.html', {
        # Preserved existing context
        'style_counts': [
            {'key': k, 'label': STYLES[k], 'count': counts[k]}
            for k in STYLES
        ],
        'nasriy_list': nasriy_list,
        'sheriy_list': sheriy_list,
        'STYLES': STYLES,

        # NEW context for word counts
        'total_words': total_words,
        'total_texts': total_texts,
        'total_authors': total_authors,
        'badiiy_count': counts.get('badiiy', 0),
        'badiiy_words': style_word_counts.get('badiiy', 0),  # Fixed typo here
        'publitsistik_count': counts.get('publitsistik', 0),
        'publitsistik_words': style_word_counts.get('publitsistik', 0),
        'ilmiy_count': counts.get('ilmiy', 0),
        'ilmiy_words': style_word_counts.get('ilmiy', 0),
        'rasmiy_count': counts.get('rasmiy', 0),
        'rasmiy_words': style_word_counts.get('rasmiy', 0),
    })
# ——————————————————————————————
# MANAGEMENT COMMAND FOR SCRIPT ANALYSIS
# ——————————————————————————————
def analyze_corpus_scripts():
    """
    Analyze the corpus to see script distribution
    Can be run as a management command
    """
    script_stats = {'cyrillic': 0, 'latin': 0, 'mixed': 0, 'unknown': 0}

    for art in Article.objects.all():
        path = os.path.join(settings.MEDIA_ROOT, art.file.name)
        if not os.path.exists(path):
            continue

        content = read_file_content(path)
        if content:
            script_type = detect_script_type(content)
            script_stats[script_type] += 1

    print("Corpus Script Analysis:")
    for script, count in script_stats.items():
        print(f"{script.capitalize()}: {count} files")

    return script_stats