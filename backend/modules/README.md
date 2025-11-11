# Estrutura de Módulos de Automação

Este diretório (`modules/`) é destinado a conter o código-fonte das automações que serão executadas pelo sistema. Para garantir a organização, manutenibilidade e a separação de responsabilidades, cada automação deve seguir uma estrutura modular clara.

## Estrutura Recomendada

Cada automação deve residir em um subdiretório que segue a estrutura de um pacote Python, preferencialmente organizado por setor ou domínio de negócio.

```
modules/
├── <setor_ou_dominio>/
│   ├── <nome_da_automacao>/
│   │   ├── __init__.py
│   │   ├── run_<nome_da_automacao>.py  # Contém a função principal de execução
│   │   ├── helpers.py                  # Funções auxiliares específicas
│   │   ├── config.json                 # Configurações específicas da automação (se necessário)
│   │   └── assets/                     # Arquivos estáticos (templates, imagens de referência)
│   └── __init__.py
└── README.md
```

## Diretrizes de Desenvolvimento

1.  **Separação de Lógica e Artefatos de Execução:**
    *   O código-fonte (`.py`) deve ser mantido limpo e focado na lógica de negócio.
    *   **Logs, Screenshots e Resultados de Execução** (ex: CSVs, PDFs gerados) **NÃO** devem ser versionados ou armazenados dentro da estrutura do módulo. Eles devem ser escritos no `WORKSPACE_ROOT` do usuário, acessível via `payload["_workspace"]`.

2.  **Função de Entrada:**
    *   A função principal de execução deve ser definida no arquivo especificado no registro da automação (ex: `run_comercial.py` com a função `run`).
    *   A função deve aceitar um dicionário (`payload: Dict[str, Any]`) como argumento, contendo dados de entrada e metadados de execução (`_workspace`, `_user_id`, `_automation_id`).

3.  **Dependências:**
    *   Dependências específicas de automação (como `pyautogui`, `playwright`) devem ser tratadas como dependências do *worker* ou do ambiente de execução da automação, e não do core da API.

4.  **Configuração:**
    *   Use o arquivo `config.json` ou variáveis de ambiente para configurações específicas da automação, evitando hardcoding.

## Exemplo de Refatoração (Comercial Dashboard)

O módulo `comercial/dashboard` atual continha artefatos de execução (`logs/`, `screenshots/`) que foram limpos. O código-fonte restante deve ser refatorado para seguir as diretrizes acima.
