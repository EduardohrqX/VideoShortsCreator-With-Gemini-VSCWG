# Ferramenta de Automação e Criação de Shorts para YouTube

Este projeto é uma solução abrangente para automatizar a criação de vídeos curtos (Shorts) para o YouTube, desde a transcrição de áudio até a edição final do vídeo. Ele integra diversas etapas de processamento para otimizar o fluxo de trabalho de criadores de conteúdo. 

Lembre-se que ele roda na versão do python 3.10, qualquer versão superior a esta o aplicativo NÃO FUNCIONARÁ

## Funcionalidades

-   **Processamento de Áudio:** Extração e manipulação de áudio de vídeos.
-   **Transcrições:** Geração de transcrições precisas a partir de arquivos de áudio.
-   **Processamento de Texto:** Análise e otimização de texto para legendas e roteiros.
-   **Análise com Gemini (IA):** Integração com a API Gemini para análise de conteúdo, geração de ideias ou otimização de roteiros.
-   **Estilização de Legendas:** Aplicação de estilos personalizados às legendas para melhor visualização.
-   **Edição de Vídeo:** Automação de tarefas de edição para compilar os Shorts finais.
-   **Gerenciamento de Perfis:** Suporte a múltiplos perfis de configuração para diferentes tipos de conteúdo ou canais.

## Estrutura do Projeto

```
├── audio_processing.py
├── gemini_analysis.py
├── main.py
├── subtitle_styler.py
├── text_processing.py
├── transcription.py
├── video_editing.py
├── profiles/
│   ├── eae.json
│   ├── Perfil Padrao.json
│   └── teste.json
├── Shorts/ (Diretório para vídeos de entrada ou intermediários)
├── shorts_final_output/ (Saída dos vídeos Shorts finalizados)
└── shorts_temp_output/ (Arquivos temporários gerados durante o processamento)
```

## Como Usar

### Pré-requisitos

Certifique-se de ter o Python 3.10 (ou superior) instalado. As dependências do projeto podem ser instaladas via `pip`.

```bash
pip install -r requirements.txt # 
```

### Configuração de Perfis

Os perfis de configuração são armazenados na pasta `profiles/`. Você pode criar e editar arquivos `.json` para definir configurações específicas para diferentes fluxos de trabalho ou canais. Por exemplo, `Perfil Padrao.json` pode conter as configurações padrão.

### Execução

Para iniciar o processo de automação, execute o script principal:

```bash
python main.py
```

O script `main.py` orquestrará as etapas de processamento de áudio, transcrição, análise, estilização de legendas e edição de vídeo, utilizando as configurações definidas nos perfis.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues para relatar bugs ou sugerir novas funcionalidades, e enviar pull requests com melhorias.

## Licença

Este projeto está licenciado sob a licença MIT. 
