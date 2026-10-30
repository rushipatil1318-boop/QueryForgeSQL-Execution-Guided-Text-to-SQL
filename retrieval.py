"""A transparent lexical schema retriever. No gold SQL or row values are used."""

from collections import Counter, deque
import math
import re


def words(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    tokens = re.findall(r"[a-z0-9]+", text.casefold())
    # A deliberately simple plural rule, not a linguistic model.
    return [token[:-1] if len(token) > 3 and token.endswith("s") else token for token in tokens]


def retrieve_schema(question: str, schema: dict, top_k: int = 4,
                    columns_per_table: int = 12) -> dict:
    tables = schema["tables"]
    documents = {
        name: words(name + " " + " ".join(column["name"] for column in table["columns"]))
        for name, table in tables.items()
    }
    query = set(words(question))
    frequencies = Counter(word for document in documents.values() for word in set(document))

    def score(document):
        counts = Counter(document)
        return sum((1 + math.log((len(tables) + 1) / (frequencies[word] + 1)))
                   * counts[word] / (len(document) + 1) for word in query if word in counts)

    ranking = sorted(tables, key=lambda name: (-score(documents[name]), name))
    selected = ranking[:top_k]
    graph = {name: set() for name in tables}
    for name, table in tables.items():
        for key in table["foreign_keys"]:
            target = key["target_table"]
            if target in graph:
                graph[name].add(target)
                graph[target].add(name)
    # Reserve one extra table, when available, to connect selected tables.
    bridges = []
    for source in list(selected):
        queue = deque([(source, [source])])
        visited = {source}
        while queue:
            node, path = queue.popleft()
            if node in selected and node != source:
                for bridge in path[1:-1]:
                    if bridge not in selected and bridge not in bridges:
                        bridges.append(bridge)
                continue
            for neighbor in sorted(graph[node]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
    selected += bridges[:1]
    selected = list(dict.fromkeys(selected))
    lines, shown_columns = [], {}
    for name in selected:
        table = tables[name]
        keys = {c["name"] for c in table["columns"] if c["primary_key"]}
        keys.update(key["column"] for key in table["foreign_keys"])
        # Include incoming join keys as well, even if their names are not query words.
        for other in selected:
            keys.update(key["target_column"] for key in tables[other]["foreign_keys"]
                        if key["target_table"] == name and key["target_column"])
        ranked_columns = sorted(table["columns"],
            key=lambda column: (-len(query.intersection(words(column["name"]))), column["name"]))
        chosen = keys | {c["name"] for c in ranked_columns[:columns_per_table]}
        columns = [column for column in table["columns"] if column["name"] in chosen]
        shown_columns[name] = [column["name"] for column in columns]
        lines.append(f"TABLE {name!r}: " + ", ".join(
            f"{column['name']!r} {column['type']}" + (" PRIMARY KEY" if column["primary_key"] else "")
            for column in columns))
        for key in table["foreign_keys"]:
            if key["target_table"] in selected:
                lines.append(f"FOREIGN KEY {name!r}.{key['column']!r} -> "
                             f"{key['target_table']!r}.{key['target_column']!r}")
    return {"text": "\n".join(lines), "tables": selected, "columns": shown_columns,
            "ranking": [{"table": name, "score": score(documents[name])} for name in ranking],
            "bridge_budget": 1}
