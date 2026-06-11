import ast
import numpy as np
import zlib
import re

# --------------------------------------------
# PYTHON AST VECTOR
# --------------------------------------------
def ast_to_vector(code, dim=128):
    try:
        tree = ast.parse(code)
    except:
        return np.zeros(dim, dtype=float)

    nodes = []

    def visit(node):
        nodes.append(zlib.crc32(type(node).__name__.encode('utf-8')) & 0xffffffff)

        if isinstance(node, ast.Name):
            nodes.append(zlib.crc32(node.id.encode('utf-8')) & 0xffffffff)
        elif isinstance(node, ast.Constant):
            nodes.append(zlib.crc32(str(node.value).encode('utf-8')) & 0xffffffff)
        elif isinstance(node, ast.Attribute):
            nodes.append(zlib.crc32(node.attr.encode('utf-8')) & 0xffffffff)

        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)

    vec = np.array(nodes, dtype=float)

    if len(vec) < dim:
        vec = np.pad(vec, (0, dim - len(vec)), "constant")
    else:
        vec = vec[:dim]

    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

# --------------------------------------------
# TOKEN VECTOR FOR OTHER LANGUAGES
# --------------------------------------------
def tokenize_code(code):
    # remove common comments: // /* */ # <!-- -->
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"#.*", "", code)
    code = re.sub(r"<!--.*?-->", "", code, flags=re.DOTALL)

    # extract words, identifiers, tags, etc.
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code)
    return tokens

def bag_of_tokens_vector(code, dim=128):
    tokens = tokenize_code(code)
    if not tokens:
        return np.zeros(dim, dtype=float)

    hashed = [(zlib.crc32(t.encode()) & 0xffffffff) for t in tokens]

    vec = np.array(hashed, dtype=float)
    if len(vec) < dim:
        vec = np.pad(vec, (0, dim - len(vec)))
    else:
        vec = vec[:dim]

    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

# --------------------------------------------
# MAIN SIMILARITY FUNCTION
# --------------------------------------------
def compute_code_similarity(c1, c2, ext=None):
    ext = ext.lower() if ext else ""

    if ext == "py":
        v1 = ast_to_vector(c1)
        v2 = ast_to_vector(c2)
    else:
        v1 = bag_of_tokens_vector(c1)
        v2 = bag_of_tokens_vector(c2)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0

    cosine = float(np.dot(v1, v2) / (norm1 * norm2))
    return max(0.0, min(cosine, 1.0))
