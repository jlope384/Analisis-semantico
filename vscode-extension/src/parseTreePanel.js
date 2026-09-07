// Panel webview que dibuja el arbol sintactico (JSON de tree_export.py)
// como una lista anidada colapsable. Sin dependencias externas: todo el
// HTML/CSS/JS vive inline para no pelear con la Content-Security-Policy
// de los webviews de VS Code.

const vscode = require("vscode");

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderNode(node) {
  if (node.kind === "token") {
    const pos = node.line != null ? ` <span class="pos">(${node.line}:${node.column})</span>` : "";
    return `<li class="token">"${escapeHtml(node.label)}"${pos}</li>`;
  }

  const children = (node.children || []).map(renderNode).join("");
  const pos = node.line != null ? ` <span class="pos">(${node.line}:${node.column})</span>` : "";
  return `
    <li class="rule">
      <details open>
        <summary>${escapeHtml(node.label)}${pos}</summary>
        <ul>${children}</ul>
      </details>
    </li>`;
}

function renderParseTreePanel(context, fileName, tree) {
  const panel = vscode.window.createWebviewPanel(
    "compiscriptParseTree",
    `Arbol sintactico: ${fileName}`,
    vscode.ViewColumn.Beside,
    { enableScripts: false }
  );

  const body = renderNode(tree);

  panel.webview.html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body { font-family: var(--vscode-editor-font-family, monospace); font-size: 13px; color: var(--vscode-editor-foreground); }
  ul { list-style: none; margin: 0; padding-left: 1.1rem; }
  li.rule > details > summary { cursor: pointer; color: var(--vscode-symbolIcon-classForeground, #4ec9b0); }
  li.token { color: var(--vscode-symbolIcon-stringForeground, #ce9178); margin: 2px 0; }
  .pos { color: var(--vscode-descriptionForeground); font-size: 0.85em; }
  summary::marker { color: var(--vscode-descriptionForeground); }
</style>
</head>
<body>
  <ul>${body}</ul>
</body>
</html>`;
}

module.exports = { renderParseTreePanel };
