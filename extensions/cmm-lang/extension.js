const vscode = require('vscode');
const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    const pythonScript = path.join(__dirname, 'scripts', 'set_cmm_icon.py');

    function stampFileIcon(filePath) {
        if (!filePath || !filePath.endsWith('.cmm')) {
            return;
        }
        if (process.platform === 'darwin' && fs.existsSync(pythonScript)) {
            execFile('python3', [pythonScript, filePath], (err) => {
                if (err) {
                    console.error('[C--] Failed to stamp icon:', err);
                } else {
                    console.log('[C--] Stamped C-- logo on saved file:', filePath);
                }
            });
        }
    }

    // Hook: When saving a .cmm file, stamp the C-- logo
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument((document) => {
            if (document.fileName && document.fileName.endsWith('.cmm')) {
                stampFileIcon(document.fileName);
            }
        })
    );

    // Hook: When creating a .cmm file, stamp the C-- logo
    context.subscriptions.push(
        vscode.workspace.onDidCreateFiles((event) => {
            for (const file of event.files) {
                if (file.fsPath && file.fsPath.endsWith('.cmm')) {
                    stampFileIcon(file.fsPath);
                }
            }
        })
    );

    // Command: Manually stamp all .cmm files in the open workspace
    context.subscriptions.push(
        vscode.commands.registerCommand('cmm.applyIcons', () => {
            const folders = vscode.workspace.workspaceFolders;
            if (folders && folders.length > 0) {
                const root = folders[0].uri.fsPath;
                if (process.platform === 'darwin' && fs.existsSync(pythonScript)) {
                    execFile('python3', [pythonScript, root], (err, stdout) => {
                        if (err) {
                            vscode.window.showErrorMessage(`C--: Could not apply icons: ${err.message}`);
                        } else {
                            vscode.window.showInformationMessage('C--: Successfully applied 3D logo icon to all .cmm files!');
                        }
                    });
                }
            }
        })
    );
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
