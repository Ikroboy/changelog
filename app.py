from flask import Flask, request, render_template, send_file
import os
import csv
import requests
from requests.auth import HTTPBasicAuth
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        jira_url = request.form["jira_url"]
        email = request.form["email"]
        token = request.form["api_token"]
        file = request.files["arquivo"]

        path_csv = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(path_csv)
        resultado_path = os.path.join(UPLOAD_FOLDER, "resultado.csv")

        try:
            linhas = []
            with open(path_csv, "r", encoding="utf-8") as csvfile:
                total = sum(1 for row in csv.reader(csvfile) if row)
            with open(path_csv, "r", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                first_line = True
                processed = 0
                for linha in reader:
                    if first_line:
                        first_line = False
                        continue
                    if not linha:
                        continue
                    issue_key = linha[0].strip()
                    url = f"{jira_url}/rest/api/2/issue/{issue_key}?expand=changelog"
                    response = requests.get(url, auth=HTTPBasicAuth(email, token))
                    if response.status_code != 200:
                        continue
                    dados = response.json()
                    summary = dados.get("fields", {}).get("summary", "").strip()
                    for hist in dados.get("changelog", {}).get("histories", []):
                        change_date = hist.get("created", "")
                        for item in hist.get("items", []):
                            if item.get("field") == "status":
                                from_str = (item.get("fromString") or "")[:30]
                                to_str = (item.get("toString") or "")[:30]
                                mudanca = f"[{from_str}] -> [{to_str}]"
                                linhas.append((change_date, issue_key, summary, "status", mudanca))
                    processed += 1

            linhas.sort(key=lambda x: (x[0], x[1]))
            with open(resultado_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["DATA", "KEY", "SUMMARY", "CAMPO", "MUDANÇA"])
                for linha in linhas:
                    writer.writerow(linha)

            # Ao concluir, mostra a mensagem de status e o botão de download
            return render_template("index.html", status=f"✅ Processo finalizado. {len(linhas)} mudanças exportadas.", download_url="/download", show_form=False)

        except Exception as e:
            return render_template("index.html", status=f"❌ Erro: {str(e)}", show_form=False)

    # Se for um GET, ou após o envio, renderiza a página com o formulário.
    return render_template("index.html", show_form=True, status=None)

@app.route("/download")
def download():
    return send_file("uploads/resultado.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)