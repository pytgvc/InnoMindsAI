"""
duplicate_detector.py
Detects duplicate / highly similar ideas using a hand-rolled TF-IDF +
cosine similarity model (NumPy only, no sklearn dependency needed).
"""

import re
import numpy as np

DUPLICATE_THRESHOLD = 0.45  # cosine similarity above this => flagged as duplicate
SIMILAR_THRESHOLD = 0.25    # above this but below duplicate => "related idea"


def _tokenize(text):
    text = str(text).lower()
    return re.findall(r"[a-z']+", text)


def _build_vocab(docs_tokens):
    vocab = {}
    for tokens in docs_tokens:
        for t in set(tokens):
            vocab.setdefault(t, len(vocab))
    return vocab


def _tf_idf_matrix(docs_tokens):
    vocab = _build_vocab(docs_tokens)
    n_docs = len(docs_tokens)
    n_terms = len(vocab)
    if n_terms == 0:
        return np.zeros((n_docs, 0)), vocab

    tf = np.zeros((n_docs, n_terms))
    for i, tokens in enumerate(docs_tokens):
        for t in tokens:
            tf[i, vocab[t]] += 1
        if tokens:
            tf[i] = tf[i] / len(tokens)

    df = np.count_nonzero(tf > 0, axis=0)
    idf = np.log((n_docs + 1) / (df + 1)) + 1
    return tf * idf, vocab


def _cosine_sim(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def find_duplicates(new_title, new_description, existing_ideas):
    """
    existing_ideas: list of dicts with keys 'id', 'title', 'description'.
    Returns (best_match_id_or_None, best_score, list_of_(id, score) for anything >= SIMILAR_THRESHOLD)
    """
    if not existing_ideas:
        return None, 0.0, []

    docs = [f"{new_title} {new_description}"] + [
        f"{it.get('title', '')} {it.get('description', '')}" for it in existing_ideas
    ]
    docs_tokens = [_tokenize(d) for d in docs]
    matrix, vocab = _tf_idf_matrix(docs_tokens)
    if matrix.shape[1] == 0:
        return None, 0.0, []

    query_vec = matrix[0]
    scores = []
    for i, it in enumerate(existing_ideas, start=1):
        sim = _cosine_sim(query_vec, matrix[i])
        scores.append((it["id"], sim))

    scores.sort(key=lambda x: x[1], reverse=True)
    related = [(idea_id, round(s, 3)) for idea_id, s in scores if s >= SIMILAR_THRESHOLD]

    if related and related[0][1] >= DUPLICATE_THRESHOLD:
        return related[0][0], related[0][1], related
    return None, (related[0][1] if related else 0.0), related
