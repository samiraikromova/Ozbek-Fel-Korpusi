import os
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Article
import cyrtranslit
from datetime import datetime
import re

styles = {
            'badiiy': 'Badiiy (roman, hikoya)',
            'publitsistik': 'Publitsistik (maqola, esse)',
            'rasmiy': 'Rasmiy (hujjat, ariza)',
            'ilmiy': 'Ilmiy (maqola, tadqiqot)'
        }

common_suffixes = {
            'di', 'gan', 'yap', 'moq', 'adi', 'ing', 'ar', 'ib', 'mi', 'chi', 'lik', 'lar',
            'da', 'dan', 'ga', 'ni', 'ning', 'si', 'siz', 'cha', 'dagi', 'man', 'san',
            'miz', 'siz', 'lar', 'dim', 'ding', 'dik', 'dilar', 'mish', 'madi', 'mas', 'a', 'ajak', 'ay', 'ala', 'ar',
            'asi', 'b', 'v', 'ver', 'gaz', 'kaz', 'qaz', 'gʻaz', 'kar',
            'gan', 'gani', 'kani', 'qani', 'gancha', 'ganicha', 'guncha', 'kuncha', 'quncha', 'gach',
            'kach', 'qach', 'gi', 'giz', 'gin', 'guvchi', 'gulik', 'gur', 'gusi', 'gʻusi', 'di',
            'digan', 'dik', 'dir'
        }


def search_active_document(request):

    last_updated = datetime.now()
    query = request.GET.get('q', '').strip().lower()
    search_type = request.GET.get('type', 'word')
    style_search = request.GET.get('style')
    page_number = request.GET.get('page', 1)
    all_results = []
    document_occurrences = []
    total_word_count = 0  # <-- New line

    cyr_query = cyrtranslit.to_cyrillic(query, 'ru')
    if style_search:
        documents = Article.objects.filter(style=style_search)
    else:
        documents = Article.objects.all()
    doc_count = documents.count()

    for document in documents:
        count = 0  # Reset count for each document

        if not document or not document.file:
            continue

        file_path = document.file.path
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    total_word_count += len(line.split())
                    line_lower = line.lower()

                    match = False
                    if query:
                        if search_type == 'word':
                            if (re.search(rf'\b{re.escape(query)}\b', line_lower) or
                                    re.search(rf'\b{re.escape(cyr_query)}\b', line_lower)):
                                match = True
                                count += 1
                        elif search_type == 'suffix' and query in common_suffixes:
                            if any(word.endswith(query) or word.endswith(cyr_query)
                                   for word in line_lower.split()):
                                match = True
                                count += 1

                    if match:
                        all_results.append([document.author, document.title, document.style,
                                            f"{line.strip()}"])

            # Only append to document_occurrences if there were matches
            if count > 0:
                document_occurrences.append({
                    'title': document.title,
                    'author': document.author,
                    'count': count,
                    'style': document.style
                })

        except Exception as e:
            all_results.append(f"{document.title}: Fayl o'qish bilan muammo - {str(e)}")

    if query and not all_results:
        context = {
            'query': query,
            'total_word_count': total_word_count,
            'last_updated': last_updated,
            'doc_count': doc_count,
            'styles': styles,
            'message': "So‘rov bo‘yicha hech qanday natija topilmadi."
        }
        return render(request, 'index.html', context)

    paginator = Paginator(all_results, 50)
    page_obj = paginator.get_page(page_number)
    found_no = len(all_results)
    print(document_occurrences)

    if page_obj:
        return render(request, 'results.html', {'results': page_obj.object_list,
                                                'search_type': search_type,
                                                'query': query,
                                                'page_obj': page_obj,
                                                'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),
                                                'found': found_no,
                                                'per_doc': document_occurrences})

    context = {
        'query': request.GET.get('q', ''),
        'total_word_count': total_word_count,  # <-- Add to context
        'last_updated': last_updated,
        'doc_count': doc_count,
        'styles': styles,
    }

    return render(request, 'index.html', context)


def results_page(request):
    return render(request, 'results.html')
