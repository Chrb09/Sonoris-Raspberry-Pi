import json

print("=== TESTE COM 5 LINHAS POR CHUNK ===")
for char_limit in [15, 20, 25, 30]:
    lines = [
        {'text': 'A' * char_limit, 'timestamp': '2025-11-23T18:14:22.123456'} 
        for _ in range(5)
    ]
    chunk = {
        'conversation_id': 'Conversa_2025-11-23_18-14-22',
        'chunk_index': 0,
        'lines': lines,
        'is_last_chunk': False
    }
    chunk_json = json.dumps(chunk, ensure_ascii=False)
    size = len(chunk_json.encode('utf-8'))
    margin = 512 - size
    status = "✓ OK" if size <= 512 else "✗ MUITO GRANDE"
    print(f"{char_limit} chars: {size} bytes | Margem: {margin:+4d} | {status}")

print("\n=== TESTE COM 4 LINHAS POR CHUNK ===")
for char_limit in [25, 30, 35, 40, 45]:
    lines = [
        {'text': 'A' * char_limit, 'timestamp': '2025-11-23T18:14:22.123456'} 
        for _ in range(4)
    ]
    chunk = {
        'conversation_id': 'Conversa_2025-11-23_18-14-22',
        'chunk_index': 0,
        'lines': lines,
        'is_last_chunk': False
    }
    chunk_json = json.dumps(chunk, ensure_ascii=False)
    size = len(chunk_json.encode('utf-8'))
    margin = 512 - size
    status = "✓ OK" if size <= 512 else "✗ MUITO GRANDE"
    print(f"{char_limit} chars: {size} bytes | Margem: {margin:+4d} | {status}")

print("\n=== TESTE COM 3 LINHAS POR CHUNK ===")
for char_limit in [40, 50, 60, 70, 80]:
    lines = [
        {'text': 'A' * char_limit, 'timestamp': '2025-11-23T18:14:22.123456'} 
        for _ in range(3)
    ]
    chunk = {
        'conversation_id': 'Conversa_2025-11-23_18-14-22',
        'chunk_index': 0,
        'lines': lines,
        'is_last_chunk': False
    }
    chunk_json = json.dumps(chunk, ensure_ascii=False)
    size = len(chunk_json.encode('utf-8'))
    margin = 512 - size
    status = "✓ OK" if size <= 512 else "✗ MUITO GRANDE"
    print(f"{char_limit} chars: {size} bytes | Margem: {margin:+4d} | {status}")
