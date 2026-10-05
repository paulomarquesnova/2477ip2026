import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("IAEDU_API_ENDPOINT")
API_KEY = os.getenv("IAEDU_API_KEY")
CHANNEL_ID = os.getenv("IAEDU_CHANNEL_ID")

HEADERS = {
    "x-api-key": API_KEY
}

PROJECT_DIR = Path.cwd()
THREAD_ID = "mini-claude-code-001"


def list_files():
    files = []

    for path in PROJECT_DIR.rglob("*"):
        if not path.is_file():
            continue

        if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue

        files.append(str(path.relative_to(PROJECT_DIR)))

    return files


def read_file(path):
    target = PROJECT_DIR / path

    if not target.exists():
        return f"ERRO: ficheiro não encontrado: {path}"

    if not target.is_file():
        return f"ERRO: não é um ficheiro: {path}"

    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERRO ao ler {path}: {e}"


def write_file(path, content):
    target = PROJECT_DIR / path

    if target.exists():
        print(f"\n⚠️ O ficheiro '{path}' já existe.")
        answer = input("Queres substituí-lo? [s/N]: ")

        if answer.lower() != "s":
            return "Operação cancelada pelo utilizador."

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return f"Ficheiro criado/alterado: {path}"


def ask_ai(message):
    data = {
        "channel_id": CHANNEL_ID,
        "thread_id": THREAD_ID,
        "user_info": "{}",
        "message": message,
    }

    response = requests.post(
        ENDPOINT,
        headers=HEADERS,
        data=data,
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP {response.status_code}: {response.text}"
        )

    result = ""

    for line in response.text.splitlines():
        if not line.strip():
            continue

        try:
            event = json.loads(line)

            if event.get("type") == "token":
                result += event.get("content", "")

        except json.JSONDecodeError:
            continue

    return result


SYSTEM_PROMPT = """
És um agente de programação chamado Mini Claude Code.

Estás a trabalhar dentro de um projeto Git.

Tens três ferramentas disponíveis:

1. LIST_FILES
2. READ_FILE
3. WRITE_FILE

Quando precisares de usar uma ferramenta, responde APENAS com JSON válido neste formato:

{"action":"LIST_FILES"}

ou:

{"action":"READ_FILE","path":"app.py"}

ou:

{"action":"WRITE_FILE","path":"hello.py","content":"print('Olá!')"}

Se não precisares de usar uma ferramenta, responde normalmente.

Nunca inventes o conteúdo de um ficheiro.
Antes de alterar um ficheiro existente, lê-o primeiro.
Não uses comandos do sistema.
Não alteres ficheiros dentro de .git ou .venv.
"""


def extract_json(text):
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def run_agent(user_message):
    conversation = SYSTEM_PROMPT + "\n\nPedido do utilizador:\n" + user_message

    for _ in range(8):
        answer = ask_ai(conversation)
        action = extract_json(answer)

        if not action:
            return answer

        action_type = action.get("action")

        if action_type == "LIST_FILES":
            result = json.dumps(
                list_files(),
                ensure_ascii=False,
                indent=2
            )

        elif action_type == "READ_FILE":
            result = read_file(action.get("path", ""))

        elif action_type == "WRITE_FILE":
            result = write_file(
                action.get("path", ""),
                action.get("content", "")
            )

        else:
            return answer

        conversation += (
            "\n\nResultado da ferramenta:\n"
            + result
            + "\n\nContinua a executar o pedido original."
        )

    return "O agente atingiu o limite de operações."


print("╭──────────────────────────────╮")
print("│      Mini Claude Code 🤖     │")
print("╰──────────────────────────────╯")
print()
print(f"Projeto: {PROJECT_DIR}")
print("Escreve 'sair' para terminar.\n")


while True:
    try:
        user_message = input("Tu: ").strip()

        if not user_message:
            continue

        if user_message.lower() in {"sair", "exit", "quit"}:
            print("Até já! 👋")
            break

        print("\nIA: ", end="", flush=True)

        result = run_agent(user_message)

        print(result)
        print()

    except KeyboardInterrupt:
        print("\nAté já! 👋")
        break

    except Exception as e:
        print(f"\nErro: {e}\n")