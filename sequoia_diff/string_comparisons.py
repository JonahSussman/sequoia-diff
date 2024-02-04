def levenshtein_distance(s1: str | None, s2: str | None):
  if s1 is None: s1 = ""
  if s2 is None: s2 = ""

  if len(s1) < len(s2):
    return levenshtein_distance(s2, s1)

  if len(s2) == 0:
    return len(s1)

  previous_row = range(len(s2) + 1)
  for i, c1 in enumerate(s1):
    current_row = [i + 1]
    for j, c2 in enumerate(s2):
      insertions = previous_row[j + 1] + 1
      deletions = current_row[j] + 1
      substitutions = previous_row[j] + (c1 != c2)
      current_row.append(min(insertions, deletions, substitutions))
    previous_row = current_row

  return previous_row[-1]


def normalized_levenshtein_distance(s1: str | None, s2: str | None):
  if s1 is None: s1 = ""
  if s2 is None: s2 = ""

  levenshtein_dist = levenshtein_distance(s1, s2)
  max_len = max(len(s1), len(s2))
  if max_len == 0:
    return 0
  
  return levenshtein_dist / max_len


def tri_gram_distance(a: str | None, b: str | None):
  if a is None: a = ""
  if b is None: b = ""

  if len(a) < 3 and len(b) < 3:
    return 2
  elif len(a) < 3:
    return 1 + len(b) - 2
  elif len(b) < 3:
    return 1 + len(a) - 2
    
  set_a = set([a[i:i+3] for i in range(len(a) - 2)])
  set_b = set([b[i:i+3] for i in range(len(b) - 2)])

  return len(set_a) + len(set_b) - len(set_a.intersection(set_b))


def normalized_tri_gram_distance(a: str, b: str):
  if a is None: a = ""
  if b is None: b = ""
  
  return tri_gram_distance(a, b) / (max(1, len(a) - 2) + max(1, len(b) - 2))
