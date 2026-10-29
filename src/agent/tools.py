import ast

def validate_syntax(code: str) -> list[str]:
    """
    Deterministic tool to analyze code withou executing it
    Returns a validation error list or empty list
    """
    errors = []

    clean_code = code.strip()
    if clean_code.startswith("```python"):
        clean_code = clean_code[9:]
    if clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]


    try:
        # ast.parse compile code into a syntax tree
        # throws SyntaxError if it finds a errors
        ast.parse(clean_code.strip())
    except SyntaxError as e:
        errors.append(f"Syntax error in line {e.lineno}: {e.msg}")
    except Exception as e:
        errors.append(f"Unexpected error while validating code: {str(e)}")

    return errors


if __name__ == "__main__":
    # Prueba rápida de la herramienta
    codigo_bueno = "def saludar():\n    print('Hola')"
    codigo_malo = "def saludar()\n    print('Faltan dos puntos')"
    
    print("Errores código bueno:", validate_syntax(codigo_bueno))
    print("Errores código malo :", validate_syntax(codigo_malo))
