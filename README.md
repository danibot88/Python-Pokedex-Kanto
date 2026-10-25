# Pokédex Kanto

Aplicativo desktop em Python para explorar os 151 Pokémon da primeira geração.
Não usa navegador. Informações e imagens consultadas na PokéAPI ficam salvas no
computador para os próximos acessos.

## Recursos

- Lista completa de Kanto disponível imediatamente
- Busca por nome ou número
- Favoritos persistentes
- Tipos, altura, peso, habilidades e atributos base
- Imagens oficiais com fallback quando a imagem não está disponível
- Cache local em `%LOCALAPPDATA%\PokedexKanto` com gravação atômica
- Logs em `%LOCALAPPDATA%\PokedexKanto\logs\app.log`
- Tema escuro (`assets/style.qss`) e interface nativa com PySide6

## Executar no VS Code

1. Instale o Python 3.10 ou mais recente e marque **Add Python to PATH**.
2. Abra esta pasta no VS Code.
3. No terminal PowerShell, execute:

   ```powershell
   .\run.ps1
   ```

O script cria o `.venv`, instala as dependências apenas quando os
`requirements*.txt` mudam e inicia o aplicativo. Se o Python não estiver no
PATH, defina o caminho manualmente:

```powershell
$env:POKEDEX_PYTHON = "C:\caminho\para\python.exe"
```

Na primeira consulta de cada Pokémon é necessária conexão com a internet. Depois,
os dados consultados funcionam a partir do cache local.

## Testes e qualidade

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Os testes de interface usam `QT_QPA_PLATFORM=offscreen` e gravam em um diretório
temporário, sem tocar em `%LOCALAPPDATA%`.

## Gerar o executável

Execute no terminal:

```powershell
.\build-exe.ps1
```

O arquivo será criado em `dist\Pokedex-Kanto.exe`. O script usa
`requirements-dev.txt` (PyInstaller incluído).

## Organização

- `main.py`: ponto de entrada
- `src/pokedex_app/app.py`: interface e workers
- `src/pokedex_app/api.py`: PokéAPI, cache e validação das imagens
- `src/pokedex_app/data.py`: índice local dos 151 Pokémon
- `src/pokedex_app/storage.py`: favoritos, pastas locais e escrita atômica
- `src/pokedex_app/theme.py`: cores e carregamento do QSS
- `src/pokedex_app/log.py`: logging e captura de erros não tratados
- `src/pokedex_app/paths.py`: caminhos de recursos (código e executável)
- `assets/style.qss`: folha de estilo da interface
- `assets/`: ícones vetoriais próprios
- `scripts/common.ps1`: descoberta do Python e criação do ambiente virtual
- `tests/`: testes automatizados (pytest)
- `pyproject.toml`: configuração de pytest e ruff

## Personalização rápida

As cores ficam em `src/pokedex_app/theme.py` e são aplicadas em
`assets/style.qss` pelos marcadores `@background`, `@panel`, `@accent` etc. O
layout principal está no método `MainWindow._build_ui`, em
`src/pokedex_app/app.py`.

## Solução de problemas

- **Dados desatualizados ou corrompidos**: apague `%LOCALAPPDATA%\PokedexKanto\cache`
  e `%LOCALAPPDATA%\PokedexKanto\sprites`; o app baixa novamente.
- **Erro inesperado**: consulte `%LOCALAPPDATA%\PokedexKanto\logs\app.log`.
- **Outro diretório de dados**: defina `POKEDEX_APP_DIR` antes de abrir o app.
