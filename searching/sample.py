import cyrtranslit

cyrillic_text = cyrtranslit.to_cyrillic("ashob", "ru")
print(cyrillic_text)  # Output: Моё судно на воздушной подушке полно угрей



m = cyrtranslit.to_latin("Моё судно", "tj")
print(m)
# import os
#
# # Get absolute path to current file
# base_dir = os.path.dirname(os.path.abspath(__file__))
# file_path = os.path.join(base_dir, '..', 'articles', 'sample.txt')  # Adjust path as needed
#
# file_path = os.path.abspath(file_path)  # Normalize path
#
# if os.path.exists(file_path):
#     with open(file_path, 'r', encoding='utf-8') as fp:
#         lines = fp.readlines()
#         word = 'бывший'
#         for row in lines:
#             if word in row:
#                 print(row)
# else:
#     print('File not found at:', file_path)
