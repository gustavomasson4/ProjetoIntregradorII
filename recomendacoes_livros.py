import requests

def recomendar_livros(termo_pesquisa, max_resultados=5):
    """
    Busca recomendações de livros usando a Google Books API
    :param termo_pesquisa: termo ou assunto para pesquisa de livros
    :param max_resultados: quantidade máxima de livros para recomendar
    :return: lista de dicionários com título e autores
    """
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": termo_pesquisa,
        "maxResults": max_resultados,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("Erro ao acessar a API:", response.status_code)
        return []
    data = response.json()
    livros = []
    for item in data.get("items", []):
        info = item.get("volumeInfo", {})
        titulo = info.get("title", "Título não disponível")
        autores = info.get("authors", ["Autor não disponível"])
        livros.append({
            "titulo": titulo,
            "autores": autores
        })
    return livros

if __name__ == "__main__":
    assunto = input("Digite um tema ou gênero para recomendações de livros: ")
    recomendacoes = recomendar_livros(assunto)
    print("\nRecomendações de livros:")
    for livro in recomendacoes:
        print(f"- {livro['titulo']} ({', '.join(livro['autores'])})")